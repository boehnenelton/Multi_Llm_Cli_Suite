#!/usr/bin/env python3
"""
Orchestrator: menu_prompter.py
Description: Interactive configuration and prompting menu for Gemini CLI.
             Manages Keys, Models (Thinking/Search), and Profiles.
"""
import os
import sys
import json
import time
from pathlib import Path

# Setup Path for local libs
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "lib"))

try:
    from lib_bejson_core import bejson_core_load_file, bejson_core_atomic_write
    from lib_bejson_validator import bejson_validator_validate_file
except ImportError:
    print("CRITICAL: Local libraries not found in lib/")
    sys.exit(1)

# Import send_query logic from prompter
from prompter import send_query, load_router

ROUTER_PATH = BASE_DIR / "router.json"

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def load_bejson(path):
    try:
        return bejson_core_load_file(str(path))
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None

def save_bejson(path, data):
    try:
        bejson_core_atomic_write(str(path), data)
        print(f"[+] Successfully updated {os.path.basename(path)}")
        return True
    except Exception as e:
        print(f"[-] Failed to save {path}: {e}")
        return False

def execute_prompt():
    clear_screen()
    print("=== EXECUTE PROMPT ===")
    print("Enter your prompt below. To finish and send, press ENTER three times (3 empty lines).")
    print("-" * 40)
    
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line.strip() == "":
                empty_count += 1
            else:
                empty_count = 0
            
            lines.append(line)
            
            if empty_count >= 3:
                break
        except EOFError:
            break
            
    prompt = "\n".join(lines).strip()
    if not prompt:
        print("\n[!] Prompt is empty. Aborting.")
        input("\nPress Enter to return...")
        return

    print("\n[*] Sending query...")
    router = load_router()
    # Note: send_query prints the response itself
    success = send_query(prompt, router)
    if not success:
        print("[-] Query failed.")
    
    input("\nPress Enter to return...")

def manage_keys():
    clear_screen()
    print("=== KEY CONFIGURATION ===")
    router = load_router()
    if not router: return
    
    key_path = BASE_DIR / router["routing"]["keys"]
    data = load_bejson(key_path)
    if not data: return

    fields = [f["name"] for f in data["Fields"]]
    slot_idx = fields.index("key_slot")
    val_idx = fields.index("key")

    print("\nCurrent Slots:")
    for row in data["Values"]:
        print(f"Slot {row[slot_idx]}: {row[val_idx][:10]}...")

    try:
        choice = input("\nSelect Slot ID to update (or Enter to cancel): ")
        if not choice: return
        choice = int(choice)
        
        found = False
        for row in data["Values"]:
            if row[slot_idx] == choice:
                new_key = input(f"Enter new key for Slot {choice}: ").strip()
                if new_key:
                    row[val_idx] = new_key
                    save_bejson(key_path, data)
                found = True
                break
        
        if not found:
            new_key = input(f"Slot {choice} not found. Create it? (y/n): ").lower()
            if new_key == 'y':
                key_val = input(f"Enter key for Slot {choice}: ").strip()
                data["Values"].append([choice, key_val])
                save_bejson(key_path, data)
    except ValueError:
        print("Invalid input.")
    input("\nPress Enter to return...")

