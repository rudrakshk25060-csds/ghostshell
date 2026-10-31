---
title: "GhostShell: Giving Forgotten Code a Voice with Gemma and Local Ollama"
published: false
description: "A local-first, retro phosphor terminal companion that turns forgotten Git history into real developer utility and gothic micro-fiction using Google Gemma 3 4B."
tags: "devchallenge, hf26challenge, python, ai, opensource"
cover_image: ""
---

# GhostShell: The Ghost in Your Terminal 👻

> *"Every repository has a past. Every commit leaves a trace. GhostShell gives that forgotten history a voice."*

Built for **Hacktoberfest 2026: Ghost in the Machine**, GhostShell is a local-first, retro phosphor terminal companion. It combines atmospheric retro-computing aesthetics with genuine developer utility: command risk analysis, read-only repository inspection, and eerie micro-fiction inspired by real code remnants — all powered by **Google's open-weight Gemma 3 4B model running offline through Ollama**.

- **GitHub Repository:** [https://github.com/rudrakshk25060-csds/ghostshell](https://github.com/rudrakshk25060-csds/ghostshell)
- **Demo Video (75s):** [https://youtu.be/your-demo-video](https://youtu.be/your-demo-video) *(Placeholder)*

---

## 1. The Inspiration & The Problem

Software repositories are modern graveyards. We abandon side projects, leave cryptic commit messages at 3:00 AM (`"it works don't touch"`), and litter codebases with unresolved `// TODO: fix this later`.

At the same time, modern AI developer tools have a glaring flaw: **they demand that you upload your proprietary source code, secrets, and private commit messages to remote corporate cloud servers.**

I wanted to build an AI companion that:
1. **Never leaks your code**: Operates 100% locally with zero cloud telemetry and zero API keys.
2. **Helps you understand obscure commands**: Safely dissects complex Git or shell commands before you execute them.
3. **Respects system security**: Never runs user input or model output as shell commands, and strictly sandboxes filesystem access.
4. **Has a soul**: Emulates a haunted retro phosphor CRT terminal with atmospheric personalities that bring your codebase's history to life.

---

## 2. What I Built

GhostShell is a full-stack, local-first application comprising:

### 🖥️ The Haunted CRT Terminal (Frontend)
- Built entirely in **HTML5, CSS3, and Vanilla JavaScript** with **zero external CDNs or remote font dependencies**.
- Eerie green phosphor glow, scanline overlay, and typewriter boot sequence.
- Full keyboard navigation with command history cycling (`ArrowUp` / `ArrowDown`).
- Accessible design with automatic reduced-motion detection (`@media (prefers-reduced-motion: reduce)`).

### 🛡️ Secure Asynchronous Backend (FastAPI & Python 3.11+)
- **Safe Command Explainer (`/api/explain`)**: Dissects shell commands into summaries, flag breakdowns, system effects, and safer alternatives. To eliminate command injection vulnerabilities, **GhostShell completely prohibits subprocess or shell execution** — commands are purely strings to explain.
- **Sandboxed Project Inspector (`/api/inspect`)**: Performs read-only scans of project structures, manifest files (`pyproject.toml`, `package.json`), and lingering TODOs. Path traversal attacks (`../`) and symlink escapes are strictly blocked. Secrets (`.env`, `*.key`, `id_rsa`) and binary files are filtered out.
- **Reflog Archaeology**: Safely parses `.git/logs/HEAD` plain text directly in Python without invoking external shell binaries, unearthing recent commits.
- **Gothic Micro-Fiction (`/api/story`)**: Weaves fictional horror micro-stories inspired by actual repository metadata (e.g., orphaned daemon scripts and memory leaks).

### 🎭 Three Distinct Personalities
1. **👻 GHOST**: Atmospheric, eerie, concise, yet technically rigorous.
2. **⚙️ DEVELOPER**: Direct, pragmatic, and structured systems architect.
3. **📜 STORYTELLER**: Weaves dark, fictional techno-horror from code remnants.

---

## 3. Architecture & The Power of Open Weights

```
+-----------------------------------------------------------+
|               GhostShell Terminal (Browser)              |
+-----------------------------------------------------------+
                              |
                     REST API (HTTP / JSON)
                              |
+-----------------------------------------------------------+
|                     FastAPI Backend                       |
|   - Path Confinement & Secret Blacklist Filters          |
|   - Prompt Injection Boundary Delimiters                  |
|   - Pure Python Git Reflog Parser (Zero Subprocess)       |
+-----------------------------------------------------------+
                              |
                Asynchronous HTTPX (Local Only)
                              |
+-----------------------------------------------------------+
|                  Local Ollama Service                     |
|                 (http://127.0.0.1:11434)                  |
|                                                           |
|             Google Gemma 3 4B (Open Weights)              |
+-----------------------------------------------------------+
```

### Why Gemma 3 4B Matters
By leveraging Google's **Gemma 3 4B** open-weight model through Ollama, GhostShell achieves:
- **True Privacy**: Your intellectual property and code structure never leave your machine.
- **Air-Gapped Reliability**: Works on planes, trains, or in air-gapped secure development environments after initial model download.
- **Zero Cost**: No recurring API bills, rate limits, or subscription tiers.

---

## 4. Security & Safety Model

AI coding tools can introduce major security risks if poorly designed. GhostShell enforces strict guardrails:

1. **No Execution Guarantee**: GhostShell never executes commands generated by the user or the model.
2. **Path Traversal & Symlink Immunity**: All inspection targets are resolved and validated against an authorized root directory (`authorized_root`). Escapes raise immediate `SecurityError` exceptions.
3. **Secret Isolation**: Files matching `.env*`, `*.pem`, `*.key`, `id_rsa*`, and `credentials*` are excluded from inspection.
4. **Prompt Injection Delimiters**: Inspected code snippets are wrapped in `<<<UNTRUSTED_REPOSITORY_DATA>>>` boundary delimiters, instructing Gemma to treat them as untrusted passive text rather than executable instructions.

---

## 5. Testing & Verification

GhostShell includes an automated test suite implemented with `pytest` and `pytest-asyncio`:

- **41 Automated Tests Passed** in under 0.2 seconds.
- **Test Categories**:
  - API endpoint status and health diagnostics.
  - Path traversal and symlink escape rejection (both directory boundaries and file link targets).
  - Secret file and binary file exclusion.
  - Command explanation and risk detection (including destructive flags and pipe-to-shell patterns).
  - Offline Ollama connection failure handling (HTTP 503 with friendly setup instructions).
  - Missing model detection (HTTP 404 with `ollama pull` guidance).
- **Live Local Inference Verified**: Live end-to-end inference was tested directly against Google's `gemma3:4b` weights running in a local Ollama instance on `http://127.0.0.1:11434`, verifying genuine model reasoning, token generation, and the absence of mocked outputs in production mode.

---

## 6. How to Run GhostShell

### Prerequisites
1. Python 3.11+
2. [Ollama](https://ollama.com) installed and running:
   ```bash
   ollama serve
   ollama pull gemma3:4b
   ```

### Quickstart
```bash
# Clone the repository
git clone https://github.com/rudrakshk25060-csds/ghostshell.git
cd ghostshell

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run GhostShell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open **`http://localhost:8000`** in your browser and awaken the ghost!

---

## 7. Reflections

Building GhostShell for Hacktoberfest 2026 proved that open-weight AI models like Gemma 3 4B are more than capable of providing responsive, intelligent developer assistance locally. By treating repository contents as archaeological remnants, we can build tools that are not only deeply useful and private, but also fun and evocative.

*Long live the ghost in the machine.* 👻
