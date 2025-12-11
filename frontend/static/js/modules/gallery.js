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

    if (this.availableVideos.length === 0) {
      this.grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem;">
          <svg
            style="width: 64px; height: 64px; margin: 0 auto 1rem; color: hsl(var(--muted-foreground));"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
            <line x1="7" y1="2" x2="7" y2="22"></line>
            <line x1="17" y1="2" x2="17" y2="22"></line>
            <line x1="2" y1="12" x2="22" y2="12"></line>
          </svg>
          <h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; color: hsl(var(--foreground));">No Videos Yet</h3>
          <p style="color: hsl(var(--muted-foreground)); margin-bottom: 1.5rem;">Upload your first product video to get started.</p>
        </div>
      `;
      return;
    }

    this.availableVideos.forEach((filename) => {
      const card = document.createElement("div");
      card.className = "card gallery-card";
      card.innerHTML = `
        <div style="position: relative;">
          <video 
            src="/media/${filename}" 
            controls 
            style="width: 100%; height: 140px; object-fit: cover; background: hsl(var(--muted)); display: block;"
          ></video>
          <div style="padding: 0.875rem;">
            <div style="font-size: 0.8125rem; font-weight: 500; color: hsl(var(--foreground)); word-break: break-all;">
              ${filename}
            </div>
            <div style="font-size: 0.75rem; color: hsl(var(--muted-foreground)); margin-top: 0.25rem;">
              Video file
            </div>
          </div>
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

    UI.showToast("Uploading video...", "info");
    try {
      const data = await API.upload("/api/upload", formData);
      if (data.status === "success") {
        UI.showToast("Upload complete!", "success");
        this.load();
        // Reset input
        e.target.value = "";
      } else {
        UI.showToast(data.message || "Upload failed", "error");
      }
    } catch (e) {
      UI.showToast("Upload failed", "error");
    }
  },
};
