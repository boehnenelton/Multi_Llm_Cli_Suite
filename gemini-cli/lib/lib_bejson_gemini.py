"""
Library:     lib_bejson_gemini.py
Jurisdiction: ["PYTHON", "CORE_COMMAND"]
Status:      OFFICIAL — Core-Command/Lib (v1.1)
Author:      Elton Boehnen
Version:     1.1 (OFFICIAL)
Date:        2026-04-23
Description: Advanced BEJSON Gemini Library (v3). 
             Sources core BEJSON and Validator libraries.
             Handles API key slots (104a), Context folder logic, 
             and Model selection per Gemini-CLI Policy.
"""

import os
import sys
import json
import time
import requests
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

# Add Lib directory to path if not already there
# CRITICAL FIX (v3.1): Dynamic path resolution — no hard-coded paths.
# Resolves the Lib directory relative to this script's location,
# with environment variable override for custom deployments.
_LIB_DIR_ENV = os.environ.get("BEJSON_LIB_DIR", "")
if _LIB_DIR_ENV:
    LIB_DIR = os.path.abspath(_LIB_DIR_ENV)
else:
    # Resolve relative to this file's location (handles any install path)
    LIB_DIR = str(Path(__file__).resolve().parent)

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

try:
    from lib_bejson_core import (
        bejson_core_load_file,
        bejson_core_atomic_write,
        bejson_core_create_104a,
        bejson_core_get_field_index,
        BEJSONCoreError
    )
    from lib_bejson_validator import bejson_validator_validate_file
except ImportError:
    print("CRITICAL: lib_bejson_core or lib_bejson_validator not found in path.")
    sys.exit(1)

# --- Constants & Templates ---

API_KEY_TEMPLATE = {
    "Format": "BEJSON",
    "Format_Version": "104a",
    "Format_Creator": "Elton Boehnen",
    "File_Version": 2,
    "Jurisdiction": "All scripts utilizing Gemini API keys",
    "Records_Type": ["ApiKey"],
    "Fields": [
        {"name": "slot_id", "type": "string"},
        {"name": "api_key", "type": "string"},
        {"name": "service", "type": "string"}
    ],
    "Values": []
}

MODELS = [
MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
]

DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_KEY_FILE = "/data/data/com.termux/files/home/.env/api_keys_v2_decrypted.104a.bejson"

# --- Gemini Key Manager ---

class GeminiKeyManager:
    """Manages Gemini API key slots in BEJSON 104a format."""

    def __init__(self, key_path: str = DEFAULT_KEY_FILE):
        self.key_path = Path(key_path)
        self.data = None
        self.slots = {} # slot_id -> key
        
        if not self.key_path.exists():
            self.create_template()
        self.load()

    def create_template(self):
        """Creates the initial API key file if it doesn't exist."""
        bejson_core_atomic_write(str(self.key_path), API_KEY_TEMPLATE, create_backup=False)

    def load(self):
        """Loads keys from the BEJSON file."""
        try:
            self.data = bejson_core_load_file(str(self.key_path))
            idx_id = bejson_core_get_field_index(self.data, "slot_id")
            if idx_id == -1: idx_id = bejson_core_get_field_index(self.data, "key_slot")
            
            idx_key = bejson_core_get_field_index(self.data, "api_key")
            if idx_key == -1: idx_key = bejson_core_get_field_index(self.data, "key")
            
            self.slots = {}
            if idx_id != -1 and idx_key != -1:
                for row in self.data.get("Values", []):
                    self.slots[str(row[idx_id])] = row[idx_key]
        except Exception as e:
            # Fallback if load fails or file is empty
            self.slots = {}

    def save(self):
        """Saves the current slot data back to BEJSON."""
        if not self.data:
            self.data = copy.deepcopy(API_KEY_TEMPLATE)
        
        idx_id = bejson_core_get_field_index(self.data, "slot_id")
        idx_key = bejson_core_get_field_index(self.data, "api_key")
        idx_svc = bejson_core_get_field_index(self.data, "service")
        
        new_values = []
        for sid, key in self.slots.items():
            row = [None] * len(self.data["Fields"])
            row[idx_id] = sid
            row[idx_key] = key
            row[idx_svc] = "Gemini"
            new_values.append(row)
        
        self.data["Values"] = new_values
        bejson_core_atomic_write(str(self.key_path), self.data)

    def get_key(self, slot_id: Optional[str] = None) -> Optional[str]:
        """Returns a key. If slot_id is None, returns a random key."""
        if not self.slots:
            return None
        if slot_id and slot_id in self.slots:
            return self.slots[slot_id]
        return random.choice(list(self.slots.values()))

    def set_key(self, slot_id: str, key: str):
        """Sets or updates a key slot."""
        self.slots[slot_id] = key
        self.save()

    def get_active_count(self) -> int:
        return len(self.slots)

