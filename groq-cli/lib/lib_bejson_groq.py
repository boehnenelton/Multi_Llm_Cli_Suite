"""
Library:     lib_bejson_groq.py
MFDB Version: 1.3.1
Format_Creator: Elton Boehnen
Status:      OFFICIAL - v1.3.1
Date:        2026-05-06
"""
"""
Library:     lib_bejson_groq.py
Family:      AI
Jurisdiction: ["PYTHON", "CORE_COMMAND", "GROQ_STANDARD"]
Status:      OFFICIAL_STANDARD
Author:      Elton Boehnen
Version:     1.5 OFFICIAL
Date:        2026-05-01
Description: Unified Groq standard library for BEJSON 104/104a.
             Schemas are EMBEDDED to ensure global consistency.
             Integrates Key Registry, Model Registry, and AI Profiles.
"""

import os
import sys
import json
import time
import requests
import random
import copy
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# --- EMBEDDED SCHEMAS (THE GLOBAL STANDARD) ---

SCHEMA_KEY_REGISTRY = {
    "Format": "BEJSON",
    "Format_Version": "104a",
    "Format_Creator": "Elton Boehnen",
    "Schema_Name": "GroqKeyRegistry",
    "Records_Type": ["ApiKey"],
    "Fields": [
        {"name": "key_slot", "type": "integer"},
        {"name": "key", "type": "string"}
    ],
    "Values": []
}

SCHEMA_MODEL_REGISTRY = {
    "Format": "BEJSON",
    "Format_Version": "104a",
    "Format_Creator": "Elton Boehnen",
    "Schema_Name": "GroqModelRegistry",
    "Records_Type": ["GroqModel"],
    "Fields": [
        {"name": "model_name", "type": "string"},
        {"name": "model_id", "type": "string"},
        {"name": "currently_active", "type": "boolean"}
    ],
    "Values": [
        ["Llama 3.3 70B Versatile", "llama-3.3-70b-versatile", True],
        ["Llama 3.1 8B Instant", "llama-3.1-8b-instant", False],
        ["Mixtral 8x7b Instruct", "mixtral-8x7b-32768", False],
        ["Gemma 2 9b It", "gemma2-9b-it", False]
    ]
}

# Profile schema is standardized across LLMs in 2026
SCHEMA_AI_PROFILE = {
    "Format": "BEJSON",
    "Format_Version": "104",
    "Format_Creator": "Elton Boehnen",
    "Records_Type": ["AI_Profile"],
    "Parent_Hierarchy": "/LLM_Configuration",
    "Fields": [
        {"name": "Record_Type_Parent", "type": "string"},
        {"name": "Name", "type": "string"},
        {"name": "Archetype", "type": "string"},
        {"name": "Persona", "type": "string"},
        {"name": "SystemInstruction", "type": "string"},
        {"name": "ForbiddenTopics", "type": "array"},
        {"name": "Avatar_Type", "type": "string"},
        {"name": "Avatar_sourceUrl", "type": "string"},
        {"name": "Avatar_Data", "type": "string"},
        {"name": "MaxResponseTokens", "type": "integer"},
        {"name": "Creativity", "type": "number"},
        {"name": "Tone", "type": "array"},
        {"name": "Formality", "type": "string"},
        {"name": "Verbosity", "type": "string"},
        {"name": "EmotionalExpression_Enabled", "type": "boolean"},
        {"name": "EmotionalExpression_Intensity", "type": "number"},
        {"name": "GoogleSearch_Enabled", "type": "boolean"},
        {"name": "CodeInterpreter_Enabled", "type": "boolean"},
        {"name": "EphemeralMemory", "type": "boolean"},
        {"name": "CodeParsing_Mode", "type": "string"},
        {"name": "CodeParsing_Languages", "type": "array"},
        {"name": "CodeParsing_StructureValidation", "type": "boolean"},
        {"name": "CodeParsing_VersionControl", "type": "boolean"},
        {"name": "Thinking_Supported", "type": "boolean"}
    ],
    "Values": [
        [
            "AI_Profile",
            "Groq_Standard",
            "Assistant",
            "A helpful and professional AI assistant.",
            "You are a helpful assistant. Provide clear, accurate, and concise information.",
            [], "Emoji", "", "⚡", 32768, 0.7, ["Professional", "Helpful"], "Formal", "Balanced", 
            False, 0.0, False, True, True, "complete", ["python", "javascript"], True, True, False
        ]
    ]
}

# --- Environment & Setup ---

LIB_DIR = os.environ.get("BEJSON_LIB_DIR", str(Path(__file__).resolve().parent))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

try:
    from lib_bejson_core import bejson_core_load_file, bejson_core_get_field_index, bejson_core_atomic_write
