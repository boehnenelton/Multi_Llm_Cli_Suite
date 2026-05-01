#!/usr/bin/env python3
"""
Orchestrator: prompter.py (OpenRouter)
Description: CLI engine for standardized OpenRouter queries via BEJSON schemas.
             Handles Round Robin keys, rate limits, and failure cooldowns.
             2026 Update: Supports Gemma 4 <|turn|> format and Thinking mode.
"""
import sys
import os
import json
import time
import requests
import argparse
import random
from pathlib import Path

# Setup Path for local libs
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "lib"))

try:
    from lib_bejson_core import bejson_core_load_file
    from lib_mfdb_core import mfdb_core_smart_repair
    from lib_mfdb_validator import MFDBValidationError
except ImportError:
    print("CRITICAL: Local libraries not found in lib/")
    sys.exit(1)

# Persistent State for CLI Session (in-memory for this run)
class OrchestratorState:
    current_key_idx = 0
    last_request_time = 0
    consecutive_errors = 0
    cooldown_until = 0
    is_initialized = False

state = OrchestratorState()

def safe_load_config(file_path):
    """Load a BEJSON config with v1.21 Self-Healing support."""
    try:
        return bejson_core_load_file(str(file_path))
    except (MFDBValidationError, Exception) as e:
        if hasattr(e, "code") and e.code in (33, 37, 38):
            print(f"[*] Inconsistency in {os.path.basename(file_path)} (Error {e.code}). Attempting repair...")
            if mfdb_core_smart_repair(str(file_path), e):
                print(f"[+] Repair successful. Reloading {os.path.basename(file_path)}...")
                return bejson_core_load_file(str(file_path))
        raise e

def initialize_state(pool_size):
    if not state.is_initialized and pool_size > 0:
        state.current_key_idx = random.randint(0, pool_size - 1)
        state.is_initialized = True
        print(f"[*] Initialized session at random Key Slot {state.current_key_idx + 1}")

def load_router():
    with open(BASE_DIR / "router.json", "r") as f:
        return json.load(f)

def get_active_model(model_path, search_id=None):
    p = Path(model_path)
    full_path = p if p.is_absolute() else BASE_DIR / model_path
    data = safe_load_config(full_path)
    fields = [f["name"] for f in data["Fields"]]
    m_id_idx = fields.index("model_id")
    active_idx = fields.index("currently_active")
    
    # Try to get new fields, fallback to False if they don't exist
    try:
        think_idx = fields.index("thinking_enabled")
    except ValueError:
        think_idx = -1
    
    for row in data["Values"]:
        if search_id:
            if row[m_id_idx] == search_id:
                return {
                    "id": row[m_id_idx],
                    "thinking": row[think_idx] if think_idx != -1 else False
                }
        elif row[active_idx] is True:
            return {
                "id": row[m_id_idx],
                "thinking": row[think_idx] if think_idx != -1 else False
            }
    
    if search_id:
        return {"id": search_id, "thinking": False}
    return {"id": "liquid/lfm-2.5-1.2b-thinking:free", "thinking": True} # Fallback

def get_keys(key_path):
    # Handle absolute paths for secure keys (e.g. in ~/.env)
    p = Path(key_path)
    full_path = p if p.is_absolute() else BASE_DIR / key_path
    data = safe_load_config(full_path)
    fields = [f["name"] for f in data["Fields"]]
    k_idx = -1
    for i, f in enumerate(data["Fields"]):
        if f["name"] in ("key", "api_key"):
            k_idx = i
            break
    
    if k_idx == -1: return []
    return [row[k_idx] for row in data["Values"] if "YOUR_OPENROUTER_KEY" not in str(row[k_idx]) and "KEY_HERE" not in str(row[k_idx])]

def get_profile(profile_path):
    p = Path(profile_path)
    full_path = p if p.is_absolute() else BASE_DIR / profile_path
    data = safe_load_config(full_path)
    fields = [f["name"].lower() for f in data["Fields"]]
    
    # Support both legacy snake_case and new PascalCase
    instr_idx = -1
    for target in ["systeminstruction", "system_instruction", "instruction"]:
        if target in fields:
            instr_idx = fields.index(target)
            break
            
    if instr_idx == -1:
        raise ValueError(f"Instruction field not found in profile: {profile_path}")
        
    return data["Values"][0][instr_idx]

