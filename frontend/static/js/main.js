import { UI } from "./modules/ui.js";
import { Dashboard } from "./modules/dashboard.js";
import { Gallery } from "./modules/gallery.js";
import { Products } from "./modules/products.js";
import { Settings } from "./modules/settings.js";

document.addEventListener("DOMContentLoaded", () => {
  // 1. Initialize UI (Theme, etc)
  UI.initTheme();

  // 2. Connect WebSocket
  const socket = io();
  socket.on("connect", () => console.log("WS Connected"));

  // 3. Initialize Modules
  Dashboard.init(socket);
  Gallery.init();
  Products.init();
  Settings.init();

  // 4. Navigation Logic
  const sidebar = document.querySelector(".sidebar");
  const pages = document.querySelectorAll(".page");

  sidebar.addEventListener("click", (e) => {
    const navItem = e.target.closest(".nav-item");
    if (!navItem) return;
    e.preventDefault();

    // Update Active State
    sidebar
      .querySelectorAll(".nav-item")
      .forEach((i) => i.classList.remove("active"));
    navItem.classList.add("active");

    // Show Page
    const targetId = navItem.dataset.page;
    pages.forEach((p) => p.classList.toggle("active", p.id === targetId));

    // Refresh Gallery if opening that tab
    if (targetId === "gallery") Gallery.load();
  });
});
