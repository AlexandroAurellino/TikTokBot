import { API } from "./api.js";
import { UI } from "./ui.js";
import { Gallery } from "./gallery.js";

export const Products = {
  list: [],
  container: document.getElementById("productsContainer"),
  emptyState: document.getElementById("productsEmptyState"),
  modal: document.getElementById("modalContainer"),
  template: document.getElementById("product-item-template"),
  modalTemplate: document.getElementById("product-modal-template"),

  async init() {
    document
      .getElementById("addProductBtn")
      .addEventListener("click", () => this.openModal());

    this.container.addEventListener("click", (e) => {
      const item = e.target.closest(".product-item");
      if (!item) return;
      const idx = parseInt(item.dataset.index);

      if (e.target.closest(".btn-edit")) this.openModal(idx);
      if (e.target.closest(".btn-delete")) this.delete(idx);

      if (e.target.closest(".btn-play")) {
        this.manualPlay(product.name);
      }
    });

    await this.load();
  },

  async manualPlay(productName) {
    try {
      const res = await API.post("/api/control/play", {
        product_name: productName,
      });
      if (res.status === "success") {
        UI.showToast(`Queued: ${productName}`);
      } else {
        UI.showToast(res.message, "error");
      }
    } catch (e) {
      UI.showToast("Failed to play", "error");
    }
  },

  async load() {
    try {
      const data = await API.get("/api/settings");
      this.list = data.products || [];
      this.render();
    } catch (e) {
      console.error(e);
    }
  },

  render() {
    this.container.innerHTML = "";
    if (this.list.length === 0) {
      this.emptyState.style.display = "block";
      this.container.style.display = "none";
    } else {
      this.emptyState.style.display = "none";
      this.container.style.display = "block";
      this.list.forEach((p, i) => {
        const clone = this.template.content.cloneNode(true);
        const el = clone.querySelector(".product-item");
        el.dataset.index = i;
        el.querySelector(".product-item-name").textContent = p.name;
        el.querySelector(".product-item-scene").textContent =
          p.scene || "No Video";
        el.querySelector(".product-item-description").textContent =
          p.description || "";
        this.container.appendChild(clone);
      });
    }
  },

  openModal(editIndex = null) {
    // Ensure Gallery is fresh
    Gallery.load();

    const isEdit = editIndex !== null;
    const product = isEdit ? this.list[editIndex] : {};

    this.modal.innerHTML = "";
    this.modal.appendChild(this.modalTemplate.content.cloneNode(true));

    const overlay = this.modal.querySelector(".modal-overlay");
    const nameInput = overlay.querySelector("#modal-product-name");
    const descInput = overlay.querySelector("#modal-product-description");
    const sceneInput = overlay.querySelector("#modal-product-scene");
    const saveBtn = overlay.querySelector("#modal-save");

    // Convert Scene input to Dropdown
    const select = document.createElement("select");
    select.className = "form-input";
    let opts = `<option value="">-- Select Video --</option>`;
    Gallery.availableVideos.forEach((v) => {
      opts += `<option value="${v}">${v}</option>`;
    });
    select.innerHTML = opts;
    sceneInput.replaceWith(select);

    // Pre-fill
    overlay.querySelector(".modal-title").textContent = isEdit ? "Edit" : "Add";
    nameInput.value = product.name || "";
    descInput.value = product.description || "";
    select.value = product.scene || "";

    // Events
    const close = () => overlay.remove();
    overlay.querySelector("#modal-cancel").addEventListener("click", close);
    overlay.addEventListener("click", (e) => e.target === overlay && close());

    saveBtn.addEventListener("click", async () => {
      if (!nameInput.value || !select.value) {
        return UI.showToast("Name and Video required", "error");
      }

      const newProd = {
        name: nameInput.value,
        scene: select.value,
        description: descInput.value,
      };

      if (isEdit) this.list[editIndex] = newProd;
      else this.list.push(newProd);

      this.render();
      close();
      await this.saveToBackend();
    });
  },

  async delete(index) {
    if (confirm("Delete product?")) {
      this.list.splice(index, 1);
      this.render();
      await this.saveToBackend();
      UI.showToast("Deleted", "success");
    }
  },

  async saveToBackend() {
    // We need to fetch current settings to avoid overwriting other keys,
    // or just send a PATCH if the backend supported it.
    // For now, re-read settings form to construct full object is safer,
    // but since Settings module handles form, we can just fetch from API first.
    try {
      const currentSettings = await API.get("/api/settings");
      currentSettings.products = this.list;
      await API.post("/api/settings", currentSettings);
      UI.showToast("Products Saved");
    } catch (e) {
      UI.showToast("Save failed", "error");
    }
  },
};
