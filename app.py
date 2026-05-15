#!/usr/bin/env python3
"""
Multi LLM Chat Flask - v2.1
Description: GUI wrapper around Multi_Llm_Cli_Suite prompter.py scripts.
             Reads/overrides router.json routing pointers.  Does NOT re-implement
             any API logic — the prompter handles everything.
Author: Elton Boehnen
Site:   boehnenelton2024.pages.dev
"""

import os
import sys
import json
import tempfile
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent / "data"
LOG_FILE = DATA_DIR / "chat_log.104.bejson"
_SUITE_ROOT_FILE = DATA_DIR / "suite_root.txt"

def _load_suite_root() -> Path:
    if _SUITE_ROOT_FILE.exists():
        v = _SUITE_ROOT_FILE.read_text(encoding="utf-8").strip()
        if v:
            return Path(v)
    env = os.environ.get("SUITE_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent

SUITE_ROOT = _load_suite_root()

# Maps service id → relative CLI folder within SUITE_ROOT
SERVICE_CLI = {
    "gemini":      "gemini-cli",
    "groq":        "groq-cli",
    "openrouter":  "openrouter-cli",
    "huggingface": "huggingface-cli",
}

SERVICE_LABEL = {
    "gemini":      "Google Gemini",
    "groq":        "Groq",
    "openrouter":  "OpenRouter",
    "huggingface": "HuggingFace",
}

# Per-service lock so concurrent requests never corrupt a router.json mid-patch
_router_locks: dict[str, threading.Lock] = {k: threading.Lock() for k in SERVICE_CLI}

# ── BEJSON 104 LOG ────────────────────────────────────────────────────────────
_LOG_SCHEMA = {
    "Format": "BEJSON",
    "Format_Version": "104",
    "Format_Creator": "Elton Boehnen",
    "Records_Type": ["ChatLog"],
    "Fields": [
        {"name": "timestamp",  "type": "string"},
        {"name": "service",    "type": "string"},
        {"name": "model_id",   "type": "string"},
        {"name": "keys_file",  "type": "string"},
        {"name": "profile",    "type": "string"},
        {"name": "prompt",     "type": "string"},
        {"name": "response",   "type": "string"},
        {"name": "status",     "type": "string"},
    ],
    "Values": []
}

def _log_append(service, model_id, keys_file, profile, prompt, response, status):
    DATA_DIR.mkdir(exist_ok=True)
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = dict(_LOG_SCHEMA)
    data["Values"].append([
        datetime.now().isoformat(timespec="seconds"),
        service, model_id, keys_file, profile, prompt, response, status
    ])
    tmp = LOG_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.rename(LOG_FILE)

# ── BEJSON READERS ────────────────────────────────────────────────────────────
def _read_bejson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _field_index(data: dict, *candidates) -> int:
    names = [f["name"].lower() for f in data["Fields"]]
    for c in candidates:
        if c.lower() in names:
            return names.index(c.lower())
    raise KeyError(f"None of {candidates} found in Fields")

def inspect_keys(path: str) -> dict:
    """Return count of valid (non-placeholder) keys from a BEJSON key file."""
    data = _read_bejson(path)
    ki = _field_index(data, "key", "api_key")
    placeholders = {"YOUR_GEMINI_KEY", "YOUR_GROQ_KEY", "YOUR_OPENROUTER_KEY",
                    "YOUR_HUGGINGFACE_KEY", "KEY_HERE", "YOUR_KEY_HERE", ""}
    valid = [r[ki] for r in data["Values"] if r[ki] not in placeholders]
    total = len(data["Values"])
    return {"valid": len(valid), "total": total, "schema_name": data.get("Schema_Name", "?")}

def inspect_models(path: str) -> list:
    """Return list of {id, name, active} from a BEJSON model file."""
    data = _read_bejson(path)
    fields = [f["name"] for f in data["Fields"]]
    id_idx   = fields.index("model_id")
    act_idx  = fields.index("currently_active")
    name_idx = fields.index("model_name") if "model_name" in fields else -1
    result = []
    for row in data["Values"]:
        result.append({
            "id":     row[id_idx],
            "name":   row[name_idx] if name_idx != -1 else row[id_idx],
            "active": bool(row[act_idx]),
        })
    return result

def inspect_profile(path: str) -> dict:
    """Return profile metadata from a BEJSON profile file."""
    data = _read_bejson(path)
    fields = [f["name"].lower() for f in data["Fields"]]
    row = data["Values"][0]

    def get(*names):
        for n in names:
            if n.lower() in fields:
                return row[fields.index(n.lower())]
        return None

    return {
        "name":        get("name"),
        "archetype":   get("archetype"),
        "persona":     get("persona"),
        "instruction": get("systeminstruction", "system_instruction", "instruction"),
        "creativity":  get("creativity"),
        "formality":   get("formality"),
        "verbosity":   get("verbosity"),
        "tone":        get("tone"),
    }

# ── ROUTER.JSON HELPERS ───────────────────────────────────────────────────────
def _cli_dir(service: str) -> Path:
    return SUITE_ROOT / SERVICE_CLI[service]

def _router_path(service: str) -> Path:
    return _cli_dir(service) / "router.json"

def _read_router(service: str) -> dict:
    with open(_router_path(service), "r") as f:
        return json.load(f)

def _patch_router(service: str, overrides: dict):
    """Atomically write a modified router.json. overrides maps routing key → new path."""
    rpath = _router_path(service)
    router = _read_router(service)
    for key, val in overrides.items():
        router["routing"][key] = val
    tmp = rpath.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(router, f, indent=2)
    tmp.rename(rpath)

# ── SUBPROCESS RUNNER ────────────────────────────────────────────────────────
def _run_prompter(service: str, prompt: str, model_id: str,
                  keys_override: str | None, profile_override: str | None) -> tuple[str, str]:
    """
    Call the CLI prompter.py as a subprocess.
    Temporarily patches router.json for keys/model-file overrides (no CLI arg for those).
    Returns (response_text, stdout_log).
    """
    cli = _cli_dir(service)
    prompter = cli / "prompter.py"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        out_file = tf.name

    try:
        with _router_locks[service]:
            # Determine what needs patching
            router = _read_router(service)
            patches = {}
            if keys_override and keys_override != router["routing"].get("keys"):
                patches["keys"] = keys_override
            if patches:
                _patch_router(service, patches)

            # Build command
            cmd = [sys.executable, str(prompter), prompt, "--output", out_file]
            if model_id:
                cmd += ["--model", model_id]
            if profile_override:
                cmd += ["--profile", profile_override]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(cli),
            )

            # Restore any patches
            if patches:
                restore = {k: router["routing"][k] for k in patches}
                _patch_router(service, restore)

        stdout_log = (result.stdout or "") + (result.stderr or "")

        # Read the response from output file
        out_path = Path(out_file)
        if out_path.exists():
            response = out_path.read_text(encoding="utf-8").strip()
        else:
            response = ""

        if not response:
            # Fallback: scrape response from stdout
            lines = stdout_log.splitlines()
            capture = False
            captured = []
            for line in lines:
                if "RESPONSE" in line.upper() and "===" in line:
                    capture = not capture
                    continue
                if capture:
                    captured.append(line)
            response = "\n".join(captured).strip()

        if not response and result.returncode != 0:
            raise RuntimeError(f"Prompter exited {result.returncode}:\n{stdout_log[-800:]}")

        return response, stdout_log

    finally:
        try:
            Path(out_file).unlink(missing_ok=True)
        except Exception:
            pass

