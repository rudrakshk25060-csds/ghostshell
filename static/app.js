/**
 * GhostShell — Retro Haunted Terminal Frontend Logic
 * Vanilla JavaScript • Zero External Dependencies • Accessible
 */

(function () {
  "use strict";

  // State
  let currentPersonality = "ghost";
  let commandHistory = [];
  let historyIndex = -1;
  let chatTurnHistory = [];
  let isAwaitingResponse = false;
  let modelStatus = {
    connected: false,
    modelAvailable: false,
    modelName: "gemma3:4b",
    baseUrl: "http://127.0.0.1:11434",
    message: "Initializing..."
  };

  // DOM Elements
  const screen = document.getElementById("terminalScreen");
  const inputForm = document.getElementById("inputForm");
  const cliInput = document.getElementById("cliInput");
  const promptLabel = document.getElementById("promptLabel");
  const statusPill = document.getElementById("statusPill");
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const footerModel = document.getElementById("footerModel");
  const btnClear = document.getElementById("btnClear");
  const personaButtons = document.querySelectorAll(".btn-persona");
  const quickChips = document.querySelectorAll(".quick-chip");

  const PROMPT_MAP = {
    ghost: "ghost@machine:~$",
    developer: "dev@machine:~$",
    storyteller: "cryptid@machine:~$"
  };

  // ASCII Art Banner
  const ASCII_BANNER = `
  .---.        .-----------.
 /     \\  __  /    GHOST    \\
/ /     \\(  )/     SHELL     \\
######   Y  ######
  |   |  |  |   |   The Ghost in Your Terminal
  |___|  |  |___|   Gemma 3 4B &bull; Local &bull; Hacktoberfest 2026
`;

  // -------------------------------------------------------------------------
  // Terminal Output Helpers
  // -------------------------------------------------------------------------

  function scrollToBottom() {
    screen.scrollTop = screen.scrollHeight;
  }

  function appendOutput(htmlContent, className = "") {
    const el = document.createElement("div");
    el.className = `term-msg ${className}`;
    el.innerHTML = htmlContent;
    screen.appendChild(el);
    scrollToBottom();
    return el;
  }

  function showLoadingIndicator(customText = "The ghost is contemplating the machine...") {
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "term-msg ghost-thinking";
    loadingDiv.id = "activeLoading";
    loadingDiv.innerHTML = `<span>&#x26A1;</span> <span>${escapeHtml(customText)}</span>`;
    screen.appendChild(loadingDiv);
    scrollToBottom();
  }

  function removeLoadingIndicator() {
    const el = document.getElementById("activeLoading");
    if (el) el.remove();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // -------------------------------------------------------------------------
  // Readiness & Status Management
  // -------------------------------------------------------------------------

  async function checkReadiness(quiet = false) {
    statusDot.className = "status-dot degraded";
    statusText.textContent = "CHECKING...";

    try {
      const resp = await fetch("/ready");
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const data = await resp.json();
      modelStatus = {
        connected: data.ollama_connected,
        modelAvailable: data.model_available,
        modelName: data.model_name,
        baseUrl: data.base_url,
        message: data.message,
        instructions: data.instructions
      };

      footerModel.textContent = `${data.model_name} (Ollama Local)`;

      if (data.ollama_connected && data.model_available) {
        statusDot.className = "status-dot ready";
        statusText.textContent = "ONLINE (READY)";
        statusPill.title = `Ollama connected. Model ${data.model_name} is ready.`;
      } else if (data.ollama_connected && !data.model_available) {
        statusDot.className = "status-dot degraded";
        statusText.textContent = "MODEL MISSING";
        statusPill.title = data.message;
      } else {
        statusDot.className = "status-dot offline";
        statusText.textContent = "OLLAMA OFFLINE";
        statusPill.title = data.message;
      }

      if (!quiet) {
        let statusHtml = `
          <div style="border: 1px solid var(--phosphor-dim); padding: 8px 12px; border-radius: 4px; margin-top: 4px;">
            <div><strong>DIAGNOSTIC STATUS:</strong> ${escapeHtml(data.message)}</div>
            <div>&bull; Ollama Service (${escapeHtml(data.base_url)}): <strong>${data.ollama_connected ? 'CONNECTED' : 'DISCONNECTED'}</strong></div>
            <div>&bull; Target Model (${escapeHtml(data.model_name)}): <strong>${data.model_available ? 'INSTALLED' : 'NOT FOUND'}</strong></div>
        `;
        if (data.instructions) {
          statusHtml += `<div style="color: var(--accent-amber); margin-top: 6px;"><strong>Action Required:</strong><br><pre style="margin-top: 4px;">${escapeHtml(data.instructions)}</pre></div>`;
        }
        statusHtml += `</div>`;
        appendOutput(statusHtml, "system");
      }
    } catch (err) {
      statusDot.className = "status-dot offline";
      statusText.textContent = "SERVER ERROR";
      if (!quiet) {
        appendOutput(`[DIAGNOSTIC ERROR] Failed to connect to GhostShell backend: ${escapeHtml(err.message)}`, "error");
      }
    }
  }

  // -------------------------------------------------------------------------
  // Boot Sequence
  // -------------------------------------------------------------------------

  function runBootSequence() {
    appendOutput(`<div class="boot-banner">${ASCII_BANNER}</div>`, "system");
    appendOutput(`[SYSTEM KERNEL] Mounting local neural circuitry...`, "system");
    appendOutput(`[IDENTITY] GhostShell v1.0 activated under MIT License.`, "system");
    appendOutput(`[PRIVACY] Local-first architecture: No remote inference, zero telemetry, no cloud keys.`, "system");

    setTimeout(() => {
      checkReadiness(false);
      appendOutput(`
        <div style="margin-top: 6px;">
          Type <strong>help</strong> for available commands, or try:
          <br>&bull; <code>explain git rebase -i</code> (analyzes shell commands safely)
          <br>&bull; <code>inspect .</code> (scans local repository metadata)
          <br>&bull; <code>story</code> (weaves dark code fiction)
        </div>
      `, "system");
    }, 600);
  }

  // -------------------------------------------------------------------------
  // Feature Callers
  // -------------------------------------------------------------------------

  async function handleHaunt(text) {
    showLoadingIndicator(`The ghost contemplates your words...`);
    try {
      const resp = await fetch("/api/haunt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          personality: currentPersonality,
          history: chatTurnHistory.slice(-6)
        })
      });

      removeLoadingIndicator();

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        renderError(errJson.error || "Inference Failed", errJson.detail, errJson.instructions);
        return;
      }

      const data = await resp.json();
      chatTurnHistory.push({ role: "user", content: text });
      chatTurnHistory.push({ role: "assistant", content: data.reply });

      const mockBadge = data.is_mock ? `<span style="color:var(--accent-amber)">[MOCK TEST]</span> ` : "";
      const personaUpper = data.personality.toUpperCase();

      const html = `
        <div class="meta-header">
          <span>${mockBadge}👻 ${personaUpper} &bull; ${escapeHtml(data.model)}</span>
          <span>${new Date(data.timestamp).toLocaleTimeString()}</span>
        </div>
        <div class="reply-body">${formatMarkdownLike(data.reply)}</div>
      `;
      appendOutput(html, "ghost-reply");
    } catch (err) {
      removeLoadingIndicator();
      renderError("Network Communication Error", err.message, "Verify that the GhostShell backend server is running.");
    }
  }

  async function handleExplain(commandStr) {
    showLoadingIndicator(`Dissecting shell command: '${commandStr}'...`);
    try {
      const resp = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command: commandStr,
          personality: currentPersonality
        })
      });

      removeLoadingIndicator();

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        renderError(errJson.error || "Explanation Error", errJson.detail, errJson.instructions);
        return;
      }

      const data = await resp.json();
      let alertBox = "";
      if (data.risks_identified && data.risk_warning) {
        alertBox += `<div class="risk-alert">&#x26A0;&#xFE0F; ${escapeHtml(data.risk_warning)}</div>`;
      }
      if (data.safe_alternative) {
        alertBox += `<div class="safe-alt">&#x1F6E1;&#xFE0F; Recommended Alternative: <code>${escapeHtml(data.safe_alternative)}</code></div>`;
      }

      const html = `
        <div class="explain-card">
          <div class="meta-header">
            <span>&#x1F50E; COMMAND ANALYSIS: <code>${escapeHtml(data.command)}</code></span>
            <span>${escapeHtml(data.model)}</span>
          </div>
          ${alertBox}
          <div class="explain-section">
            <div class="reply-body">${formatMarkdownLike(data.explanation)}</div>
          </div>
        </div>
      `;
      appendOutput(html, "ghost-reply");
    } catch (err) {
      removeLoadingIndicator();
      renderError("Explanation Failure", err.message);
    }
  }

  async function handleInspect(targetPath = ".") {
    showLoadingIndicator(`Scanning safe repository remnants at '${targetPath}'...`);
    try {
      const resp = await fetch("/api/inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_path: targetPath,
          max_depth: 3,
          include_git: true
        })
      });

      removeLoadingIndicator();

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        renderError(errJson.error || "Inspection Restricted", errJson.detail || errJson.message);
        return;
      }

      const data = await resp.json();
      let commitsHtml = "";
      if (data.recent_commits && data.recent_commits.length > 0) {
        commitsHtml = `
          <div style="margin-top: 8px;">
            <strong>Recent Git Log Remnants:</strong>
            <ul style="margin-left: 20px; font-size: 0.85rem;">
              ${data.recent_commits.map(c => `<li><code>${escapeHtml(c.hash)}</code>: ${escapeHtml(c.message)}</li>`).join("")}
            </ul>
          </div>
        `;
      }

      let obsHtml = "";
      if (data.observations && data.observations.length > 0) {
        obsHtml = `
          <div style="margin-top: 8px;">
            <strong>Observations for the Ghost:</strong>
            <ul style="margin-left: 20px; font-size: 0.85rem;">
              ${data.observations.map(o => `<li>${escapeHtml(o)}</li>`).join("")}
            </ul>
          </div>
        `;
      }

      const treeSnippet = data.directory_tree.slice(0, 30).join("\n");

      const html = `
        <div class="explain-card">
          <div class="meta-header">
            <span>&#x1F4C1; REPOSITORY INSPECTION: ${escapeHtml(data.project_name)}</span>
            <span>Scanned: ${data.total_files_scanned} files (${data.context_char_count} chars)</span>
          </div>
          <div><strong>Location:</strong> <code>${escapeHtml(data.resolved_path)}</code></div>
          <div><strong>Technologies:</strong> ${data.key_technologies.length > 0 ? escapeHtml(data.key_technologies.join(", ")) : "Standard Scripts"}</div>
          <div class="inspect-tree">${escapeHtml(treeSnippet)}</div>
          ${commitsHtml}
          ${obsHtml}
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px;">
            * Read-only inspection complete. Zero shell commands executed. Untrusted data bounded.
          </div>
        </div>
      `;
      appendOutput(html, "ghost-reply");
    } catch (err) {
      removeLoadingIndicator();
      renderError("Inspection Error", err.message);
    }
  }

  async function handleStory(userArgs = "") {
    showLoadingIndicator(`The storyteller summons a dark tale from the machine's memory...`);
    try {
      const resp = await fetch("/api/story", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: "The Forgotten Repository",
          context: userArgs || "A codebase abandoned after a fatal merge conflict.",
          vibe: "eerie gothic tech horror"
        })
      });

      removeLoadingIndicator();

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        renderError(errJson.error || "Story Generation Error", errJson.detail, errJson.instructions);
        return;
      }

      const data = await resp.json();
      const html = `
        <div class="story-card">
          <div class="story-title">&#x1F4D6; ${escapeHtml(data.inspired_by)}: An Uncanny Chronicle</div>
          <div class="reply-body">${formatMarkdownLike(data.story)}</div>
          <div class="story-disclaimer">${escapeHtml(data.disclaimer)}</div>
        </div>
      `;
      appendOutput(html, "term-msg");
    } catch (err) {
      removeLoadingIndicator();
      renderError("Storytelling Failed", err.message);
    }
  }

  function renderHelp() {
    const html = `
      <div style="border: 1px solid var(--phosphor-dim); padding: 10px 14px; border-radius: 4px;">
        <h4 style="color: var(--phosphor-bright); margin-bottom: 6px;">COMMAND DIRECTORY &bull; GHOSTSHELL</h4>
        <div><strong>explain &lt;command&gt;</strong> — Safely dissects a shell command (intent, flags, effects, risks). Never executes it.</div>
        <div><strong>inspect [path]</strong> — Performs bounded read-only inspection of repository structure and git logs.</div>
        <div><strong>story [context]</strong> — Generates an eerie, fictional micro-horror story inspired by the codebase.</div>
        <div><strong>status</strong> — Runs live diagnostics on local Ollama and Gemma 3 4B availability.</div>
        <div><strong>clear</strong> — Wipes the terminal transcript screen.</div>
        <div><strong>help</strong> — Displays this command reference.</div>
        <div style="margin-top: 6px; color: var(--phosphor-bright);">
          Or simply speak naturally: GhostShell responds via your active personality (Ghost / Developer / Storyteller).
        </div>
      </div>
    `;
    appendOutput(html, "system");
  }

  function renderError(title, detail, instructions) {
    let errHtml = `<strong>[ERROR: ${escapeHtml(title)}]</strong>`;
    if (detail) {
      errHtml += `<div style="margin-top: 4px;">${escapeHtml(detail)}</div>`;
    }
    if (instructions) {
      errHtml += `<div style="margin-top: 6px; color: var(--accent-amber);"><strong>Remedy:</strong><br><pre style="white-space: pre-wrap; margin-top: 4px;">${escapeHtml(instructions)}</pre></div>`;
    }
    appendOutput(errHtml, "error");
  }

  function formatMarkdownLike(text) {
    if (!text) return "";
    let safe = escapeHtml(text);

    // Temporarily extract multi-line code blocks to preserve indentation and formatting
    const codeBlocks = [];
    safe = safe.replace(/```([a-zA-Z0-9_-]*)\r?\n?([\s\S]*?)```/g, (match, lang, code) => {
      const idx = codeBlocks.length;
      codeBlocks.push(`<pre style="background: rgba(0,0,0,0.6); padding: 8px 12px; border-radius: 4px; border: 1px solid #1a331a; margin: 6px 0; overflow-x: auto;"><code>${code}</code></pre>`);
      return `___GHOST_CODE_BLOCK_${idx}___`;
    });

    // Inline code `...`
    safe = safe.replace(/`([^`]+)`/g, '<code style="background: rgba(0,255,102,0.1); padding: 1px 4px; border-radius: 2px;">$1</code>');

    // Bold **...**
    safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Section headers [SUMMARY], etc.
    safe = safe.replace(/\[([A-Z\s&]+)\]:/g, '<h4 style="color:var(--phosphor-bright); margin-top:8px; margin-bottom:2px;">[$1]</h4>');

    // Convert newlines to breaks for prose
    safe = safe.replace(/\n/g, "<br>");

    // Restore preformatted code blocks
    safe = safe.replace(/___GHOST_CODE_BLOCK_(\d+)___/g, (match, idx) => {
      return codeBlocks[parseInt(idx, 10)] || "";
    });

    return safe;
  }

  // -------------------------------------------------------------------------
  // Input Handling
  // -------------------------------------------------------------------------

  async function processInput(rawText) {
    const text = rawText.trim();
    if (!text || isAwaitingResponse) return;

    // Echo user command
    const promptString = PROMPT_MAP[currentPersonality] || "ghost@machine:~$";
    appendOutput(`<strong>${promptString}</strong> ${escapeHtml(text)}`, "user");

    commandHistory.push(text);
    historyIndex = commandHistory.length;
    cliInput.value = "";

    isAwaitingResponse = true;
    cliInput.disabled = true;

    try {
      const lower = text.toLowerCase();

      if (lower === "clear") {
        screen.innerHTML = "";
        appendOutput(`<div class="boot-banner">${ASCII_BANNER}</div>`, "system");
      } else if (lower === "help") {
        renderHelp();
      } else if (lower === "status") {
        await checkReadiness(false);
      } else if (lower.startsWith("explain ") || lower === "explain") {
        const cmdToExplain = text.substring(7).trim();
        if (!cmdToExplain) {
          appendOutput("Usage: <code>explain &lt;shell_command&gt;</code> (e.g., <code>explain git log --oneline</code>)", "system");
        } else {
          await handleExplain(cmdToExplain);
        }
      } else if (lower.startsWith("inspect")) {
        const target = text.substring(7).trim() || ".";
        await handleInspect(target);
      } else if (lower.startsWith("story") || lower === "haunt") {
        const storyArg = text.replace(/^(story|haunt)/i, "").trim();
        await handleStory(storyArg);
      } else {
        // Natural chat conversation
        await handleHaunt(text);
      }
    } finally {
      isAwaitingResponse = false;
      cliInput.disabled = false;
      cliInput.focus();
      scrollToBottom();
    }
  }

  // -------------------------------------------------------------------------
  // Event Listeners
  // -------------------------------------------------------------------------

  inputForm.addEventListener("submit", (e) => {
    e.preventDefault();
    processInput(cliInput.value);
  });

  cliInput.addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (commandHistory.length > 0 && historyIndex > 0) {
        historyIndex--;
        cliInput.value = commandHistory[historyIndex];
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        historyIndex++;
        cliInput.value = commandHistory[historyIndex];
      } else {
        historyIndex = commandHistory.length;
        cliInput.value = "";
      }
    }
  });

  // Personality switcher
  personaButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      personaButtons.forEach(b => {
        b.classList.remove("active");
        b.setAttribute("aria-pressed", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-pressed", "true");

      currentPersonality = btn.getAttribute("data-persona");
      promptLabel.textContent = PROMPT_MAP[currentPersonality] || "ghost@machine:~$";
      appendOutput(`[PERSONA SWITCHED] Active companion is now <strong>${currentPersonality.toUpperCase()}</strong>.`, "system");
      cliInput.focus();
    });
  });

  // Clear button
  btnClear.addEventListener("click", () => {
    screen.innerHTML = "";
    appendOutput(`<div class="boot-banner">${ASCII_BANNER}</div>`, "system");
    cliInput.focus();
  });

  // Quick suggestion chips
  quickChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const cmd = chip.getAttribute("data-cmd");
      if (cmd) {
        processInput(cmd);
      }
    });
  });

  // Status pill click (run diagnostics)
  statusPill.addEventListener("click", () => {
    checkReadiness(false);
  });

  // Initialize
  runBootSequence();
})();
