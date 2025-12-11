import { API } from "./api.js";
import { UI } from "./ui.js";

export const Gallery = {
  availableVideos: [],
  grid: document.getElementById("galleryGrid"),
  uploadInput: document.getElementById("videoUploadInput"),

  init() {
    if (this.uploadInput) {
      this.uploadInput.addEventListener("change", (e) => this.handleUpload(e));
    }
    this.load();
  },

  async load() {
    try {
      this.availableVideos = await API.get("/api/media");
      this.render();
    } catch (e) {
      console.error(e);
    }
  },

  render() {
    if (!this.grid) return;
    this.grid.innerHTML = "";
    this.availableVideos.forEach((filename) => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
                <div style="position: relative;">
                    <video src="/media/${filename}" controls style="width: 100%; height: 120px; object-fit: cover; background:#000;"></video>
                    <div style="padding: 0.5rem; font-size: 0.8rem; word-break: break-all; font-weight: 500;">${filename}</div>
                </div>
            `;
      this.grid.appendChild(card);
    });
  },

  async handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    UI.showToast("Uploading...", "info");
    try {
      const data = await API.upload("/api/upload", formData);
      if (data.status === "success") {
        UI.showToast("Upload complete");
        this.load();
      } else {
        UI.showToast(data.message, "error");
      }
    } catch (e) {
      UI.showToast("Upload failed", "error");
    }
  },
};
