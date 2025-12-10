// frontend/static/js/script.js

document.addEventListener("DOMContentLoaded", () => {
  // --- THEME MANAGEMENT ---
  const initTheme = () => {
    const savedTheme = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);
  };

  const updateThemeIcon = (theme) => {
    const icon = document.getElementById("themeIcon");
    if (theme === "light") {
      // Sun icon for light mode (click to switch to dark)
      icon.innerHTML =
        '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
    } else {
      // Moon icon for dark mode (click to switch to light)
      icon.innerHTML =
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
    }
  };

  const toggleTheme = () => {
    const currentTheme =
      document.documentElement.getAttribute("data-theme") || "dark";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateThemeIcon(newTheme);
  };

  const themeToggleBtn = document.getElementById("themeToggleBtn");
  themeToggleBtn.addEventListener("click", toggleTheme);

  initTheme();

  // --- STATE ---
  let state = {
    products: [],
    isRunning: false,
  };

  // --- SELECTORS ---
  const sidebar = document.querySelector(".sidebar");
  const pages = document.querySelectorAll(".page");
  const startButton = document.getElementById("startButton");
  const stopButton = document.getElementById("stopButton");
  const settingsForm = document.getElementById("settingsForm");
  const addProductBtn = document.getElementById("addProductBtn");
  const productsContainer = document.getElementById("productsContainer");
  const productsEmptyState = document.getElementById("productsEmptyState");
  const modalContainer = document.getElementById("modalContainer");
  const toastContainer = document.getElementById("toastContainer");

  // Log Containers
  const chatLogContent = document.getElementById("chatLogContent");
  const actionLogContent = document.getElementById("actionLogContent");

  const productItemTemplate = document.getElementById("product-item-template");
  const productModalTemplate = document.getElementById(
    "product-modal-template"
  );

  let statusPollInterval = null;

  // --- HELPER: TOASTS ---
  const showToast = (message, type = "success") => {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<div class="toast-title">${type.toUpperCase()}</div><div class="toast-message">${message}</div>`;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  };

  // --- HELPER: RENDER LOGS (NEW) ---
  const renderLogs = (logs) => {
    if (!logs || !Array.isArray(logs)) return;

    // Clear current logs to avoid duplication
    // (The backend sends the full recent history every poll)
    chatLogContent.innerHTML = "";
    actionLogContent.innerHTML = "";

    // The logs come in [Oldest, ..., Newest].
    // Our CSS uses 'flex-direction: column-reverse', so the last DOM element
    // appears at the TOP of the container visually.
    logs.forEach((log) => {
      const entry = document.createElement("div");
      entry.className = "log-entry";

      if (log.type === "chat") {
        entry.innerHTML = `<span class="user">${log.user}:</span> ${log.message}`;
        chatLogContent.appendChild(entry);
      } else {
        // System/Action log
        entry.innerHTML = `<span class="action-success">[${log.time}]</span> ${log.message}`;
        actionLogContent.appendChild(entry);
      }
    });
  };

  // --- API POLL ---
  const fetchStatusAndLogs = async () => {
    try {
      const response = await fetch("/api/status");
      if (!response.ok) return;
      const data = await response.json();

      // Update UI State
      state.isRunning = data.running;
      startButton.disabled = state.isRunning;
      stopButton.disabled = !state.isRunning;

      const badge = document.getElementById("bot-status-badge");
      badge.textContent = state.isRunning ? "Running" : "Stopped";
      badge.className = `status-badge ${
        state.isRunning ? "status-badge-active" : "status-badge-inactive"
      }`;

      // Simulating connection statuses based on bot state (since we don't have granular flags yet)
      const tiktokBadge = document.getElementById("tiktok-status-badge");
      const obsBadge = document.getElementById("obs-status-badge");

      if (state.isRunning) {
        tiktokBadge.textContent = "Active";
        tiktokBadge.className = "status-badge status-badge-active";
        obsBadge.textContent = "Active";
        obsBadge.className = "status-badge status-badge-active";
      } else {
        tiktokBadge.textContent = "Offline";
        tiktokBadge.className = "status-badge status-badge-inactive";
        obsBadge.textContent = "Offline";
        obsBadge.className = "status-badge status-badge-inactive";
      }

      // Update Stats
      if (data.stats) {
        document.getElementById("statsContainer").innerHTML = `
         <div class="stats-mini-grid">
            <div class="stat-box"><span class="stat-label">Comments</span><span class="stat-value">${data.stats.comments_processed}</span></div>
            <div class="stat-box"><span class="stat-label">Switches</span><span class="stat-value">${data.stats.scenes_switched}</span></div>
            <div class="stat-box"><span class="stat-label">Cache Hits</span><span class="stat-value">${data.stats.cache_hits}</span></div>
            <div class="stat-box"><span class="stat-label">Errors</span><span class="stat-value">${data.stats.errors}</span></div>
         </div>`;
      }

      // Update Logs (The missing piece!)
      if (data.logs) {
        renderLogs(data.logs);
      }
    } catch (error) {
      console.error("Polling failed:", error);
    }
  };

  // --- PRODUCT & SETTINGS LOGIC ---
  const saveAllToBackend = async (silent = false) => {
    const saveBtn = document.getElementById("saveSettingsBtn");
    if (!silent) {
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";
    }

    try {
      const settingsToSave = {
        tiktok_username: document.getElementById("tiktok_username").value,
        deepseek_api_key: document.getElementById("deepseek_api_key").value,
        main_scene_name: document.getElementById("main_scene_name").value,
        obs_ws_host: document.getElementById("obs_ws_host").value,
        obs_ws_port: document.getElementById("obs_ws_port").value,
        obs_ws_password: document.getElementById("obs_ws_password").value,
        comment_rate_limit: document.getElementById("rate_limit").value,
        tiktok_reconnect_delay:
          document.getElementById("reconnect_delay").value,
        cache_duration_seconds: document.getElementById("cache_duration").value,
        products: state.products,
      };

      const response = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsToSave),
      });

      if (!response.ok) throw new Error("Save failed");
      if (!silent) showToast("Saved!", "success");
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      if (!silent) {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Settings";
      }
    }
  };

  const renderProducts = () => {
    productsContainer.innerHTML = "";
    if (state.products.length === 0) {
      productsEmptyState.style.display = "block";
      productsContainer.style.display = "none";
    } else {
      productsEmptyState.style.display = "none";
      productsContainer.style.display = "block";
      state.products.forEach((product, index) => {
        const item = productItemTemplate.content.cloneNode(true);
        item.querySelector(".product-item").dataset.index = index;
        item.querySelector(".product-item-name").textContent = product.name;
        item.querySelector(".product-item-scene").textContent = product.scene;
        item.querySelector(".product-item-description").textContent =
          product.description || "";
        productsContainer.appendChild(item);
      });
    }
  };

  const showProductModal = (editIndex = null) => {
    const isEdit = editIndex !== null;
    const product = isEdit ? state.products[editIndex] : {};

    modalContainer.innerHTML = "";
    modalContainer.appendChild(productModalTemplate.content.cloneNode(true));

    const overlay = modalContainer.querySelector(".modal-overlay");
    const nameInput = overlay.querySelector("#modal-product-name");
    const sceneInput = overlay.querySelector("#modal-product-scene");
    const descInput = overlay.querySelector("#modal-product-description");
    const saveBtn = overlay.querySelector("#modal-save");

    overlay.querySelector(".modal-title").textContent = isEdit
      ? "Edit Product"
      : "Add Product";
    saveBtn.textContent = isEdit ? "Update & Save" : "Save Product";

    nameInput.value = product.name || "";
    sceneInput.value = product.scene || "";
    descInput.value = product.description || "";

    const closeModal = () => overlay.remove();
    overlay.addEventListener(
      "click",
      (e) => e.target === overlay && closeModal()
    );
    overlay
      .querySelector("#modal-cancel")
      .addEventListener("click", closeModal);

    // Save Handler (Immediate DB Save)
    saveBtn.addEventListener("click", async () => {
      if (!nameInput.value || !sceneInput.value)
        return showToast("Required fields missing", "error");
      const newProd = {
        name: nameInput.value,
        scene: sceneInput.value,
        description: descInput.value,
      };

      if (isEdit) state.products[editIndex] = newProd;
      else state.products.push(newProd);

      renderProducts();
      closeModal();
      await saveAllToBackend(true);
    });
  };

  const loadSettings = async () => {
    try {
      const res = await fetch("/api/settings");
      const data = await res.json();

      document.getElementById("tiktok_username").value =
        data.tiktok_username || "";
      document.getElementById("deepseek_api_key").value =
        data.deepseek_api_key || "";
      document.getElementById("main_scene_name").value =
        data.main_scene_name || "";
      document.getElementById("obs_ws_host").value =
        data.obs_ws_host || "localhost";
      document.getElementById("obs_ws_port").value = data.obs_ws_port || 4455;
      document.getElementById("obs_ws_password").value =
        data.obs_ws_password || "";
      document.getElementById("rate_limit").value =
        data.comment_rate_limit || 2;
      document.getElementById("reconnect_delay").value =
        data.tiktok_reconnect_delay || 30;
      document.getElementById("cache_duration").value =
        data.cache_duration_seconds || 300;

      state.products = data.products || [];
      renderProducts();
    } catch (e) {
      console.error(e);
    }
  };

  // --- LISTENERS ---
  sidebar.addEventListener("click", (e) => {
    const navItem = e.target.closest(".nav-item");
    if (!navItem) return;
    e.preventDefault();
    sidebar
      .querySelectorAll(".nav-item")
      .forEach((i) => i.classList.remove("active"));
    navItem.classList.add("active");
    pages.forEach((p) =>
      p.classList.toggle("active", p.id === navItem.dataset.page)
    );
  });

  startButton.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/start", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message, "success");
        fetchStatusAndLogs();
      } else {
        showToast(data.message, "error");
      }
    } catch (e) {
      showToast("Failed to start", "error");
    }
  });

  stopButton.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/stop", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message, "success");
        fetchStatusAndLogs();
      } else {
        showToast(data.message, "error");
      }
    } catch (e) {
      showToast("Failed to stop", "error");
    }
  });

  addProductBtn.addEventListener("click", () => showProductModal());

  productsContainer.addEventListener("click", async (e) => {
    const editBtn = e.target.closest(".btn-edit");
    const deleteBtn = e.target.closest(".btn-delete");

    if (editBtn) {
      showProductModal(
        parseInt(editBtn.closest(".product-item").dataset.index)
      );
    }
    if (deleteBtn && confirm("Delete product?")) {
      state.products.splice(
        parseInt(deleteBtn.closest(".product-item").dataset.index),
        1
      );
      renderProducts();
      await saveAllToBackend(true);
      showToast("Product deleted", "success");
    }
  });

  settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    await saveAllToBackend();
  });

  // Init
  loadSettings();
  fetchStatusAndLogs();
  statusPollInterval = setInterval(fetchStatusAndLogs, 3000);
});