@app.route("/api/config", methods=["GET"])
def api_config_get():
    return jsonify({"suite_root": str(SUITE_ROOT)})


@app.route("/api/config", methods=["POST"])
def api_config_set():
    global SUITE_ROOT
    body = request.get_json(force=True)
    new_root = body.get("suite_root", "").strip()
    if not new_root:
        return jsonify({"error": "suite_root is empty"}), 400
    DATA_DIR.mkdir(exist_ok=True)
    _SUITE_ROOT_FILE.write_text(new_root, encoding="utf-8")
    SUITE_ROOT = Path(new_root)
    return jsonify({"suite_root": str(SUITE_ROOT), "ok": True})


# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    services = [{"id": k, "label": v} for k, v in SERVICE_LABEL.items()]
    return render_template("index.html", services=services, suite_root=str(SUITE_ROOT))


@app.route("/api/router")
def api_router():
    """Return the router.json for a service, with CLI dir and prompter existence check."""
    service = request.args.get("service", "")
    if service not in SERVICE_CLI:
        return jsonify({"error": "Unknown service"}), 400
    cli = _cli_dir(service)
    rpath = _router_path(service)
    if not rpath.exists():
        return jsonify({"error": f"router.json not found: {rpath}"}), 404
    router = _read_router(service)
    return jsonify({
        "cli_dir":      str(cli),
        "prompter":     str(cli / "prompter.py"),
        "prompter_ok":  (cli / "prompter.py").exists(),
        "routing":      router.get("routing", {}),
        "settings":     router.get("settings", {}),
    })


