# GhostShell — 60-90 Second Video Demo Script

> **Hacktoberfest 2026: Ghost in the Machine**  
> **Target Duration:** 75 seconds  
> **Tools:** Screen recording of terminal / browser at `http://localhost:8000`

---

## Video Walkthrough Timeline

### 0:00 – 0:12 | Scene 1: The Boot Sequence & Local Connection
- **Visual:** Open browser to `http://localhost:8000`. The CRT scanlines flicker gently. The green phosphor boot sequence rolls across the screen: ASCII skull, memory checks, and the status indicator in the top right transitions to `ONLINE (READY)`.
- **Voiceover:**
  > *"Every repository has a past. Every commit leaves a trace. Welcome to GhostShell — a local-first, haunted terminal companion powered by Google's Gemma 3 4B running on your machine via Ollama."*

---

### 0:13 – 0:28 | Scene 2: Safe Command Explanation
- **Visual:** The user types or clicks the suggested chip:  
  `explain git rebase -i HEAD~3`
- **Action:** Hit `[ENTER]`.
- **Visual:** The loading pulse appears: *"Dissecting shell command..."*  
  The terminal outputs a formatted breakdown with:
  - **[SUMMARY]**: Interactive Git history rewriting.
  - **[FLAGS & ARGUMENTS]**: `-i` for interactive, `HEAD~3` specifying the last 3 commits.
  - **[SYSTEM EFFECTS]**: Rewrites commit hashes.
  - **[RISK ASSESSMENT]**: Warning about force-pushing shared branches.
  - **[SAFER ALTERNATIVE]**: `git branch backup-branch` before rebasing.
- **Voiceover:**
  > *"GhostShell isn't just an atmospheric toy — it's real developer intelligence. When you ask it to explain a complex or dangerous command, it dissects the flags, effects, and risks. And critically: GhostShell never executes commands — zero subprocess calls, zero risk to your machine."*

---

### 0:29 – 0:44 | Scene 3: Read-Only Repository Inspection
- **Visual:** The user types:  
  `inspect sample_repo`
- **Action:** Hit `[ENTER]`.
- **Visual:** The terminal renders the inspection summary:
  - Directory hierarchy (`📁 necropolis-cache`, `📄 ritual.py`, `📄 config.json`).
  - Read-only Git reflog commits extracted without shell execution:
    `Awaken the forgotten daemon`, `Initial ritual commit`.
  - Discovered lingering TODO markers (`# TODO: Investigate memory leak reported on midnight cron`).
- **Voiceover:**
  > *"Point GhostShell at a repository, and it performs a bounded, read-only inspection. It scans manifests, extracts Git reflogs, and identifies lingering TODOs — all strictly confined within your authorized project boundary, blocking secrets like .env files and private keys."*

---

### 0:45 – 0:58 | Scene 4: Fictional Ghost Stories from Real Code
- **Visual:** The user clicks the **📜 STORYTELLER** persona button. The prompt changes to `cryptid@machine:~$`.  
  The user types:  
  `story`
- **Action:** Hit `[ENTER]`.
- **Visual:** The storyteller spins a gothic micro-story weaving in the `necropolis-cache` daemon, port `6660`, and the midnight cron memory leak, accompanied by the explicit fictional disclaimer badge.
- **Voiceover:**
  > *"Switch to the Storyteller persona, and GhostShell breathes uncanny life into your forgotten code remnants — turning stale branches and abandoned commit messages into gothic tech horror."*

---

### 0:59 – 1:15 | Scene 5: Why Open-Weight AI & Local Inference Matter
- **Visual:** Zoom out to show the whole dashboard and the footer:  
  `INFERENCE: gemma3:4b (Ollama Local) | PRIVACY: 100% AIR-GAPPED &bull; ZERO TELEMETRY`.
- **Voiceover:**
  > *"Best of all: 100% local. Your code never leaves your laptop. No API fees, no remote tracking, and no cloud dependencies. Open-weight innovation like Gemma puts power back into developers' hands. GhostShell is open source under the MIT License for Hacktoberfest 2026."*

---

## Backup Demo Inputs & Cheat Sheet

```bash
# 1. Check system readiness
status

# 2. Command explanation (safe)
explain git rebase -i

# 3. Dangerous command explanation (triggers high-severity risk alert)
explain rm -rf /tmp/cache

# 4. Safe repo inspection
inspect sample_repo

# 5. Generate story
story
```
