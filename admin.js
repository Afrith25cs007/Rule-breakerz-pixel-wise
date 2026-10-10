/**
 * PixelWise AI — District Administrator Dashboard Controller
 * Governs multi-school expenditure metrics, visual trend charts,
 * 300 schools directory telemetry, and district spending policies.
 */

class AdminDashboard {
  constructor() {
    this.trendChart = null;
    this.tierChart = null;
    this.currentSchoolPage = 1;
    this.schoolPageLimit = 15;
    this.currentSearch = "";
    this.currentZone = "ALL";
    this.init();
  }

  init() {
    this.bindEvents();
    this.refresh();
  }

  bindEvents() {
    document.getElementById("btn-refresh-admin")?.addEventListener("click", () => this.refresh());
    document.getElementById("btn-open-policies")?.addEventListener("click", () => this.openPoliciesModal());
    document.getElementById("btn-close-modal")?.addEventListener("click", () => this.closePoliciesModal());
    document.getElementById("btn-cancel-policies")?.addEventListener("click", () => this.closePoliciesModal());
    document.getElementById("btn-save-policies")?.addEventListener("click", () => this.savePolicies());

    // Search and filter inputs for 300 schools
    const searchInput = document.getElementById("school-search-input");
    if (searchInput) {
      let timeout = null;
      searchInput.addEventListener("input", (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          this.currentSearch = e.target.value.trim();
          this.currentSchoolPage = 1;
          this.loadSchoolsTable();
        }, 300);
      });
    }

    const zoneSelect = document.getElementById("zone-filter-select");
    if (zoneSelect) {
      zoneSelect.addEventListener("change", (e) => {
        this.currentZone = e.target.value;
        this.currentSchoolPage = 1;
        this.loadSchoolsTable();
      });
    }

    // Pagination
    document.getElementById("btn-page-prev")?.addEventListener("click", () => {
      if (this.currentSchoolPage > 1) {
        this.currentSchoolPage--;
        this.loadSchoolsTable();
      }
    });

    document.getElementById("btn-page-next")?.addEventListener("click", () => {
      this.currentSchoolPage++;
      this.loadSchoolsTable();
    });
  }

  async refresh() {
    await Promise.all([
      this.loadMetrics(),
      this.loadSchoolsTable()
    ]);
  }

  async loadMetrics() {
    try {
      const res = await fetch("/api/admin/metrics");
      const data = await res.json();

      // Update KPI cards
      document.getElementById("kpi-actual-spend").textContent = `₹${data.total_actual_spend.toLocaleString()}`;
      document.getElementById("kpi-baseline-spend").textContent = `₹${data.total_baseline_spend.toLocaleString()}`;
      document.getElementById("kpi-saved-spend").textContent = `₹${data.total_saved.toLocaleString()}`;
      document.getElementById("kpi-saved-pct").textContent = `${data.savings_pct}% Cost Reduction`;
      document.getElementById("kpi-total-requests").textContent = data.total_requests.toLocaleString();
      document.getElementById("kpi-zero-cost-pct").textContent = `${data.zero_cost_pct}%`;
      document.getElementById("kpi-zero-count").textContent = `${data.zero_cost_count}`;
      document.getElementById("kpi-avg-cost").textContent = `₹${data.avg_cost_per_image.toFixed(2)}`;
      document.getElementById("kpi-autocorrect-count").textContent = `${data.autocorrect_count}`;

      // Update Charts
      this.renderTrendChart(data.trends);
      this.renderTierChart(data.tier_breakdown);

    } catch (err) {
      console.warn("Error loading admin metrics:", err);
    }
  }

  renderTrendChart(trends) {
    const ctx = document.getElementById("trendChart");
    if (!ctx) return;

    if (this.trendChart) {
      this.trendChart.destroy();
    }

    const labels = (trends && trends.length > 0) ? trends.map(t => t.day.slice(5)) : ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"];
    const actualData = (trends && trends.length > 0) ? trends.map(t => t.actual_spend) : [120, 190, 150, 220, 180];
    const baselineData = (trends && trends.length > 0) ? trends.map(t => t.baseline_spend) : [450, 580, 520, 680, 610];

    this.trendChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Actual Spend (PixelWise AI)",
            data: actualData,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.15)",
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: "#10b981"
          },
          {
            label: "Naive Baseline Spend (Without Optimization)",
            data: baselineData,
            borderColor: "#f43f5e",
            backgroundColor: "transparent",
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0.35,
            pointBackgroundColor: "#f43f5e"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: "#94a3b8", font: { family: "'Outfit', sans-serif", size: 12 } }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ₹${ctx.parsed.y.toFixed(2)}`
            }
          }
        },
        scales: {
          x: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#64748b" }
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: {
              color: "#64748b",
              callback: (val) => `₹${val}`
            }
          }
        }
      }
    });
  }

  renderTierChart(tierBreakdown) {
    const ctx = document.getElementById("tierChart");
    if (!ctx) return;

    if (this.tierChart) {
      this.tierChart.destroy();
    }

    const labels = [];
    const counts = [];
    const colors = ["#10b981", "#06b6d4", "#6366f1", "#a855f7"];

    if (tierBreakdown && tierBreakdown.length > 0) {
      tierBreakdown.forEach(tb => {
        let name = tb.chosen_tier.replace("TIER_", "").replace(/_/g, " ");
        if (tb.chosen_tier === "TIER_0_REUSE") name = "Asset Reuse (₹0)";
        else if (tb.chosen_tier === "TIER_1_ZERO_AI_SVG") name = "Zero-AI SVG (₹0)";
        else if (tb.chosen_tier === "TIER_2_ECO_AI") name = "PixelEco-1 (Std AI)";
        else if (tb.chosen_tier === "TIER_3_ADVANCED_AI") name = "PixelPro-HD (Adv)";
        labels.push(name);
        counts.push(tb.count);
      });
    } else {
      labels.push("Asset Reuse", "Zero-AI SVG", "PixelEco-1", "PixelPro-HD");
      counts.push(40, 25, 45, 15);
    }

    this.tierChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: counts,
          backgroundColor: colors,
          borderColor: "#0f172a",
          borderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", font: { family: "'Outfit', sans-serif", size: 11 } }
          }
        },
        cutout: "68%"
      }
    });
  }

  async loadSchoolsTable() {
    const tbody = document.getElementById("schools-tbody");
    const pageInfo = document.getElementById("pagination-info");
    if (!tbody) return;

    try {
      const url = `/api/admin/schools?page=${this.currentSchoolPage}&limit=${this.schoolPageLimit}&search=${encodeURIComponent(this.currentSearch)}&zone=${encodeURIComponent(this.currentZone)}`;
      const res = await fetch(url);
      const data = await res.json();

      tbody.innerHTML = "";

      if (!data.schools || data.schools.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2rem; color: var(--text-dim);">No schools matching search criteria.</td></tr>`;
        return;
      }

      data.schools.forEach(sch => {
        const utilPct = Math.min(100, Math.round((sch.current_spend / sch.monthly_budget) * 100));
        let badgeClass = "badge-normal";
        let barClass = "";
        let statusText = "Compliant";

        if (utilPct >= 95) {
          badgeClass = "badge-danger";
          barClass = "danger";
          statusText = "Budget Exceeded";
        } else if (utilPct >= 80) {
          badgeClass = "badge-warning";
          barClass = "warning";
          statusText = "Alert (>80%)";
        }

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><code>${sch.id}</code></td>
          <td><strong>${sch.name}</strong></td>
          <td>${sch.zone}</td>
          <td>₹${sch.monthly_budget.toFixed(2)}</td>
          <td><strong>₹${sch.current_spend.toFixed(2)}</strong></td>
          <td>
            <span>${utilPct}%</span>
            <div class="budget-bar-container">
              <div class="budget-bar-fill ${barClass}" style="width: ${utilPct}%;"></div>
            </div>
          </td>
          <td>${sch.total_requests}</td>
          <td>${sch.reused_count}</td>
          <td><span class="status-badge ${badgeClass}">${statusText}</span></td>
        `;
        tbody.appendChild(tr);
      });

      const start = (this.currentSchoolPage - 1) * this.schoolPageLimit + 1;
      const end = Math.min(data.total, this.currentSchoolPage * this.schoolPageLimit);
      if (pageInfo) {
        pageInfo.textContent = `Showing schools ${start} to ${end} of ${data.total} schools`;
      }

      // Update button disabled states
      const prevBtn = document.getElementById("btn-page-prev");
      const nextBtn = document.getElementById("btn-page-next");
      if (prevBtn) prevBtn.disabled = this.currentSchoolPage <= 1;
      if (nextBtn) nextBtn.disabled = end >= data.total;

    } catch (err) {
      console.warn("Error loading schools table:", err);
    }
  }

  async openPoliciesModal() {
    const modal = document.getElementById("policies-modal");
    if (!modal) return;

    try {
      const res = await fetch("/api/policies");
      const data = await res.json();
      const p = data.policies || {};

      document.getElementById("policy-max-retries").value = p.max_retries || 2;
      document.getElementById("policy-max-budget").value = p.max_request_budget || 8.0;
      document.getElementById("policy-school-budget").value = p.school_monthly_budget || 500.0;
      document.getElementById("policy-autocorrect").checked = p.autocorrect_enabled !== false;
      document.getElementById("policy-prefer-zero").checked = p.prefer_zero_ai !== false;

      modal.style.display = "flex";
    } catch (err) {
      modal.style.display = "flex";
    }
  }

  closePoliciesModal() {
    const modal = document.getElementById("policies-modal");
    if (modal) modal.style.display = "none";
  }

  async savePolicies() {
    const payload = {
      max_retries: parseInt(document.getElementById("policy-max-retries").value, 10),
      max_request_budget: parseFloat(document.getElementById("policy-max-budget").value),
      school_monthly_budget: parseFloat(document.getElementById("policy-school-budget").value),
      autocorrect_enabled: document.getElementById("policy-autocorrect").checked,
      prefer_zero_ai: document.getElementById("policy-prefer-zero").checked
    };

    try {
      const res = await fetch("/api/policies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        window.showToast("District spending policies updated across 300 schools.", "success");
        this.closePoliciesModal();
        this.refresh();
      }
    } catch (err) {
      window.showToast("Failed to save district policies.", "error");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.adminDashboard = new AdminDashboard();
});