def manage_models():
    clear_screen()
    print("=== MODEL CONFIGURATION (Thinking & Search) ===")
    router = load_router()
    if not router: return
    
    model_path = BASE_DIR / router["routing"]["model"]
    data = load_bejson(model_path)
    if not data: return

    fields = [f["name"] for f in data["Fields"]]
    name_idx = fields.index("model_name")
    id_idx = fields.index("model_id")
    active_idx = fields.index("currently_active")
    
    # Try to get new fields
    try:
        think_idx = fields.index("thinking_enabled")
        search_idx = fields.index("google_search_enabled")
    except ValueError:
        print("[-] Error: Model schema missing thinking/search fields.")
        input("\nPress Enter to return...")
        return

    print("\nAvailable Models:")
    for i, row in enumerate(data["Values"]):
        status = "[ACTIVE]" if row[active_idx] else "        "
        think = "T" if row[think_idx] else "-"
        search = "S" if row[search_idx] else "-"
        print(f"{i+1}. {status} {row[name_idx]} ({row[id_idx]}) [Flags: {think}{search}]")

    try:
        choice = input("\nSelect model to set as ACTIVE (or Enter to cancel): ")
        if not choice: return
        choice = int(choice)
        if choice > len(data["Values"]): return
        
        for i, row in enumerate(data["Values"]):
            row[active_idx] = (i == choice - 1)
        
        save_bejson(model_path, data)
    except ValueError:
        print("Invalid input.")
    input("\nPress Enter to return...")

def manage_profiles():
    clear_screen()
    print("=== PROFILE CONFIGURATION ===")
    config_dir = BASE_DIR / "configuration"
    profiles = []
    
    print("\nScanning and Validating Profiles...")
    for f in config_dir.glob("*.bejson"):
        if "template" in f.name or "key" in f.name:
            continue
            
        try:
            bejson_validator_validate_file(str(f))
            profiles.append(f)
        except Exception as e:
            print(f"[!] Skipping {f.name}: Invalid BEJSON ({e})")

    if not profiles:
        print("No valid profiles found.")
        input("\nPress Enter to return...")
        return

    router = load_router()
    current_profile = router["routing"]["profile"]

    print("\nValid Profiles:")
    for i, p in enumerate(profiles):
        rel_path = f"configuration/{p.name}"
        status = "[ACTIVE]" if rel_path == current_profile else "        "
        print(f"{i+1}. {status} {p.name}")

    try:
        choice = input("\nSelect profile to set as ACTIVE (or Enter to cancel): ")
        if not choice: return
        choice = int(choice)
        if choice > len(profiles): return
        
        new_profile = f"configuration/{profiles[choice-1].name}"
        router["routing"]["profile"] = new_profile
        
        with open(ROUTER_PATH, "w") as f:
            json.dump(router, f, indent=2)
        print(f"[+] Router updated to use {profiles[choice-1].name}")
    except ValueError:
        print("Invalid input.")
    input("\nPress Enter to return...")

def save_configuration():
    clear_screen()
    print("=== SAVE CONFIGURATION ===")
    print("[*] Running System Validation...")
    router = load_router()
    try:
        # Validate all paths in router
        for key in ["profile", "model", "keys"]:
            path = BASE_DIR / router["routing"][key]
            if not path.exists():
                print(f"[-] ERROR: Missing file {path}")
            else:
                load_bejson(path)
                print(f"[+] Verified {key}: {router['routing'][key]}")
        print("\n[SUCCESS] Configuration is healthy and saved.")
    except Exception as e:
        print(f"[-] Health Check Failed: {e}")
    
    input("\nPress Enter to return...")

def config_submenu():
    while True:
        clear_screen()
        print("=== CONFIGURATION MANAGEMENT ===")
        print("1. Key Configuration")
        print("2. Model (Thinking/Search) Configuration")
        print("3. Profile Configuration")
        print("4. Back to Main Menu")
        
        choice = input("\nSelect an option: ")
        if choice == '1':
            manage_keys()
        elif choice == '2':
            manage_models()
        elif choice == '3':
            manage_profiles()
        elif choice == '4':
            break

def main():
    while True:
        clear_screen()
        print("=== GEMINI CLI MENU PROMPTER ===")
        print("1. Save Configuration")
        print("2. Execute Prompt (Multi-line)")
        print("3. Configure Settings")
        print("4. Exit")
        
        choice = input("\nSelect an option: ")
        if choice == '1':
            save_configuration()
        elif choice == '2':
            execute_prompt()
        elif choice == '3':
            config_submenu()
        elif choice == '4':
            print("Exiting...")
            break

if __name__ == "__main__":
    main()
