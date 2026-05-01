# Multi-LLM CLI Suite 2026
## Unified Terminal Interface for Gemini, Groq, and OpenRouter

Welcome to the **Multi-LLM CLI Suite**, a production-grade toolkit designed for high-reasoning model interaction, secure key management, and automated documentation research. This suite consolidates three distinct CLI tools and a specialized research skill into a single, portable repository.

---

## 📑 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Security & BEJSON 104a](#security--bejson-104a)
3. [Toolkit Components](#toolkit-components)
    - [Gemini CLI](#gemini-cli)
    - [Groq CLI](#groq-cli)
    - [OpenRouter CLI](#openrouter-cli)
4. [Skills: GH-Docs-Researcher](#skills-gh-docs-researcher)
5. [Installation & Setup](#installation--setup)
6. [Usage Guide](#usage-guide)
7. [Advanced Features](#advanced-features)
8. [Standardization & Compliance](#standardization--compliance)

---

## 🏛 Architecture Overview
The Multi-LLM CLI Suite is built on the principle of **Secure Decoupling**. Unlike traditional CLI tools that store configuration and keys in flat \`.env\` files or hardcoded strings, this suite utilizes the **BEJSON 104a** standard for all structured data.

### Core Philosophy:
- **Registry-First:** All API keys are stored in encrypted or protected BEJSON registries outside the repository path.
- **Model Standardized:** Built-in support for the 2026 standardized model lineups (Gemini 2.5/3.1, Liquid LFM, Gemma 3/4).
- **Thinking-Aware:** Natively parses and displays "Thinking" or "Reasoning" blocks from models like \`liquid/lfm-2.5-1.2b-thinking\`.

---

## 🔐 Security & BEJSON 104a
Security is the cornerstone of this toolkit. Every tool in this suite adheres to the following mandates:

### 1. Centralized Key Management
API keys are never stored within the tool's directory. Instead, they are referenced via a \`router.json\` that points to a centralized BEJSON registry:
- **Gemini:** \`~/.env/gemini_keys.bejson\`
- **Groq:** \`~/.env/groq_keys.bejson\`
- **OpenRouter:** \`~/.env/openrouter_keys.bejson\`

### 2. The BEJSON 104a Standard
BEJSON (Boehnen Elton JSON) 104a is a schema-validated format designed by Elton Boehnen. It ensures that every configuration file has:
- A mandatory \`Format\` and \`Format_Version\`.
- \`Fields\` definitions for type safety.
- \`Records_Type\` to prevent data corruption.

Example Template:
\`\`\`json
{
  "Format": "BEJSON",
  "Format_Version": "104a",
  "Schema_Name": "ApiKeyRegistry",
  "Fields": [{"name": "key_slot", "type": "integer"}, {"name": "key", "type": "string"}],
  "Values": [[1, "YOUR_KEY_HERE"]]
}
\`\`\`

---

## 🛠 Toolkit Components

### ♊ Gemini CLI (\`gemini-cli\`)
The flagship CLI for Google's Gemini models.
- **Capabilities:** Supports multimodal inputs, long-context window management, and strict schema adherence.
- **2026 Models:** Defaulting to \`gemini-2.5-flash\` and \`gemini-3.1-pro-preview\`.
- **Key Feature:** Randomized key slot rotation to prevent rate-limiting across multiple free-tier keys.

### ⚡ Groq CLI (\`groq-cli\`)
Optimized for the fastest inference speeds on the market.
- **Capabilities:** Ultra-low latency responses using Llama 3.x and Mixtral models.
- **Integration:** Perfect for real-time pipeline automation where speed is critical.
- **Health Checks:** Includes a \`run_tests.sh\` suite to verify connectivity and latency.

### 🌐 OpenRouter CLI (\`openrouter-cli\`)
The "Swiss Army Knife" of LLM access, providing a unified API for hundreds of models.
- **2026 Update:** Fully compatible with Liquid and Gemma 4 models.
- **Specialized Formatting:** Automatically handles "Developer Instruction" errors for Gemma 3/4 by wrapping system prompts into the first user turn.
- **Thinking Support:** Dedicated logic to handle and display \`thought\` fields in model responses.

---

## 🔍 Skills: GH-Docs-Researcher
The \`gh-docs-researcher\` is a specialized skill that extends the capabilities of any Gemini-CLI instance.

### Features:
- **Automated Discovery:** Searches for official documentation repositories on GitHub based on project names.
- **Shallow Cloning:** Uses \`--depth 1\` to minimize storage impact while retaining full documentation context.
- **Resource Indexing:** Automatically identifies and indexes \`README.md\`, \`/docs\`, and \`/examples\` directories.
- **Standard Pathing:** Clones to \`/storage/emulated/0/Documents/<project>\` to maintain a clean workspace.

---

## 🚀 Installation & Setup

### Prerequisites:
- Python 3.10+
- \`pip install requests colorama\`
- Access to Termux or a Linux-based terminal.

### Step 1: Create Key Registries
Copy the templates from the \`configuration/\` folders of each tool to \`~/.env/\` and rename them (e.g., \`gemini_keys.bejson\`). Populate them with your actual API keys.

### Step 2: Configure Routers
Ensure the \`router.json\` in each CLI directory points to the correct path of your \`.env\` registries.

### Step 3: Skill Installation
To install the documentation researcher:
\`\`\`bash
gemini skills install ./skills/gh-docs-researcher
\`\`\`

---

## 📖 Usage Guide

### Running Gemini:
\`\`\`bash
python3 gemini-cli/prompter.py "Explain the BEJSON 104a standard."
\`\`\`

### Running OpenRouter with Thinking Models:
\`\`\`bash
python3 openrouter-cli/prompter.py --model liquid/lfm-2.5-1.2b-thinking "How do I optimize a Python loop?"
\`\`\`

### Using the Research Skill:
\`\`\`bash
# Within a Gemini CLI session
> use gh-docs-researcher to clone openrouter docs
\`\`\`

---

## 🌟 Advanced Features

### 1. Key Slot Rotation
The tools implement a "Random Slot" strategy. When multiple keys are provided in the BEJSON registry, the CLI selects one at random. If a key fails (429 or 401), it automatically cycles to the next available slot.

### 2. Multi-Part Response Handling
For models that output both "Thoughts" and "Content", the CLI uses a double-box rendering system:
- **Top Box:** Monospace, dimmed text for reasoning/thinking.
- **Bottom Box:** Standard styling for the final response.

### 3. System Health Checks
Each tool includes a v1.21 Health Check protocol that verifies:
- Python environment compatibility.
- BEJSON registry accessibility.
- Network connectivity to the respective API endpoints.

---

## 📏 Standardization & Compliance

This suite is fully compliant with the **Switch Core v1.2** architecture.
- **Portability:** Designed to work across Termux and portable dev environments (\`/storage/emulated/0/dev\`).
- **Audit Trails:** All successful operations and errors are logged to centralized system logs (if configured).
- **No-Leak Guarantee:** The \`README.md\` and all repository files are scanned to ensure no sensitive data is present.

---

## 🤝 Contributing
We welcome contributions to the Multi-LLM CLI Suite! Please ensure any PRs:
1. Maintain BEJSON 104a compliance.
2. Follow the secure key management protocol.
3. Include updated documentation in this README.

---

## 📜 License
This toolkit is provided "as-is" for developer productivity. Please respect the Terms of Service of the respective API providers (Google, Groq, OpenRouter).

---

### Appendix A: Model ID Reference (April 2026)
| Provider | Model ID | Tier |
| --- | --- | --- |
| Google | \`google/gemma-4-31b-it:free\` | Free |
| Google | \`google/gemma-3-27b-it:free\` | Free |
| Liquid | \`liquid/lfm-2.5-1.2b-thinking:free\` | Free |
| Groq | \`llama-3.1-70b-versatile\` | Production |

### Appendix B: Troubleshooting
- **400 Error (Gemma):** Ensure the \`wrap_system_prompt\` flag is enabled in \`openrouter-cli/prompter.py\`.
- **429 Error:** Add more keys to your BEJSON registry to increase your aggregate rate limit.
- **ModuleNotFoundError:** Run \`pip install -r requirements.txt\` (if provided) or manually install \`requests\` and \`colorama\`.

---