except ImportError:
    def bejson_core_load_file(p):
        with open(p, 'r') as f: return json.load(f)
    def bejson_core_get_field_index(d, n):
        for i, f in enumerate(d.get("Fields", [])):
            if f["name"] == n: return i
        return -1
    def bejson_core_atomic_write(p, d):
        with open(p, 'w') as f: json.dump(d, f, indent=2)

# --- Registry Managers ---

class GroqKeyRegistry:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.keys = []
        if not self.file_path.exists():
            self.create_default()
        self.load()

    def create_default(self):
        bejson_core_atomic_write(str(self.file_path), SCHEMA_KEY_REGISTRY)

    def load(self):
        try:
            data = bejson_core_load_file(str(self.file_path))
            idx = bejson_core_get_field_index(data, "key")
            if idx != -1:
                self.keys = [row[idx] for row in data["Values"] if "YOUR_GROQ_KEY" not in str(row[idx]) and "KEY_HERE" not in str(row[idx])]
        except Exception:
            self.keys = []

class GroqModelRegistry:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.models = []
        self.active_model_id = "llama-3.3-70b-versatile"
        if not self.file_path.exists():
            self.create_default()
        self.load()

    def create_default(self):
        bejson_core_atomic_write(str(self.file_path), SCHEMA_MODEL_REGISTRY)

    def load(self):
        try:
            data = bejson_core_load_file(str(self.file_path))
            fields = [f["name"] for f in data["Fields"]]
            id_idx = fields.index("model_id")
            active_idx = fields.index("currently_active")
            
            self.models = []
            for row in data["Values"]:
                m_info = {"id": row[id_idx]}
                self.models.append(m_info)
                if row[active_idx] is True:
                    self.active_model_id = row[id_idx]
        except Exception:
            for row in SCHEMA_MODEL_REGISTRY["Values"]:
                self.models.append({"id": row[1]})

    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        target_id = model_id or self.active_model_id
        for m in self.models:
            if m["id"] == target_id: return m
        return {"id": target_id}

class GroqProfile:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.instruction = ""
        self.config = {}
        if not self.file_path.exists():
            self.create_default()
        self.load()

    def create_default(self):
        bejson_core_atomic_write(str(self.file_path), SCHEMA_AI_PROFILE)

    def load(self):
        try:
            data = bejson_core_load_file(str(self.file_path))
            fields = [f["name"] for f in data["Fields"]]
            instr_idx = fields.index("SystemInstruction")
            self.instruction = data["Values"][0][instr_idx]
            self.config = {f["name"]: data["Values"][0][i] for i, f in enumerate(data["Fields"])}
        except Exception:
            self.instruction = SCHEMA_AI_PROFILE["Values"][0][4]
            self.config = {f["name"]: SCHEMA_AI_PROFILE["Values"][0][i] for i, f in enumerate(SCHEMA_AI_PROFILE["Fields"])}

# --- Unified Prompter Engine ---

class GroqStandardPrompter:
    def __init__(
        self, 
        key_registry_path: Union[str, Path],
        model_registry_path: Union[str, Path],
        profile_path: Union[str, Path]
    ):
        self.key_reg = GroqKeyRegistry(key_registry_path)
        self.model_reg = GroqModelRegistry(model_registry_path)
        self.profile = GroqProfile(profile_path)
        self.current_key_idx = 0
        self.last_request_time = 0
        self.request_delay = 1.0

    def _get_next_key(self) -> Optional[str]:
        keys = self.key_reg.keys
        if not keys: return None
        key = keys[self.current_key_idx]
        self.current_key_idx = (self.current_key_idx + 1) % len(keys)
        return key

    def prompt(self, user_input: str, model_id: Optional[str] = None) -> str:
        now = time.time()
        diff = now - self.last_request_time
        if diff < self.request_delay: time.sleep(self.request_delay - diff)
        
        key = self._get_next_key()
        if not key: return "ERROR: No valid API keys."

        m_info = self.model_reg.get_model_info(model_id)
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": m_info["id"],
            "messages": [
                {"role": "system", "content": self.profile.instruction},
                {"role": "user", "content": user_input}
            ],
            "max_tokens": self.profile.config.get("MaxResponseTokens", 32768),
            "temperature": self.profile.config.get("Creativity", 0.7)
        }

        self.last_request_time = time.time()
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=90)
            res.raise_for_status()
            data = res.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"].strip()
            return f"ERROR: No choices. {json.dumps(data)}"
        except Exception as e:
            return f"ERROR: {str(e)}"

# --- Global Standard Paths (2026) ---

STD_KEY_PATH = "/Data/Data/com.termux/files/home/.env/groq_keys.bejson"
STD_MODEL_PATH = "{SC_ROOT}/Schemas/groq_model_registry.104a.bejson"
STD_PROFILE_PATH = "{SC_ROOT}/Schemas/groq_standard_profile.bejson"

def get_standard_prompter():
    return GroqStandardPrompter(STD_KEY_PATH, STD_MODEL_PATH, STD_PROFILE_PATH)
