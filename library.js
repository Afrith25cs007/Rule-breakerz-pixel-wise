/**
 * PixelWise AI — Shared District Library Explorer Controller
 * Allows teachers and curriculum directors to browse, search, and reuse approved educational assets.
 */

document.addEventListener("DOMContentLoaded", () => {
  initLibraryExplorer();
});

let currentLibCategory = "ALL";
let currentLibSearch = "";

function initLibraryExplorer() {
  const searchInput = document.getElementById("library-search-input");
  const categorySelect = document.getElementById("library-category-select");

  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        currentLibSearch = e.target.value.trim();
        loadLibraryAssets();
      }, 300);
    });
  }

  if (categorySelect) {
    categorySelect.addEventListener("change", (e) => {
      currentLibCategory = e.target.value;
      loadLibraryAssets();
    });
  }

  loadLibraryAssets();
}

async function loadLibraryAssets() {
  const grid = document.getElementById("library-grid");
  if (!grid) return;

  grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-dim);">Loading district asset cache...</div>`;

  try {
    const url = `/api/library/assets?category=${encodeURIComponent(currentLibCategory)}&search=${encodeURIComponent(currentLibSearch)}`;
    const res = await fetch(url);
    const data = await res.json();

    grid.innerHTML = "";

    if (!data.assets || data.assets.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-dim);">No educational assets found matching criteria.</div>`;
      return;
    }

    data.assets.forEach(ast => {
      const card = document.createElement("div");
      card.className = "asset-card";

      let previewHtml = "";
      if (ast.svg_markup) {
        previewHtml = `<div class="asset-preview-box">${ast.svg_markup}</div>`;
      } else {
        previewHtml = `<div class="asset-preview-box" style="color: #64748b; font-size: 2rem;">🖼️</div>`;
      }

      card.innerHTML = `
        ${previewHtml}
        <div class="asset-meta-row">
          <span class="status-badge" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc; text-transform: uppercase;">${ast.category}</span>
          <span class="asset-usage-pill">★ Used in ${ast.usage_count} schools</span>
        </div>
        <div class="asset-title">${ast.title}</div>
        <div class="asset-tags">Tags: ${ast.tags.split(",").slice(0, 4).join(", ")}</div>
        <div class="asset-card-actions">
          <button class="btn btn-primary btn-sm btn-use-asset" style="width: 100%;">
            🖍️ Use in Teacher Portal (₹0 Reuse)
          </button>
        </div>
      `;

      // Handle clicking "Use in Teacher Portal"
      card.querySelector(".btn-use-asset").addEventListener("click", () => {
        useAssetInTeacherPortal(ast);
      });

      grid.appendChild(card);
    });

  } catch (err) {
    console.warn("Error loading library assets:", err);
  }
}

function useAssetInTeacherPortal(ast) {
  const promptInput = document.getElementById("prompt-input");
  const teacherTabBtn = document.getElementById("tab-btn-teacher");

  if (promptInput) {
    promptInput.value = ast.title;
    document.getElementById("prompt-char-count").textContent = `${ast.title.length} chars`;
  }

  // Set material type
  const chips = document.querySelectorAll(".mat-chip");
  chips.forEach(c => {
    if (c.getAttribute("data-type") === ast.category) {
      c.classList.add("active");
    } else {
      c.classList.remove("active");
    }
  });

  // Switch to teacher view
  if (teacherTabBtn) {
    teacherTabBtn.click();
    window.showToast(`Selected "${ast.title}" for classroom generation.`, "success");
    // Trigger pre-flight preview
    if (typeof triggerPreflightAnalysis === "function") {
      triggerPreflightAnalysis();
    }
  }
}
