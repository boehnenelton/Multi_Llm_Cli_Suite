# Multi-LLM CLI Suite

**Version 1.1.0 · BEJSON Native · Cross-Provider AI Orchestrator**

The **Multi-LLM CLI Suite** is a standardized, high-performance orchestration framework designed for unified access to multiple Large Language Model (LLM) providers through a command-line interface. Built on Elton Boehnen's **BEJSON** and **MFDB** architectures, it enables deterministic model behavior, robust rate-limit management, and self-healing configuration registries across Gemini, Groq, OpenRouter, and Hugging Face.

## Author Information
- **Name:** Elton Boehnen
- **Email:** [boehnenelton2024@gmail.com](mailto:boehnenelton2024@gmail.com)
- **GitHub:** [https://github.com/boehnenelton/](https://github.com/boehnenelton/)
- **Website:** [https://boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev)

## Core Capabilities
- **Unified Orchestration:** A single, consistent interface (`prompter.py`) across all providers for querying models with standardized input/output logic.
- **BEJSON-Driven Configuration:** Leverages BEJSON 104a and 104 schemas for profile management, model registries, and key rotation.
- **Round-Robin Key Rotation:** Automatically cycles through multiple API keys to maximize throughput and bypass rate limits.
- **Self-Healing Architecture:** Integrated support for `mfdb_core_smart_repair` to automatically detect and fix corrupted or inconsistent configuration files.
- **Rate Limit & Cooldown Logic:** Implements sophisticated request delays, consecutive error tracking, and intelligent cooldown periods to ensure high availability.
- **Modular Provider Support:**
    - **Gemini-CLI:** Optimized for Google's 2.5 and 3.1 Pro/Flash models.
    - **Groq-CLI:** High-speed inference for Llama, Mixtral, and Gemma models.
    - **OpenRouter-CLI:** Proxy access to hundreds of open-source and proprietary models.
    - **HuggingFace-CLI:** Standardized interface for the Hugging Face Inference API.

## Technical Specifications
- **Language:** Python 3.10+
- **Database Architecture:** BEJSON (104, 104a), MFDB v1.3.1
- **API Protocols:** Standardized REST/JSON requests with custom error handling.
- **Environment:** Optimized for Termux (Android) and standard Linux CLI.

## Repository Structure
- `gemini-cli/`: Dedicated orchestrator and configuration for Google Gemini.
- `groq-cli/`: Specialized high-speed prompter for the Groq API.
- `openrouter-cli/`: Universal proxy orchestrator for OpenRouter.
- `huggingface-cli/`: Synchronized orchestrator for Hugging Face models.
- `skills/`: Extensible CLI skills (e.g., `gh-docs-researcher`) integrated with the suite.

## Usage Guide

### Basic Prompting (Example)
```bash
cd gemini-cli  # or groq-cli, huggingface-cli, etc.
python3 prompter.py "Explain the benefits of BEJSON architecture."
```

### Specifying a Profile
```bash
python3 prompter.py "Generate a system report." --profile ./configuration/gemini_test_profile.bejson
```

## Standards Compliance
This suite strictly adheres to the **2026 Standards** for AI integration, ensuring that all model interactions are traceable, structured, and resilient against API instabilities.

## License
Created and maintained by Elton Boehnen. All rights reserved.
