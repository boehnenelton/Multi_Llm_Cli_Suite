# Gemini BEJSON Configurator (CLI)

A high-performance, standardized prompting engine for Google Gemini models, specialized in generating and validating **BEJSON (v104/104a/104db)** and **MFDB (v1.2)** data structures.

## 🚀 Key Features

*   **Standardized AI Profiles:** Uses BEJSON-based profiles to define complex personas, system instructions, and technical constraints.
*   **Round Robin API Management:** Automatically cycles through a pool of API keys to maximize throughput and avoid rate limits.
*   **Intelligent Routing:** Configurable `router.json` for mapping profiles, models, and key registries.
*   **Rate Limiting & Cooldowns:** Built-in safeguards for request delays, consecutive error limits, and global system cooldowns.
*   **Multi-Model Testing:** Includes automation for benchmarking prompts across the entire Gemini model family (3.1 Pro, 3 Flash, 2.5 Flash, etc.).

## 📁 Project Structure

*   `prompter.py`: The core CLI engine.
*   `router.json`: Central configuration for model routing and system settings.
*   `configuration/`: BEJSON registries for AI profiles, model definitions, and API keys.
*   `lib/`: Core logic for BEJSON parsing and Gemini API orchestration.
*   `output/`: Default directory for saved responses.
*   `run_tests.sh`: Automation script for multi-model benchmarking.

## 🛠️ Usage

### Basic Prompt
\`\`\`bash
python3 prompter.py "Generate a BEJSON 104 schema for a user profile."
\`\`\`

### Custom Model & Output
\`\`\`bash
python3 prompter.py "Compare BEJSON 104 vs 104a" --model "gemini-3.1-pro-preview" --output "analysis.txt"
\`\`\`

### Running Benchmarks
\`\`\`bash
./run_tests.sh
\`\`\`

## 📊 Data Standards

This engine is designed to enforce the **BEJSON** tabular standard created by **Elton Boehnen**, ensuring positional integrity and strict schema compliance for AI-generated data.

---
*Powered by BEJSON & Gemini*