# --- Gemini Query Engine ---

class GeminiQuery:
    """Handles Gemini API interaction with Context and Policy support."""

    def __init__(self, key_manager: GeminiKeyManager, script_path: str, model: str = DEFAULT_MODEL):
        self.km = key_manager
        self.model = model
        self.script_dir = Path(script_path).resolve().parent if os.path.isfile(script_path) else Path(script_path).resolve()
        self.context_dir = self._init_context_dir()
        self.enabled_context_files = [] # List of filenames to include
        self.external_context_path = None
        self.use_external_context = False
        self.status_callback = None

    def _init_context_dir(self) -> Path:
        """Section 3A/3B: Initialize Context folder."""
        lc = self.script_dir / "context"
        uc = self.script_dir / "Context"
        if lc.exists() and lc.is_dir():
            return lc
        uc.mkdir(exist_ok=True)
        return uc

    def set_status_callback(self, callback: Callable[[str], None]):
        self.status_callback = callback

    def update_status(self, status: str):
        if self.status_callback:
            self.status_callback(status)
        else:
            print(f"[*] {status}")

    def get_available_context_files(self) -> List[str]:
        base = self.external_context_path if (self.use_external_context and self.external_context_path) else self.context_dir
        if not base or not base.exists(): return []
        return [f.name for f in base.iterdir() if f.is_file()]

    def query(self, prompt: str, system_instruction: Optional[str] = None, thinking: bool = False, google_search: bool = False) -> str:
        """Executes a Gemini query and returns a clean response."""
        
        # Section 5A: No key testing! Try at moment of generation.
        key = self.km.get_key()
        if not key:
            self.update_status("IDLE: Warning! No API Keys Detected!")
            return ""

        self.update_status("SENDING: Query dispatched, waiting...")

        # Section 3E: Attach Context
        context_data = ""
        base = self.external_context_path if (self.use_external_context and self.external_context_path) else self.context_dir
        
        for fname in self.enabled_context_files:
            fpath = base / fname
            if fpath.exists():
                try:
                    content = fpath.read_text(errors='ignore')
                    context_data += f"\n--- CONTEXT FILE: {fname} ---\n{content}\n--- END CONTEXT ---\n"
                except Exception:
                    pass

        if context_data:
            study_header = "The following attached files are for context and study only. DO NOT directly import or copy them. Study and learn from them to assist with the request. If you're writing, use it to write original content from what you learn."
            prompt = f"{study_header}\n\n{context_data}\n\nUSER REQUEST: {prompt}"

        # API Call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        # Add Google Search if enabled
        if google_search:
            payload["tools"] = [{"google_search": {}}]

        # Add Thinking if enabled (using 2026 standard thinking_config)
        if thinking:
            payload["generationConfig"] = payload.get("generationConfig", {})
            payload["generationConfig"]["thinking_config"] = {"include_thoughts": True}

        self.update_status("PROCESSING: Query Received, processing and awaiting response.")

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # Extract clean response
            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            else:
                return f"Error: No candidates returned. Raw: {json.dumps(data)}"
        except Exception as e:
            return f"Error during query: {str(e)}"

    def toggle_context_file(self, filename: str, state: bool):
        if state and filename not in self.enabled_context_files:
            self.enabled_context_files.append(filename)
        elif not state and filename in self.enabled_context_files:
            self.enabled_context_files.remove(filename)

    def set_external_context(self, path: str, enabled: bool = True):
        self.external_context_path = Path(path).resolve()
        self.use_external_context = enabled

# --- Module Functions ---

def get_engine_status(km: GeminiKeyManager) -> str:
    count = km.get_active_count()
    if count == 0:
        return "IDLE: Warning! No API Keys Detected!"
    return f"IDLE: ({count}) API Key Slots Active! System ready."

if __name__ == "__main__":
    # Self-test/Example
    km = GeminiKeyManager("test_keys.bejson.json")
    print(get_engine_status(km))
    # engine = GeminiQuery(km, __file__)
    # print(f"Context Dir: {engine.context_dir}")
