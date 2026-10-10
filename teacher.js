/**
 * PixelWise AI — Teacher Portal Controller
 * Coordinates material creation, real-time decision inspection, E(C) visualization,
 * preview rendering, and printable worksheet formatting.
 */

document.addEventListener("DOMContentLoaded", () => {
  initTeacherPortal();
});

let currentActiveMaterialType = "worksheet";
let currentGenerationResult = null;
let preflightTimeout = null;

function initTeacherPortal() {
  const promptInput = document.getElementById("prompt-input");
  const charCount = document.getElementById("prompt-char-count");
  const generateBtn = document.getElementById("generate-btn");
  const materialChips = document.querySelectorAll(".mat-chip");
  const presetChips = document.querySelectorAll(".chip-preset");
  const auditToggle = document.getElementById("audit-toggle");

  // Load school choices into dropdown
  loadSchoolsDropdown();

  // Material type chip selection
  materialChips.forEach(chip => {
    chip.addEventListener("click", () => {
      materialChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      currentActiveMaterialType = chip.getAttribute("data-type");
      triggerPreflightAnalysis();
    });
  });

  // Prompt preset clicks
  presetChips.forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      const type = btn.getAttribute("data-type");
      const grade = btn.getAttribute("data-grade");

      promptInput.value = prompt;
      charCount.textContent = `${prompt.length} chars`;

      // Select material type
      materialChips.forEach(c => {
        if (c.getAttribute("data-type") === type) {
          c.classList.add("active");
          currentActiveMaterialType = type;
        } else {
          c.classList.remove("active");
        }
      });

      // Select grade
      const gradeSelect = document.getElementById("grade-select");
      if (gradeSelect && grade) {
        gradeSelect.value = grade;
      }

      triggerPreflightAnalysis();
    });
  });

  // Prompt typing listener with debounce for pre-flight analysis
  if (promptInput) {
    promptInput.addEventListener("input", () => {
      charCount.textContent = `${promptInput.value.length} chars`;
      clearTimeout(preflightTimeout);
      preflightTimeout = setTimeout(triggerPreflightAnalysis, 400);
    });
  }

  // Generate Button Click
  if (generateBtn) {
    generateBtn.addEventListener("click", handleGenerateSubmit);
  }

  // Audit accordion toggle
  if (auditToggle) {
    auditToggle.addEventListener("click", () => {
      const body = document.getElementById("audit-body");
      const icon = auditToggle.querySelector(".toggle-icon");
      if (body) {
        const isHidden = body.style.display === "none";
        body.style.display = isHidden ? "block" : "none";
        icon.textContent = isHidden ? "▲" : "▼";
      }
    });
  }

  // Action Buttons
  document.getElementById("btn-print-worksheet")?.addEventListener("click", handlePrintWorksheet);
  document.getElementById("btn-download-asset")?.addEventListener("click", handleDownloadAsset);
  document.getElementById("btn-q-pass")?.addEventListener("click", () => handleTeacherFeedback(true));
  document.getElementById("btn-q-flag")?.addEventListener("click", () => handleTeacherFeedback(false));
}

async function loadSchoolsDropdown() {
  const select = document.getElementById("school-select");
  if (!select) return;

  try {
    const res = await fetch("/api/schools");
    const data = await res.json();
    if (data.schools && data.schools.length > 0) {
      select.innerHTML = "";
      data.schools.forEach(sch => {
        const opt = document.createElement("option");
        opt.value = sch.id;
        opt.textContent = `${sch.id}: ${sch.name} (${sch.zone})`;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    console.warn("Could not load dynamic schools list:", err);
  }
}

async function triggerPreflightAnalysis() {
  const promptInput = document.getElementById("prompt-input");
  const preflightPill = document.getElementById("preflight-pill");
  const preflightText = document.getElementById("preflight-text");
  const gradeSelect = document.getElementById("grade-select");
  const schoolSelect = document.getElementById("school-select");

  if (!promptInput || !promptInput.value.trim()) {
    if (preflightText) preflightText.textContent = "Predicted Route: Enter a prompt to preview optimal cost allocation...";
    return;
  }

  try {
    const res = await fetch("/api/analyze-preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: promptInput.value.trim(),
        material_type: currentActiveMaterialType,
        grade_level: gradeSelect ? gradeSelect.value : "primary",
        school_id: schoolSelect ? schoolSelect.value : "SCH-001"
      })
    });

    const data = await res.json();
    if (data.routing && preflightText) {
      const tierName = data.routing.tier_name;
      const expCost = data.routing.expected_total_cost;
      preflightText.innerHTML = `Predicted Allocation: <strong>${tierName}</strong> (Expected Cost: <strong>₹${expCost.toFixed(2)}</strong> vs ₹6.00 baseline)`;
    }
  } catch (err) {
    console.warn("Preflight preview error:", err);
  }
}

