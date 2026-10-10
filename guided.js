/**
 * PixelWise AI — Evaluator Guided Tour Controller
 * Powers 1-click live execution of the 5 core district demonstration scenarios.
 */

document.addEventListener("DOMContentLoaded", () => {
  initGuidedTour();
});

async function initGuidedTour() {
  const container = document.getElementById("guided-scenarios-grid");
  if (!container) return;

  try {
    const res = await fetch("/api/guided-scenarios");
    const data = await res.json();

    container.innerHTML = "";

    if (data.scenarios && data.scenarios.length > 0) {
      data.scenarios.forEach((sc, idx) => {
        const card = document.createElement("div");
        card.className = "scenario-card";

        card.innerHTML = `
          <span class="scenario-number-badge">DEMO SCENARIO ${idx + 1} OF 5</span>
          <h3>${sc.title.split(":")[1] || sc.title}</h3>
          <p class="scenario-desc">${sc.description}</p>
          <div class="scenario-meta-box">
            <div><strong>Prompt:</strong> "${sc.prompt}"</div>
            <span class="scenario-outcome">Expected Result: ${sc.expected_outcome}</span>
          </div>
          <button class="btn btn-primary btn-run-scenario" data-scenario-id="${sc.id}">
            ⚡ Run Scenario &amp; Inspect Decision Pipeline
          </button>
        `;

        card.querySelector(".btn-run-scenario").addEventListener("click", () => {
          executeGuidedScenario(sc);
        });

        container.appendChild(card);
      });
    }

  } catch (err) {
    console.warn("Error initializing guided scenarios:", err);
  }
}

function executeGuidedScenario(sc) {
  // 1. Switch to Teacher Portal tab
  const teacherTabBtn = document.getElementById("tab-btn-teacher");
  if (teacherTabBtn) teacherTabBtn.click();

  // 2. Populate Teacher Form fields
  const promptInput = document.getElementById("prompt-input");
  const gradeSelect = document.getElementById("grade-select");
  const schoolSelect = document.getElementById("school-select");
  const forceDefectToggle = document.getElementById("force-defect-toggle");
  const generateBtn = document.getElementById("generate-btn");

  if (promptInput) {
    promptInput.value = sc.prompt;
    document.getElementById("prompt-char-count").textContent = `${sc.prompt.length} chars`;
  }

  if (gradeSelect) gradeSelect.value = sc.grade_level;
  if (schoolSelect) schoolSelect.value = sc.school_id;
  if (forceDefectToggle) forceDefectToggle.checked = sc.force_defect || false;

  // Set material type chip
  const chips = document.querySelectorAll(".mat-chip");
  chips.forEach(c => {
    if (c.getAttribute("data-type") === sc.material_type) {
      c.classList.add("active");
    } else {
      c.classList.remove("active");
    }
  });

  window.showToast(`Executing Guided Demo: ${sc.title}...`, "success");

  // 3. Trigger generation after a brief 300ms pause for visual smooth transition
  setTimeout(() => {
    if (generateBtn) generateBtn.click();
  }, 350);
}
