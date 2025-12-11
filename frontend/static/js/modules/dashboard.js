import { API } from "./api.js";
import { UI } from "./ui.js";

export const Dashboard = {
  state: { isRunning: false },
  socket: null,

  init(socketInstance) {
    this.socket = socketInstance;
    this.bindEvents();
    this.setupSocketListeners();
    this.checkStatus();
  },

  bindEvents() {
    const startBtn = document.getElementById("startButton");
    const stopBtn = document.getElementById("stopButton");
    const skipBtn = document.getElementById("skipButton");

    if (startBtn)
      startBtn.addEventListener("click", () => this.toggleBot("start"));
    if (stopBtn)
      stopBtn.addEventListener("click", () => this.toggleBot("stop"));

    if (skipBtn) {
      skipBtn.addEventListener("click", async () => {
        try {
          await API.post("/api/control/skip", {});
        } catch (e) {
          UI.showToast("Skip failed", "error");
        }
      });
    }
  },

  setupSocketListeners() {
    const chatLog = document.getElementById("chatLogContent");
    const actionLog = document.getElementById("actionLogContent");

    const appendAndScroll = (container, html) => {
      if (!container) return;
      const isScrolledToBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight <
        100;

      const entry = document.createElement("div");
      entry.className = "log-entry";
      entry.innerHTML = html;
      container.appendChild(entry);

      if (isScrolledToBottom) {
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 0);
      }
    };

    this.socket.on("new_log", (log) => {
      const timeStr = `<span class="log-time">[${log.time}]</span>`;
      if (log.type === "chat") {
        const html = `${timeStr} <span style="font-weight:600; color:hsl(var(--primary));">${log.user}:</span> ${log.message}`;
        appendAndScroll(chatLog, html);
      } else {
        const html = `${timeStr} ${log.message}`;
        appendAndScroll(actionLog, html);
      }
    });

    this.socket.on("stats_update", (stats) => {
      if (!stats) return;

      // Update Stats
      const elComments = document.getElementById("stat-comments");
      const elSwitches = document.getElementById("stat-switches");
      const elErrors = document.getElementById("stat-errors");

      if (elComments) elComments.textContent = stats.comments_processed;
      if (elSwitches) elSwitches.textContent = stats.scenes_switched;
      if (elErrors) elErrors.textContent = stats.errors;

      // Update Now Playing with new design
      const nowPlayingText = document.getElementById("now-playing-text");
      const nowPlayingBox = document.getElementById("currentProductDisplay");

      if (nowPlayingText && nowPlayingBox) {
        if (stats.current_product) {
          nowPlayingText.textContent = stats.current_product;
          nowPlayingBox.classList.remove("idle");
        } else {
          nowPlayingText.textContent = "Idle - Waiting for requests...";
          nowPlayingBox.classList.add("idle");
        }
      }

      // Update Queue with new design
      const queueList = document.getElementById("queueList");
      if (queueList) {
        queueList.innerHTML = "";
        if (stats.queue && stats.queue.length > 0) {
          stats.queue.forEach((item, index) => {
            const div = document.createElement("div");
            div.className = "queue-item";
            div.innerHTML = `
              <span class="queue-number">${index + 1}</span>
              <span style="font-weight:500; flex: 1;">${item}</span>
            `;
            queueList.appendChild(div);
          });
        } else {
          queueList.innerHTML = `<div class="text-muted text-sm" style="font-style: italic; padding: 1rem 0; text-align: center;">Queue is empty</div>`;
        }
      }
    });
  },

  async toggleBot(action) {
    try {
      const data = await API.post("/api/control", { action });
      if (
        data.status === "success" ||
        data.status === "started" ||
        data.status === "stopped"
      ) {
        UI.showToast(data.message, "success");
        this.state.isRunning = action === "start";
        this.updateUI();
      } else {
        UI.showToast(data.message, "error");
      }
    } catch (e) {
      UI.showToast("Connection failed", "error");
    }
  },

  async checkStatus() {
    try {
      const data = await API.get("/api/status");
      this.state.isRunning = data.running;
      this.updateUI();
    } catch (e) {
      console.error(e);
    }
  },

  updateUI() {
    const startBtn = document.getElementById("startButton");
    const stopBtn = document.getElementById("stopButton");
    const statusText = document.getElementById("bot-status-text");

    if (startBtn) startBtn.disabled = this.state.isRunning;
    if (stopBtn) stopBtn.disabled = !this.state.isRunning;

    if (statusText) {
      statusText.textContent = this.state.isRunning ? "Running" : "Stopped";
      statusText.style.color = this.state.isRunning
        ? "hsl(var(--primary))"
        : "hsl(var(--muted-foreground))";
    }
  },
};