async function handleGenerateSubmit() {
  const promptInput = document.getElementById("prompt-input");
  const generateBtn = document.getElementById("generate-btn");
  const spinner = document.getElementById("gen-spinner");
  const btnText = document.getElementById("gen-btn-text");
  const gradeSelect = document.getElementById("grade-select");
  const schoolSelect = document.getElementById("school-select");
  const teacherInput = document.getElementById("teacher-name");
  const forceDefect = document.getElementById("force-defect-toggle")?.checked || false;

  const prompt = promptInput?.value.trim();
  if (!prompt) {
    window.showToast("Please enter a prompt description first.", "error");
    promptInput.focus();
    return;
  }

  // Update button state
  generateBtn.disabled = true;
  if (spinner) spinner.style.display = "inline-block";
  if (btnText) btnText.textContent = "Analyzing & Optimizing Cloud Resources...";

  // Reset Stepper
  resetPipelineStepper();

  try {
    // Step 1: Activate classification
    activateStep(1, "Analyzing...", "active");

    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: prompt,
        material_type: currentActiveMaterialType,
        grade_level: gradeSelect ? gradeSelect.value : "primary",
        school_id: schoolSelect ? schoolSelect.value : "SCH-001",
        teacher_name: teacherInput ? teacherInput.value : "Teacher",
        force_defect: forceDefect
      })
    });

    const result = await response.json();
    currentGenerationResult = result;

    if (result.error) {
      window.showToast(result.error, "error");
      return;
    }

    // Animate through decision layers
    await animatePipelineDecision(result);

    // Render result image / SVG
    renderOutputAsset(result);

    // Update global savings header badge
    if (typeof fetchDistrictHeaderTelemetry === "function") {
      fetchDistrictHeaderTelemetry();
    }

    window.showToast(`Resource Allocated: Saved ₹${result.cost_saved.toFixed(2)} (${result.savings_pct}%)!`, "success");

  } catch (err) {
    console.error("Generation error:", err);
    window.showToast("An error occurred during request processing.", "error");
  } finally {
    generateBtn.disabled = false;
    if (spinner) spinner.style.display = "none";
    if (btnText) btnText.textContent = "⚡ Generate Material (Cost-Optimized)";
  }
}

function resetPipelineStepper() {
  for (let i = 1; i <= 6; i++) {
    const item = document.getElementById(`step-${i}`);
    if (item) item.className = "step-item";
    const line = document.getElementById(`line-${i}`);
    if (line) line.className = "step-line";
  }
  const badge = document.getElementById("pipeline-status-badge");
  if (badge) {
    badge.className = "pipeline-badge active";
    badge.textContent = "Processing Pipeline...";
  }
}

function activateStep(stepNum, desc, state = "completed") {
  const item = document.getElementById(`step-${stepNum}`);
  if (item) {
    item.className = `step-item ${state}`;
    const descElem = document.getElementById(`step-${stepNum}-desc`);
    if (descElem && desc) descElem.textContent = desc;
  }
  if (stepNum > 1) {
    const line = document.getElementById(`line-${stepNum - 1}`);
    if (line) line.className = "step-line completed";
  }
}

