---
name: gh-docs-researcher
description: Search for and clone official documentation repositories from GitHub. Use when the user needs local access to developer guides, API references, or example code for a specific project or model.
---

# Gh Docs Researcher

## Overview

The **Gh Docs Researcher** skill automates the discovery and local acquisition of official technical documentation from GitHub. It ensures that research is grounded in official sources and provides a structured local base for deep analysis.

## Workflow

### 1. Discovery
Use `google_web_search` or `grep_search` (if in a connected repo) to identify the official GitHub repository for the target project.
- **Official Organization Check**: Prioritize repositories under the project's official organization (e.g., `google-deepmind/gemma`, `OpenRouterTeam/openrouter-examples`).
- **Recency Check**: Look for repositories with recent activity (updated in 2026).

### 2. Acquisition
Run the bundled `clone_docs.py` script to clone the repository to the local documentation root.
- **Default Path**: `/storage/emulated/0/Documents/<project_name>`
- **Command**: `python3 scripts/clone_docs.py <REPO_URL>`

### 3. Initial Indexing
The script will automatically identify key documentation folders (`docs/`, `examples/`). You should then perform a `list_directory` on these folders to map the available research material.

## Usage Examples

### Researching a new Model
**User**: "Find the implementation docs for Liquid LFM 2026."
**Action**:
1. Search for Liquid AI GitHub.
2. Identify `liquid-ai/lfm-docs` (or similar).
3. Execute: `python3 scripts/clone_docs.py https://github.com/liquid-ai/lfm-docs`
4. Summarize the found documentation structure.

### Deep Dive into an API
**User**: "I need the full OpenRouter prompt caching specs."
**Action**:
1. Search for OpenRouter documentation repo.
2. Execute: `python3 scripts/clone_docs.py https://github.com/OpenRouterTeam/openrouter-examples`
3. Analyze `examples/prompt-caching` for the latest 2026 specs.

## Resources

### scripts/
- **clone_docs.py**: Automates cloning with `--depth 1` and performs an initial documentation inventory.

### references/
- **official_orgs.md**: (Optional) A list of known official GitHub organizations for common tools.
