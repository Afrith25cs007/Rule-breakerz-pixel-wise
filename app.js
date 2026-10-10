/**
 * PixelWise AI — App Controller
 * Handles navigation tab switching, theme toggling, global telemetry, and notifications.
 */

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initThemeToggle();
  fetchDistrictHeaderTelemetry();
});

function initNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  const views = document.querySelectorAll(".view-panel");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");

      tabs.forEach(t => t.classList.remove("active"));
      views.forEach(v => v.classList.remove("active"));

      tab.classList.add("active");
      const targetView = document.getElementById(targetId);
      if (targetView) {
        targetView.classList.add("active");
      }

      // If switching to admin, refresh charts and metrics
      if (targetId === "admin-view" && window.adminDashboard) {
        window.adminDashboard.refresh();
      }
    });
  });
}

function initThemeToggle() {
  const toggleBtn = document.getElementById("theme-toggle-btn");
  const themeIcon = document.getElementById("theme-icon");

  if (!toggleBtn) return;

  toggleBtn.addEventListener("click", () => {
    document.body.classList.toggle("light-theme");
    const isLight = document.body.classList.contains("light-theme");
    themeIcon.textContent = isLight ? "☀️" : "🌙";
  });
}

async function fetchDistrictHeaderTelemetry() {
  try {
    const res = await fetch("/api/admin/metrics");
    const data = await res.json();
    const savedElem = document.getElementById("header-saved-value");
    if (savedElem && data.total_saved !== undefined) {
      savedElem.textContent = `₹${data.total_saved.toLocaleString()} (${data.savings_pct}%)`;
    }
  } catch (err) {
    console.warn("Could not fetch header telemetry:", err);
  }
}

// Global Toast / Notification Helper
window.showToast = function(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast-popup ${type}`;
  toast.textContent = message;
  toast.style.position = "fixed";
  toast.style.bottom = "24px";
  toast.style.right = "24px";
  toast.style.padding = "12px 20px";
  toast.style.borderRadius = "8px";
  toast.style.background = type === "success" ? "#10b981" : "#f43f5e";
  toast.style.color = "#ffffff";
  toast.style.fontWeight = "600";
  toast.style.fontSize = "0.9rem";
  toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.3)";
  toast.style.zIndex = "9999";
  toast.style.transition = "all 0.3s ease";
  
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
};
