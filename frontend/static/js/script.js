document.addEventListener("DOMContentLoaded", () => {
  // --- STATE MANAGEMENT ---
  let state = {
    products: [], // Holds the source of truth for products
    isRunning: false,
    settings: {},
  };

  // --- ELEMENT SELECTORS ---
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

  // Templates
  const productItemTemplate = document.getElementById("product-item-template");
  const productModalTemplate = document.getElementById(
    "product-modal-template"
  );

  let statusPollInterval = null;

  // ============================
  // === UI & RENDER FUNCTIONS ===
  // ============================

  /**
   * Shows a toast notification at the bottom-right of the screen.
   * @param {string} message The message to display.
   * @param {('success'|'error')} type The type of toast.
   */
  const showToast = (message, type = "success") => {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-title">${
        type.charAt(0).toUpperCase() + type.slice(1)
      }</div>
      <div class="toast-message">${message}</div>
    `;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  };

  /** Renders the list of products from the local state. */
  const renderProducts = () => {
    productsContainer.innerHTML = ""; // Clear existing products
    if (state.products.length === 0) {
      productsEmptyState.style.display = "block";
      productsContainer.style.display = "none";
    } else {
      productsEmptyState.style.display = "none";
      productsContainer.style.display = "block";
      state.products.forEach((product, index) => {
        const productElement = productItemTemplate.content.cloneNode(true);
        productElement.querySelector(".product-item").dataset.index = index;
        productElement.querySelector(".product-item-name").textContent =
          product.name;
        productElement.querySelector(
          ".product-item-scene"
        ).textContent = `OBS Scene: ${product.scene}`;
        productElement.querySelector(".product-item-description").textContent =
          product.description || "No AI keywords or description provided.";
        productsContainer.appendChild(productElement);
      });
    }
  };

  /**
   * Updates the entire dashboard UI based on API data.
   * @param {object} data The data from the /api/status endpoint.
   */
  const updateDashboardUI = (data) => {
    state.isRunning = data.running;

    // Buttons
    startButton.disabled = state.isRunning;
    stopButton.disabled = !state.isRunning;

    // Badges
    const botStatusBadge = document.getElementById("bot-status-badge");
    const tiktokStatusBadge = document.getElementById("tiktok-status-badge");
    const obsStatusBadge = document.getElementById("obs-status-badge");

    botStatusBadge.textContent = state.isRunning ? "Running" : "Stopped";
    botStatusBadge.className = `status-badge ${
      state.isRunning ? "status-badge-active" : "status-badge-inactive"
    }`;

    // In a real scenario, the backend would provide individual connection statuses
    tiktokStatusBadge.textContent = state.isRunning
      ? "Connected"
      : "Disconnected";
    tiktokStatusBadge.className = `status-badge ${
      state.isRunning ? "status-badge-active" : "status-badge-inactive"
    }`;
    obsStatusBadge.textContent = state.isRunning ? "Connected" : "Disconnected";
    obsStatusBadge.className = `status-badge ${
      state.isRunning ? "status-badge-active" : "status-badge-inactive"
    }`;

    // Stats
    const statsContainer = document.getElementById("statsContainer");
    if (data.running && data.stats) {
      statsContainer.innerHTML = `
            <div class="stat-card"><div class="stat-label">Comments</div><div class="stat-value">${
              data.stats.comments_processed || 0
            }</div></div>
            <div class="stat-card"><div class="stat-label">Switches</div><div class="stat-value">${
              data.stats.scenes_switched || 0
            }</div></div>
            <div class="stat-card"><div class="stat-label">Cache Hits</div><div class="stat-value">${
              data.stats.cache_hits || 0
            }</div></div>
            <div class="stat-card"><div class="stat-label">Errors</div><div class="stat-value">${
              data.stats.errors || 0
            }</div></div>
        `;
    }
  };

  // ===========================
  // === MODAL & FORM LOGIC ===
  // ===========================

  /**
   * Displays the modal for adding or editing a product.
   * @param {number|null} editIndex The index of the product to edit, or null to add.
   */
  const showProductModal = (editIndex = null) => {
    const isEdit = editIndex !== null;
    const product = isEdit ? state.products[editIndex] : {};

    const modalNode = productModalTemplate.content.cloneNode(true);
    modalContainer.innerHTML = ""; // Clear any previous modal
    modalContainer.appendChild(modalNode);

    const overlay = modalContainer.querySelector(".modal-overlay");
    const title = overlay.querySelector(".modal-title");
    const saveBtn = overlay.querySelector("#modal-save");
    const nameInput = overlay.querySelector("#modal-product-name");
    const sceneInput = overlay.querySelector("#modal-product-scene");
    const descInput = overlay.querySelector("#modal-product-description");

    title.textContent = isEdit ? "Edit Product" : "Add New Product";
    saveBtn.textContent = isEdit ? "Update Product" : "Save Product";
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
    overlay.querySelector("#modal-save").addEventListener("click", () => {
      const name = nameInput.value.trim();
      const scene = sceneInput.value.trim();
      const description = descInput.value.trim();

      if (!name || !scene) {
        return showToast("Product Name and OBS Scene are required.", "error");
      }

      const newProduct = { name, scene, description };
      if (isEdit) {
        state.products[editIndex] = newProduct;
      } else {
        state.products.push(newProduct);
      }

      renderProducts();
      showToast(
        `Product ${isEdit ? "updated" : "added"} successfully.`,
        "success"
      );
      closeModal();
    });
  };

  // ============================
  // === API COMMUNICATION ===
  // ============================

  /** Fetches status and log data from the backend. */
  const fetchStatusAndLogs = async () => {
    try {
      const response = await fetch("/api/status");
      if (!response.ok) return; // Fail silently on poll
      const data = await response.json();
      updateDashboardUI(data);

      // Placeholder for future log fetching from an endpoint like /api/logs
      // const logResponse = await fetch("/api/logs");
      // const logData = await logResponse.json();
      // updateLogs(logData);
    } catch (error) {
      console.error("Polling failed:", error);
    }
  };

  /** Loads all settings and populates the UI. */
  const loadSettings = async () => {
    try {
      const response = await fetch("/api/settings");
      if (!response.ok)
        throw new Error("Failed to fetch settings from server.");
      const settings = await response.json();
      state.settings = settings;

      // Populate Settings form
      settingsForm.querySelector("#tiktok_username").value =
        settings.tiktok_username || "";
      settingsForm.querySelector("#deepseek_api_key").value =
        settings.deepseek_api_key || "";
      settingsForm.querySelector("#main_scene_name").value =
        settings.main_scene_name || "";
      settingsForm.querySelector("#obs_ws_host").value =
        settings.obs_ws_host || "localhost";
      settingsForm.querySelector("#obs_ws_port").value =
        settings.obs_ws_port || 4455;
      settingsForm.querySelector("#obs_ws_password").value =
        settings.obs_ws_password || "";
      settingsForm.querySelector("#rate_limit").value =
        settings.comment_rate_limit || 2;
      settingsForm.querySelector("#reconnect_delay").value =
        settings.tiktok_reconnect_delay || 30;
      settingsForm.querySelector("#cache_duration").value =
        settings.cache_duration_seconds || 300;

      // Populate local product state from the flat config lists
      state.products = settings.product_list.map((name) => ({
        name: name,
        scene: settings.product_to_scene_map[name] || "",
        description: settings.product_descriptions?.[name] || "",
      }));
      renderProducts();
    } catch (error) {
      console.error("Load settings error:", error);
      showToast(error.message, "error");
    }
  };

  /** Saves all settings from the UI to the backend. */
  const handleSaveSettings = async (event) => {
    event.preventDefault();
    const saveButton = document.getElementById("saveSettingsBtn");
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";

    try {
      // Construct the flat structure the backend expects from our product state
      const product_list = state.products.map((p) => p.name);
      const product_to_scene_map = Object.fromEntries(
        state.products.map((p) => [p.name, p.scene])
      );
      const product_descriptions = Object.fromEntries(
        state.products.map((p) => [p.name, p.description])
      );

      const settingsToSave = {
        tiktok_username: settingsForm.querySelector("#tiktok_username").value,
        deepseek_api_key: settingsForm.querySelector("#deepseek_api_key").value,
        main_scene_name: settingsForm.querySelector("#main_scene_name").value,
        obs_ws_host: settingsForm.querySelector("#obs_ws_host").value,
        obs_ws_port: parseInt(
          settingsForm.querySelector("#obs_ws_port").value,
          10
        ),
        obs_ws_password: settingsForm.querySelector("#obs_ws_password").value,
        comment_rate_limit: parseInt(
          settingsForm.querySelector("#rate_limit").value,
          10
        ),
        tiktok_reconnect_delay: parseInt(
          settingsForm.querySelector("#reconnect_delay").value,
          10
        ),
        cache_duration_seconds: parseInt(
          settingsForm.querySelector("#cache_duration").value,
          10
        ),
        product_list,
        product_to_scene_map,
        product_descriptions,
      };

      const response = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsToSave),
      });

      const result = await response.json();
      if (!response.ok)
        throw new Error(result.error || "Failed to save settings.");

      showToast("Settings saved successfully!", "success");
    } catch (error) {
      console.error("Save settings error:", error);
      showToast(error.message, "error");
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "Save Settings";
    }
  };

  // ======================
  // === EVENT LISTENERS ===
  // ======================

  // Sidebar Navigation
  sidebar.addEventListener("click", (e) => {
    const navItem = e.target.closest(".nav-item");
    if (!navItem) return;
    e.preventDefault();
    const targetPageId = navItem.dataset.page;

    sidebar
      .querySelectorAll(".nav-item")
      .forEach((item) => item.classList.remove("active"));
    navItem.classList.add("active");

    pages.forEach((page) =>
      page.classList.toggle("active", page.id === targetPageId)
    );
  });

  // Bot Controls
  startButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/api/start", { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message);
      showToast(result.message, "success");
      fetchStatusAndLogs(); // Immediate update
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  stopButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/api/stop", { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message);
      showToast(result.message, "success");
      fetchStatusAndLogs(); // Immediate update
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  // Product Actions
  addProductBtn.addEventListener("click", () => showProductModal());
  productsContainer.addEventListener("click", (e) => {
    const editBtn = e.target.closest(".btn-edit");
    const deleteBtn = e.target.closest(".btn-delete");

    if (editBtn) {
      const index = parseInt(
        editBtn.closest(".product-item").dataset.index,
        10
      );
      showProductModal(index);
    }
    if (deleteBtn) {
      if (confirm("Are you sure you want to delete this product?")) {
        const index = parseInt(
          deleteBtn.closest(".product-item").dataset.index,
          10
        );
        state.products.splice(index, 1);
        renderProducts();
        showToast("Product deleted.", "success");
      }
    }
  });

  // Settings Form
  settingsForm.addEventListener("submit", handleSaveSettings);

  // ====================
  // === INITIALIZATION ===
  // ====================
  const initialize = async () => {
    await loadSettings();
    await fetchStatusAndLogs();
    statusPollInterval = setInterval(fetchStatusAndLogs, 3000); // Poll every 3 seconds
  };

  initialize();
});