async function animatePipelineDecision(res) {
  // 1. Classification
  activateStep(1, res.classification.visual_style.replace(/_/g, " "), "completed");
  await sleep(150);

  // 2. Reuse Check
  const isReuse = res.routing.chosen_tier === "TIER_0_REUSE";
  activateStep(2, isReuse ? "Cache Hit (₹0)" : "Cache Miss (Synthesize)", "completed");
  await sleep(150);

  // 3. Cost Router
  activateStep(3, `E(C) = ₹${res.routing.expected_total_cost.toFixed(2)}`, "completed");
  renderExpectedCostFormulas(res.routing.options, res.routing.chosen_tier);
  await sleep(150);

  // 4. Generation
  activateStep(4, res.routing.tier_name.split("(")[0], "completed");
  await sleep(150);

  // 5. Verification & Auto-Correction
  const wasAutocorrected = res.final_status === "DELIVERED_AUTOCORRECTED";
  activateStep(5, wasAutocorrected ? "PIL Repaired (₹0.02)" : "Verified 100%", "completed");
  await sleep(150);

  // 6. Delivered
  activateStep(6, `Final: ₹${res.actual_cost.toFixed(2)}`, "completed");

  const badge = document.getElementById("pipeline-status-badge");
  if (badge) {
    badge.className = "pipeline-badge success";
    badge.textContent = `${res.final_status.replace(/_/g, " ")} • ₹${res.actual_cost.toFixed(2)}`;
  }
}

function renderExpectedCostFormulas(options, chosenTier) {
  const box = document.getElementById("ec-breakdown-box");
  const grid = document.getElementById("ec-tiers-grid");
  if (!box || !grid || !options) return;

  grid.innerHTML = "";
  box.style.display = "block";

  Object.keys(options).forEach(tierKey => {
    const opt = options[tierKey];
    const isWinner = tierKey === chosenTier;

    const card = document.createElement("div");
    card.className = `ec-tier-card ${isWinner ? "winner" : ""}`;

    card.innerHTML = `
      <div class="ec-tier-title">
        <span>${opt.name.split("(")[0]}</span>
        ${isWinner ? '<span class="winner-tag">★ SELECTED OPTIMAL</span>' : ''}
      </div>
      <div class="ec-formula-text">${opt.formula_display}</div>
      <div style="margin-top: 4px; font-weight: 600; color: ${isWinner ? 'var(--accent-emerald)' : 'var(--text-muted)'};">
        Expected Total: ₹${opt.expected_total_cost.toFixed(2)} (Pass: ${opt.pass_rate_pct}%)
      </div>
    `;

    grid.appendChild(card);
  });
}

function renderOutputAsset(res) {
  const viewport = document.getElementById("preview-viewport");
  const placeholder = document.getElementById("viewport-placeholder");
  const svgContainer = document.getElementById("svg-container");
  const renderedImg = document.getElementById("rendered-image");
  const actions = document.getElementById("result-actions");
  const feedbackBar = document.getElementById("quality-feedback-bar");
  const tierTag = document.getElementById("result-tier-tag");
  const savingsBanner = document.getElementById("savings-banner");

  if (placeholder) placeholder.style.display = "none";
  if (actions) actions.style.display = "flex";
  if (feedbackBar) feedbackBar.style.display = "flex";

  // Tier tag
  if (tierTag) {
    tierTag.textContent = `${res.routing.tier_name} • Actual Cost: ₹${res.actual_cost.toFixed(2)}`;
  }

  // Display SVG or Bitmap image
  if (res.asset_type === "svg" && res.svg_content) {
    if (renderedImg) renderedImg.style.display = "none";
    if (svgContainer) {
      svgContainer.style.display = "flex";
      svgContainer.innerHTML = res.svg_content;
    }
  } else if (res.image_url) {
    if (svgContainer) svgContainer.style.display = "none";
    if (renderedImg) {
      renderedImg.style.display = "block";
      renderedImg.src = res.image_url + `?t=${Date.now()}`;
    }
  }

  // Savings Banner
  if (savingsBanner) {
    savingsBanner.style.display = "flex";
    document.getElementById("savings-headline").textContent = `₹${res.cost_saved.toFixed(2)} Saved (${res.savings_pct}% Cloud Reduction)`;
    document.getElementById("banner-baseline-cost").textContent = `₹${res.baseline_cost.toFixed(2)}`;
    document.getElementById("banner-actual-cost").textContent = `₹${res.actual_cost.toFixed(2)}`;
    
    let subExplanation = `Fulfilled via ${res.routing.tier_name}.`;
    if (res.final_status === "DELIVERED_AUTOCORRECTED") {
      subExplanation = "Inexpensive PIL binarization cleaned gray background at ₹0.02, avoiding a ₹5.50 regeneration!";
    } else if (res.routing.chosen_tier === "TIER_0_REUSE") {
      subExplanation = "100% cost elimination: Reused pre-approved educational asset from district library.";
    }
    document.getElementById("savings-sub").textContent = subExplanation;
  }

  // Populate Audit Card
  populateAuditCard(res);
}

