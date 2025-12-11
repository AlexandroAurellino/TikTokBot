export const UI = {
  toastContainer: document.getElementById("toastContainer"),

  showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`; // You might want to update toast CSS styles too in style.css to match shadcn
    toast.innerHTML = `<div class="toast-title">${
      type === "error" ? "Error" : "Success"
    }</div><div class="text-sm text-muted">${message}</div>`;
    this.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  },

  initTheme() {
    // Check local storage or system preference
    const isDark =
      localStorage.getItem("theme") === "dark" ||
      (!localStorage.getItem("theme") &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);

    this.applyTheme(isDark);

    const btn = document.getElementById("themeToggleBtn");
    if (btn) {
      btn.addEventListener("click", () => {
        const wasDark = document.documentElement.classList.contains("dark");
        this.applyTheme(!wasDark);
      });
    }
  },

  applyTheme(isDark) {
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
      this.updateThemeIcon(true);
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
      this.updateThemeIcon(false);
    }
  },

  updateThemeIcon(isDark) {
    const icon = document.getElementById("themeIcon");
    if (!icon) return;
    if (!isDark) {
      // Sun icon
      icon.innerHTML =
        '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
    } else {
      // Moon icon
      icon.innerHTML =
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
    }
  },
};
