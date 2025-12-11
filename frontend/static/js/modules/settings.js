import { API } from "./api.js";
import { UI } from "./ui.js";

export const Settings = {
  form: document.getElementById("settingsForm"),

  init() {
    if (this.form) {
      this.form.addEventListener("submit", (e) => {
        e.preventDefault();
        this.save();
      });
    }
    this.load();
  },

  async load() {
    try {
      const data = await API.get("/api/settings");
      this.populate(data);
      return data; // Return data so other modules can use it if needed
    } catch (e) {
      console.error(e);
    }
  },

  populate(data) {
    const fields = [
      "tiktok_username",
      "deepseek_api_key",
      "main_scene_name",
      "obs_ws_host",
      "obs_ws_port",
      "obs_ws_password",
      "rate_limit",
      "reconnect_delay",
    ];

    // Map DB keys to ID keys if they differ slightly
    const map = {
      rate_limit: "comment_rate_limit",
      reconnect_delay: "tiktok_reconnect_delay",
    };

    fields.forEach((id) => {
      const el = document.getElementById(id);
      const key = map[id] || id;
      if (el) el.value = data[key] || "";
    });
  },

  async save() {
    const btn = document.getElementById("saveSettingsBtn");
    btn.disabled = true;
    btn.textContent = "Saving...";

    const data = {
      tiktok_username: document.getElementById("tiktok_username").value,
      deepseek_api_key: document.getElementById("deepseek_api_key").value,
      main_scene_name: document.getElementById("main_scene_name").value,
      obs_ws_host: document.getElementById("obs_ws_host").value,
      obs_ws_port: document.getElementById("obs_ws_port").value,
      obs_ws_password: document.getElementById("obs_ws_password").value,
      comment_rate_limit: document.getElementById("rate_limit").value,
      tiktok_reconnect_delay: document.getElementById("reconnect_delay").value,
    };

    try {
      await API.post("/api/settings", data);
      UI.showToast("Settings Saved!");
    } catch (e) {
      UI.showToast(e.message, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "Save Settings";
    }
  },
};