def send_query(prompt, router, model_override=None, output_file=None):
    now = time.time()
    
    # 1. Check Cooldown
    if state.cooldown_until > now:
        rem = int((state.cooldown_until - now) / 60) + 1
        print(f"[-] System on COOLDOWN. Wait {rem} minute(s).")
        return False

    # 2. Check Delay
    delay = router["settings"]["request_delay_seconds"]
    diff = now - state.last_request_time
    if diff < delay:
        wait = int(delay - diff)
        print(f"[*] Rate limit: Sleeping for {wait}s...")
        time.sleep(wait)

    # 3. Load Configs
    model_cfg = get_active_model(router["routing"]["model"], search_id=model_override)
    
    model_id = model_cfg["id"]
    keys = get_keys(router["routing"]["keys"])
    system_instruction = get_profile(router["routing"]["profile"])
    
    if not keys:
        print("[-] No valid keys found in registry.")
        return False

    initialize_state(len(keys))
    print(f"[*] Preparing query (Model: {model_id})")
    if model_cfg["thinking"]: print("[*] Feature: Thinking ENABLED")
    
    state.last_request_time = time.time()
    
    attempts = 0
    pool_errors = 0
    
    while attempts < len(keys):
        key = keys[state.current_key_idx]
        key_num = state.current_key_idx + 1
        
        # Advance for next time
        state.current_key_idx = (state.current_key_idx + 1) % len(keys)
        attempts += 1
        
        print(f"[*] Sending via Key {key_num}/{len(keys)}...")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/boehnenelton/cli_openrouter",
            "X-Title": "Gemini CLI OpenRouter Tool"
        }
        
        # --- 2026 Gemma Formatting ---
        # If it's a Gemma 4 or Gemma 3 model, we combine system and user roles
        # to bypass "Developer instruction not enabled" errors from certain bridges.
        is_gemma_modern = "google/gemma-4" in model_id or "google/gemma-3" in model_id
        
        if is_gemma_modern:
            full_prompt = f"{system_instruction}\n\n{prompt}"
            messages = [{"role": "user", "content": full_prompt}]
        else:
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]

        payload = {
            "model": model_id,
            "messages": messages
        }

        # Handle Thinking if enabled
        if model_cfg["thinking"]:
            payload["include_thoughts"] = True

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                text = ""
                # Robust content extraction
                if "message" in choice and choice["message"] is not None:
                    if "content" in choice["message"] and choice["message"]["content"] is not None:
                        text = choice["message"]["content"].strip()
                
                # Check for thoughts/reasoning in 2026 format
                thoughts = ""
                if "message" in choice and choice["message"] is not None:
                    if "reasoning" in choice["message"] and choice["message"]["reasoning"] is not None:
                        thoughts = choice["message"]["reasoning"].strip()
                    elif "thought" in choice["message"] and choice["message"]["thought"] is not None:
                        thoughts = choice["message"]["thought"].strip()
                
                if not thoughts and "thought" in choice and choice["thought"] is not None:
                    thoughts = choice["thought"].strip()

                if output_file:
                    with open(output_file, "w") as f:
                        if thoughts: f.write(f"<thought>\n{thoughts}\n</thought>\n\n")
                        f.write(text)
                    print(f"[+] Response saved to {output_file}")
                else:
                    print("\n=== OPENROUTER RESPONSE ===\n")
                    if thoughts:
                        print(f"THOUGHTS:\n{thoughts}\n")
                    print(text if text else "(Empty response content)")
                    print("\n===========================\n")
                state.consecutive_errors = 0
                return True
            else:
                raise Exception("No choices returned")

        except Exception as e:
            # Security: Mask key in error message
            err_msg = str(e)
            if key in err_msg:
                err_msg = err_msg.replace(key, "REDACTED_KEY")
                
            # If we get a response-level error, show the body for debugging (masked)
            if hasattr(e, 'response') and e.response is not None:
                resp_text = e.response.text
                if key in resp_text: resp_text = resp_text.replace(key, "REDACTED_KEY")
                print(f"[-] API Error Body: {resp_text}")

            print(f"[-] Key {key_num} FAILED: {err_msg}")
            pool_errors += 1
            state.consecutive_errors += 1
            
            if pool_errors >= 2:
                print("[-] Prompt HALTED: 2 keys failed in a row.")
                break
                
            if state.consecutive_errors >= router["settings"]["consecutive_error_limit"]:
                state.cooldown_until = time.time() + (router["settings"]["cooldown_minutes"] * 60)
                print(f"[-] Global TIMEOUT triggered.")
                break
    return False

def main():
    parser = argparse.ArgumentParser(description="OpenRouter Standardized Prompter")
    parser.add_argument("prompt", nargs="?", help="The prompt string")
    parser.add_argument("--model", help="Override the active model ID")
    parser.add_argument("--profile", help="Override the active profile path")
    parser.add_argument("--output", help="Save response to this file")
    
    args = parser.parse_args()
    router = load_router()
    
    # Arg Overrides
    model_override = args.model
    if args.profile:
        router["routing"]["profile"] = args.profile
    
    # v1.21 Self-Healing Health Check
    print("[*] Running v1.21 System Health Check...")
    try:
        get_active_model(router["routing"]["model"], search_id=model_override)
        get_keys(router["routing"]["keys"])
        get_profile(router["routing"]["profile"])
        print("[+] Health Check: OK")
    except Exception as e:
        print(f"[!] Health Check FAILED: {e}")
        print("[!] Attempting to proceed anyway...")
    
    if args.prompt:
        send_query(args.prompt, router, model_override, args.output)
    else:
        print("Usage: python3 prompter.py \"prompt\" [--model model_id] [--output file.txt]")

if __name__ == "__main__":
    main()
