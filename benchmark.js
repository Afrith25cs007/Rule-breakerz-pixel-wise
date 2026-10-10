/**
 * PixelWise AI — Savings Benchmark Controller
 * Executes side-by-side comparative simulation of Naive Baseline vs PixelWise AI.
 */

document.addEventListener("DOMContentLoaded", () => {
  const runBtn = document.getElementById("btn-run-benchmark");
  if (runBtn) {
    runBtn.addEventListener("click", runLiveBenchmark);
  }
});

async function runLiveBenchmark() {
  const runBtn = document.getElementById("btn-run-benchmark");
  const tbody = document.getElementById("benchmark-tbody");
  const summaryBox = document.getElementById("benchmark-summary");

  if (!runBtn || !tbody) return;

  runBtn.disabled = true;
  runBtn.innerHTML = `⚡ Running 5 Live Prompts across 300 Schools...`;
  tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 2.5rem; color: var(--accent-cyan);">⚡ Evaluating prompts through Naive Baseline and PixelWise Decision Router...</td></tr>`;

  try {
    const res = await fetch("/api/benchmark-sample", { method: "POST" });
    const data = await res.json();

    tbody.innerHTML = "";

    if (data.benchmark_results && data.benchmark_results.length > 0) {
      data.benchmark_results.forEach(row => {
        const tr = document.createElement("tr");

        let badgeStyle = "background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald);";
        if (row.chosen_tier === "TIER_3_ADVANCED_AI") {
          badgeStyle = "background: rgba(99, 102, 241, 0.15); color: #a5b4fc;";
        } else if (row.chosen_tier === "TIER_0_REUSE") {
          badgeStyle = "background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan);";
        }

        tr.innerHTML = `
          <td><strong>${row.prompt}</strong></td>
          <td><span style="text-transform: capitalize; font-size: 0.8rem; color: var(--text-muted);">${row.material_type}</span></td>
          <td style="color: var(--accent-rose);">PixelPro-HD (Fixed Premium)</td>
          <td><del style="color: var(--accent-rose); font-family: var(--font-mono);">₹${row.baseline_cost.toFixed(2)}</del></td>
          <td><span class="status-badge" style="${badgeStyle}">${row.tier_name.split("(")[0]}</span></td>
          <td><strong style="color: var(--accent-emerald); font-family: var(--font-mono);">₹${row.pixelwise_cost.toFixed(2)}</strong></td>
          <td><strong style="color: var(--accent-cyan); font-family: var(--font-mono);">₹${row.cost_saved.toFixed(2)}</strong></td>
          <td><strong style="color: var(--accent-emerald);">${row.savings_pct}%</strong></td>
        `;
        tbody.appendChild(tr);
      });

      // Update Summary Footprint
      if (summaryBox) {
        summaryBox.style.display = "flex";
        document.getElementById("b-tot-baseline").textContent = `₹${data.total_baseline.toFixed(2)}`;
        document.getElementById("b-tot-pixelwise").textContent = `₹${data.total_pixelwise.toFixed(2)}`;
        document.getElementById("b-tot-saved").textContent = `₹${data.total_saved.toFixed(2)}`;
        document.getElementById("b-tot-pct").textContent = `${data.overall_savings_pct}% Cloud Expenditure Reduction`;
      }

      window.showToast(`Benchmark Complete: ₹${data.total_saved.toFixed(2)} saved across 5 classroom prompts (${data.overall_savings_pct}%)!`, "success");
    }

  } catch (err) {
    console.error("Benchmark error:", err);
    window.showToast("Benchmark execution failed.", "error");
  } finally {
    runBtn.disabled = false;
    runBtn.innerHTML = `⚡ Run 5-Prompt Live District Benchmark`;
  }
}