function populateAuditCard(res) {
  const auditCard = document.getElementById("audit-card");
  if (!auditCard) return;
  auditCard.style.display = "block";

  // Classification column
  const classList = document.getElementById("audit-class-list");
  if (classList) {
    classList.innerHTML = `
      <li><strong>Style:</strong> ${res.classification.visual_style}</li>
      <li><strong>Complexity:</strong> ${res.classification.complexity_score} / 5</li>
      <li><strong>Priority:</strong> ${res.classification.quality_priority}</li>
      <li><strong>Zero-AI Eligible:</strong> ${res.classification.zero_ai_eligible ? 'Yes' : 'No'}</li>
      <li><strong>Tokens:</strong> ${res.classification.detected_tags.join(", ") || "generic"}</li>
    `;
  }

  // Verification column
  const verifList = document.getElementById("audit-verif-list");
  if (verifList && res.attempts_log) {
    verifList.innerHTML = "";
    res.attempts_log.forEach(att => {
      const v = att.verification_result || {};
      const li = document.createElement("li");
      li.innerHTML = `<strong>Att ${att.attempt}:</strong> ${att.action} → <em>${att.status}</em><br><small>${v.details || 'Verified'}</small>`;
      verifList.appendChild(li);
    });
  }

  // Cost column
  const costList = document.getElementById("audit-cost-list");
  if (costList) {
    costList.innerHTML = `
      <li><strong>Total Billed:</strong> ₹${res.actual_cost.toFixed(2)}</li>
      <li><strong>Naive Price:</strong> ₹${res.baseline_cost.toFixed(2)}</li>
      <li><strong>Net Savings:</strong> ₹${res.cost_saved.toFixed(2)} (${res.savings_pct}%)</li>
      <li><strong>Status:</strong> ${res.final_status}</li>
      <li><strong>Request ID:</strong> ${res.request_id}</li>
    `;
  }
}

function handlePrintWorksheet() {
  if (!currentGenerationResult) return;

  const schoolSelect = document.getElementById("school-select");
  const schoolName = schoolSelect ? schoolSelect.options[schoolSelect.selectedIndex].text.split(":")[1] : "District School";
  
  const printTitle = document.getElementById("print-title");
  const printSchool = document.getElementById("print-school-name");
  const printContent = document.getElementById("print-content");

  if (printTitle) printTitle.textContent = currentGenerationResult.prompt.slice(0, 60);
  if (printSchool) printSchool.textContent = schoolName;

  if (printContent) {
    if (currentGenerationResult.asset_type === "svg" && currentGenerationResult.svg_content) {
      printContent.innerHTML = currentGenerationResult.svg_content;
    } else if (currentGenerationResult.image_url) {
      printContent.innerHTML = `<img src="${currentGenerationResult.image_url}" style="max-width: 100%; max-height: 18cm;" />`;
    }
  }

  // Invoke browser print dialog
  window.print();
}

function handleDownloadAsset() {
  if (!currentGenerationResult) return;

  if (currentGenerationResult.asset_type === "svg" && currentGenerationResult.svg_content) {
    const blob = new Blob([currentGenerationResult.svg_content], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentGenerationResult.request_id}_worksheet.svg`;
    a.click();
    URL.revokeObjectURL(url);
    window.showToast("Downloaded Scalable Vector (SVG) asset.", "success");
  } else if (currentGenerationResult.image_url) {
    const a = document.createElement("a");
    a.href = currentGenerationResult.image_url;
    a.download = `${currentGenerationResult.request_id}_image.png`;
    a.click();
    window.showToast("Downloaded Image (PNG) asset.", "success");
  }
}

async function handleTeacherFeedback(isApproved) {
  if (!currentGenerationResult) return;

  const msgElem = document.getElementById("q-feedback-msg");
  try {
    await fetch("/api/flag-request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: currentGenerationResult.request_id,
        is_positive: isApproved,
        feedback: isApproved ? "Classroom Approved" : "Teacher flagged quality defect"
      })
    });

    if (msgElem) {
      msgElem.textContent = isApproved ? "✓ Teacher Approval Saved" : "⚠️ Quality Flag Logged for District Review";
      msgElem.style.color = isApproved ? "var(--accent-emerald)" : "var(--accent-rose)";
    }
  } catch (err) {
    console.warn("Feedback error:", err);
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
