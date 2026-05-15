# Multi LLM Chat Flask - v2.0

GUI wrapper around the Multi_Llm_Cli_Suite prompter.py scripts.
All API logic stays in the CLI tools. Flask is pure UI + subprocess caller.

## Architecture

```
Flask UI  →  reads router.json  →  inspects BEJSON files (keys/model/profile)
          →  calls prompter.py as subprocess with --model / --profile args
          →  temporarily patches router.json if keys path overridden
          →  reads --output file for response
          →  logs to data/chat_log.104.bejson (BEJSON 104)
```

## Placement

Drop inside Multi_Llm_Cli_Suite/:

```
Multi_Llm_Cli_Suite/
├── gemini-cli/
├── groq-cli/
├── openrouter-cli/
├── huggingface-cli/
└── multi_llm_chat_flask/   ← here
```

## Run

```bash
pip install flask
python app.py
# → http://localhost:5050
```

Custom suite location:
```bash
export SUITE_ROOT=/path/to/Multi_Llm_Cli_Suite
python app.py
```

## Usage

1. Select a **service** → router.json auto-loads, showing all 3 routing paths
2. **Edit any path** to point at different BEJSON files on device:
   - KEYS FILE → your populated key registry
   - MODEL FILE → your model registry
   - PROFILE FILE → your system instruction profile
3. **INSPECT** buttons show key count, profile name/instruction
4. **LOAD MODELS** populates the model dropdown from the model file
5. Select a model, type message, **SEND**
6. Prompter stdout visible in collapsible "PROMPTER STDOUT" section

## Path Override Behavior

| Field | Passed as |
|-------|-----------|
| model_id | `--model <id>` arg (no router.json patch needed) |
| profile path | `--profile <path>` arg (no router.json patch needed) |
| keys path | temporary atomic router.json patch → restore after call |