@app.route("/api/inspect/keys")
def api_inspect_keys():
    path = request.args.get("path", "")
    if not path or not Path(path).exists():
        return jsonify({"error": f"File not found: {path}"}), 404
    try:
        return jsonify(inspect_keys(path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/inspect/models")
def api_inspect_models():
    path = request.args.get("path", "")
    if not path or not Path(path).exists():
        return jsonify({"error": f"File not found: {path}"}), 404
    try:
        return jsonify(inspect_models(path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/inspect/profile")
def api_inspect_profile():
    path = request.args.get("path", "")
    if not path or not Path(path).exists():
        return jsonify({"error": f"File not found: {path}"}), 404
    try:
        return jsonify(inspect_profile(path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/send", methods=["POST"])
def api_send():
    body = request.get_json(force=True)
    service          = body.get("service", "").strip()
    model_id         = body.get("model_id", "").strip()
    message          = body.get("message", "").strip()
    keys_override    = body.get("keys_path", "").strip() or None
    profile_override = body.get("profile_path", "").strip() or None

    if not service or service not in SERVICE_CLI:
        return jsonify({"error": f"Unknown service: {service}"}), 400
    if not model_id:
        return jsonify({"error": "No model selected"}), 400
    if not message:
        return jsonify({"error": "Message is empty"}), 400

    cli = _cli_dir(service)
    if not (cli / "prompter.py").exists():
        return jsonify({"error": f"prompter.py not found at: {cli}"}), 500

    try:
        response, stdout_log = _run_prompter(
            service, message, model_id, keys_override, profile_override
        )
        _log_append(service, model_id,
                    keys_override or "default",
                    profile_override or "default",
                    message, response, "OK")
        return jsonify({"response": response, "log": stdout_log, "status": "OK"})
    except Exception as e:
        err = str(e)
        _log_append(service, model_id,
                    keys_override or "default",
                    profile_override or "default",
                    message, err, "ERROR")
        return jsonify({"error": err, "status": "ERROR"}), 500


@app.route("/api/log")
def api_log():
    if not LOG_FILE.exists():
        return jsonify(dict(_LOG_SCHEMA))
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    print(f"[*] SUITE ROOT : {SUITE_ROOT}")
    for svc, folder in SERVICE_CLI.items():
        cli = SUITE_ROOT / folder
        ok = "OK" if (cli / "prompter.py").exists() else "NOT FOUND"
        print(f"[*] {svc:12s}: {cli}  [{ok}]")
    app.run(host="0.0.0.0", port=5050, debug=True)
