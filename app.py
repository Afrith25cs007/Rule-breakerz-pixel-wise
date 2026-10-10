import os
import json
import sqlite3
from flask import Flask, request, jsonify, render_template, send_from_directory
from config import BASE_DIR, STATIC_DIR, DATABASE_PATH, TIERS, CURRENCY, BASELINE_COST_PER_IMAGE
from database import init_db
from modules.orchestrator import PixelWiseOrchestrator
from modules.classifier import RequestClassifier
from modules.zero_ai_library import ZeroAILibrary
from modules.cost_router import CostRouter

app = Flask(__name__, template_folder="templates", static_folder="static")

# Ensure database is initialized on startup
init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/schools", methods=["GET"])
def get_schools():
    """Returns list of schools for teacher selection dropdown."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, zone FROM schools ORDER BY id ASC LIMIT 100")
    schools = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"schools": schools})

@app.route("/api/analyze-preview", methods=["POST"])
def analyze_preview():
    """
    Instant preview endpoint:
    Classifies prompt, checks library reuse, and computes expected costs E(C)
    without generating the image yet.
    """
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    material_type = data.get("material_type", "worksheet")
    grade_level = data.get("grade_level", "primary")
    school_id = data.get("school_id", "SCH-001")

    if not prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    school_info = PixelWiseOrchestrator.get_school(school_id)
    policies = PixelWiseOrchestrator.get_policies()

    classification = RequestClassifier.classify(prompt, material_type, grade_level)
    reuse_result = ZeroAILibrary.check_reuse_library(prompt, classification["detected_tags"], material_type)
    routing = CostRouter.route_request(classification, reuse_result, policies, {
        "current_spend": school_info.get("current_spend", 0.0),
        "monthly_budget": school_info.get("monthly_budget", 500.0),
        "near_limit": False
    })

    return jsonify({
        "classification": classification,
        "reuse_result": {
            "found": reuse_result.get("found", False),
            "title": reuse_result.get("title", ""),
            "usage_count": reuse_result.get("usage_count", 0)
        },
        "routing": routing
    })

@app.route("/api/generate", methods=["POST"])
def generate_image():
    """
    Main image request endpoint:
    Processes the request through the complete decision layer.
    """
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    material_type = data.get("material_type", "worksheet")
    grade_level = data.get("grade_level", "primary")
    school_id = data.get("school_id", "SCH-001")
    teacher_name = data.get("teacher_name", "Teacher")
    force_defect = data.get("force_defect", False)

    if not prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    result = PixelWiseOrchestrator.execute_request(
        school_id=school_id,
        teacher_name=teacher_name,
        prompt=prompt,
        material_type=material_type,
        grade_level=grade_level,
        force_defect=force_defect
    )

    return jsonify(result)

@app.route("/api/admin/metrics", methods=["GET"])
def get_admin_metrics():
    """
    District Dashboard Metrics:
    Aggregates spend, savings, tier usage, category distribution, and timeline across 300 schools.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Core aggregates
    cursor.execute("""
    SELECT 
        COUNT(*) as total_requests,
        COALESCE(SUM(actual_cost), 0.0) as total_actual_spend,
        COALESCE(SUM(baseline_cost), 0.0) as total_baseline_spend,
        COALESCE(SUM(cost_saved), 0.0) as total_saved,
        SUM(CASE WHEN chosen_tier IN ('TIER_0_REUSE', 'TIER_1_ZERO_AI_SVG') THEN 1 ELSE 0 END) as zero_cost_count,
        SUM(CASE WHEN final_status = 'DELIVERED_AUTOCORRECTED' THEN 1 ELSE 0 END) as autocorrect_count,
        SUM(CASE WHEN final_status = 'DELIVERED_ESCALATED' THEN 1 ELSE 0 END) as escalated_count
    FROM generation_requests
    """)
    totals = dict(cursor.fetchone())

    # Tier breakdown
    cursor.execute("""
    SELECT chosen_tier, COUNT(*) as count, SUM(actual_cost) as spend
    FROM generation_requests
    GROUP BY chosen_tier
    """)
    tier_breakdown = [dict(r) for r in cursor.fetchall()]

    # Category breakdown
    cursor.execute("""
    SELECT material_type, COUNT(*) as count, SUM(actual_cost) as spend
    FROM generation_requests
    GROUP BY material_type
    """)
    category_breakdown = [dict(r) for r in cursor.fetchall()]

    # Daily trend (last 14 days)
    cursor.execute("""
    SELECT SUBSTR(created_at, 1, 10) as day, 
           COUNT(*) as requests, 
           ROUND(SUM(actual_cost), 2) as actual_spend,
           ROUND(SUM(baseline_cost), 2) as baseline_spend,
           ROUND(SUM(cost_saved), 2) as saved
    FROM generation_requests
    GROUP BY day
    ORDER BY day ASC
    LIMIT 20
    """)
    trends = [dict(r) for r in cursor.fetchall()]

    # Schools alert count
    cursor.execute("""
    SELECT COUNT(*) as alert_schools
    FROM schools
    WHERE current_spend >= (monthly_budget * 0.8)
    """)
    alert_schools = cursor.fetchone()["alert_schools"]

    conn.close()

    total_req = totals["total_requests"] or 1
    avg_cost = round(totals["total_actual_spend"] / total_req, 2)
    savings_pct = round((totals["total_saved"] / (totals["total_baseline_spend"] or 1)) * 100, 1)
    zero_cost_pct = round((totals["zero_cost_count"] / total_req) * 100, 1)

    return jsonify({
        "total_requests": totals["total_requests"],
        "total_actual_spend": round(totals["total_actual_spend"], 2),
        "total_baseline_spend": round(totals["total_baseline_spend"], 2),
        "total_saved": round(totals["total_saved"], 2),
        "savings_pct": savings_pct,
        "avg_cost_per_image": avg_cost,
        "zero_cost_count": totals["zero_cost_count"],
        "zero_cost_pct": zero_cost_pct,
        "autocorrect_count": totals["autocorrect_count"],
        "escalated_count": totals["escalated_count"],
        "alert_schools": alert_schools,
        "tier_breakdown": tier_breakdown,
        "category_breakdown": category_breakdown,
        "trends": trends,
        "currency": CURRENCY,
        "baseline_unit_price": BASELINE_COST_PER_IMAGE
    })

@app.route("/api/admin/schools", methods=["GET"])
def get_admin_schools():
    """Returns 300 schools list with spend, requests, and search filter."""
    search = request.args.get("search", "").strip()
    zone = request.args.get("zone", "").strip()
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    offset = (page - 1) * limit

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM schools WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if zone and zone != "ALL":
        query += " AND zone = ?"
        params.append(zone)

    query += " ORDER BY current_spend DESC, total_requests DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    schools = [dict(r) for r in cursor.fetchall()]

    # Count total
    count_query = "SELECT COUNT(*) as total FROM schools WHERE 1=1"
    count_params = []
    if search:
        count_query += " AND (name LIKE ? OR id LIKE ?)"
        count_params.extend([f"%{search}%", f"%{search}%"])
    if zone and zone != "ALL":
        count_query += " AND zone = ?"
        count_params.append(zone)

    cursor.execute(count_query, count_params)
    total_count = cursor.fetchone()["total"]

    conn.close()

    return jsonify({
        "schools": schools,
        "total": total_count,
        "page": page,
        "limit": limit
    })

@app.route("/api/admin/requests", methods=["GET"])
def get_admin_requests():
    """Returns recent requests with routing and cost details."""
    limit = int(request.args.get("limit", 15))
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT r.*, s.name as school_name
    FROM generation_requests r
    LEFT JOIN schools s ON r.school_id = s.id
    ORDER BY r.id DESC
    LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({"requests": rows})

@app.route("/api/policies", methods=["GET", "POST"])
def manage_policies():
    """Read or update district spending policies."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.get_json() or {}
        for k, v in data.items():
            cursor.execute("INSERT OR REPLACE INTO district_policies (key, value) VALUES (?, ?)", (k, json.dumps(v)))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "District policies updated successfully."})

    cursor.execute("SELECT key, value FROM district_policies")
    rows = cursor.fetchall()
    conn.close()

    policies = {}
    for r in rows:
        try:
            policies[r["key"]] = json.loads(r["value"])
        except:
            policies[r["key"]] = r["value"]

    return jsonify({"policies": policies})

@app.route("/api/flag-request", methods=["POST"])
def flag_request():
    """Teacher quality review feedback."""
    data = request.get_json() or {}
    req_id = data.get("request_id")
    feedback = data.get("feedback", "")
    is_positive = data.get("is_positive", True)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE generation_requests
    SET flagged_by_teacher = ?, flag_feedback = ?
    WHERE request_id = ?
    """, (0 if is_positive else 1, feedback, req_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Teacher feedback recorded."})

@app.route("/api/benchmark-sample", methods=["POST"])
def run_benchmark_sample():
    """
    Evaluates a sample batch of standard educational prompts through both
    the Naive Baseline system (always calls ₹6.00 high-res model) and PixelWise AI.
    """
    benchmarks = [
        {
            "prompt": "Create an elephant colouring worksheet for a seven-year-old with thick outlines",
            "material_type": "worksheet",
            "grade_level": "kindergarten"
        },
        {
            "prompt": "Monarch butterfly outline coloring page with symmetrical wings",
            "material_type": "worksheet",
            "grade_level": "primary"
        },
        {
            "prompt": "Water cycle educational diagram showing evaporation and condensation",
            "material_type": "flashcard",
            "grade_level": "primary"
        },
        {
            "prompt": "Solar system planets educational diagram with labeled orbits",
            "material_type": "flashcard",
            "grade_level": "middle"
        },
        {
            "prompt": "District Annual Report high-resolution commemorative poster",
            "material_type": "poster",
            "grade_level": "high"
        }
    ]

    results = []
    total_baseline = 0.0
    total_pixelwise = 0.0

    for item in benchmarks:
        prompt = item["prompt"]
        mat = item["material_type"]
        grd = item["grade_level"]

        # Run PixelWise
        res = PixelWiseOrchestrator.execute_request(
            school_id="SCH-001",
            teacher_name="Benchmark Evaluator",
            prompt=prompt,
            material_type=mat,
            grade_level=grd
        )

        b_cost = BASELINE_COST_PER_IMAGE
        p_cost = res["actual_cost"]
        saved = round(b_cost - p_cost, 2)
        total_baseline += b_cost
        total_pixelwise += p_cost

        results.append({
            "prompt": prompt,
            "material_type": mat,
            "chosen_tier": res["routing"]["chosen_tier"],
            "tier_name": res["routing"]["tier_name"],
            "final_status": res["final_status"],
            "baseline_cost": b_cost,
            "pixelwise_cost": p_cost,
            "cost_saved": saved,
            "savings_pct": round((saved / b_cost) * 100, 1),
            "image_url": res["image_url"],
            "has_svg": res["svg_content"] is not None
        })

    total_saved = round(total_baseline - total_pixelwise, 2)
    overall_savings_pct = round((total_saved / total_baseline) * 100, 1)

    return jsonify({
        "benchmark_results": results,
        "total_baseline": total_baseline,
        "total_pixelwise": round(total_pixelwise, 2),
        "total_saved": total_saved,
        "overall_savings_pct": overall_savings_pct
    })

@app.route("/api/library/assets", methods=["GET"])
def get_library_assets():
    """Returns curated and cached educational assets for the District Library Explorer."""
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM library_assets WHERE 1=1"
    params = []
    if category and category != "ALL":
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (title LIKE ? OR tags LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY usage_count DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    assets = []
    for r in rows:
        d = dict(r)
        # Resolve SVG content if it references template key
        if d["content"] in ZeroAILibrary.SVG_TEMPLATES:
            d["svg_markup"] = ZeroAILibrary.SVG_TEMPLATES[d["content"]]
        elif d["content"] == "ELEPHANT_SVG":
            d["svg_markup"] = ZeroAILibrary.SVG_TEMPLATES["elephant"]
        elif d["content"] == "BUTTERFLY_SVG":
            d["svg_markup"] = ZeroAILibrary.SVG_TEMPLATES["butterfly"]
        elif d["content"] == "WATER_CYCLE_SVG":
            d["svg_markup"] = ZeroAILibrary.SVG_TEMPLATES["water cycle"]
        elif d["content"] == "SOLAR_SYSTEM_SVG":
            d["svg_markup"] = ZeroAILibrary.SVG_TEMPLATES["solar system"]
        elif d["content"] == "GEOMETRIC_SHAPES_SVG":
            d["svg_markup"] = ZeroAILibrary.SVG_TEMPLATES["shapes"]
        elif d["content"] == "LION_SVG":
            d["svg_markup"] = ZeroAILibrary.SVG_TEMPLATES["lion"]
        elif d["asset_type"] == "svg" and "<svg" in d["content"]:
            d["svg_markup"] = d["content"]
        else:
            d["svg_markup"] = None
        assets.append(d)

    return jsonify({"assets": assets, "total": len(assets)})

@app.route("/api/admin/export-csv", methods=["GET"])
def export_admin_csv():
    """Generates an official district cloud expenditure CSV report across 300 schools."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schools ORDER BY id ASC")
    schools = cursor.fetchall()
    conn.close()

    lines = ["School ID,School Name,Zone,Monthly Budget (INR),Current Spend (INR),Utilization Pct,Total Requests,Zero-AI Reused Count,Compliance Status\n"]
    for s in schools:
        util = min(100.0, round((s["current_spend"] / s["monthly_budget"]) * 100, 1))
        status = "COMPLIANT"
        if util >= 95:
            status = "BUDGET_EXCEEDED"
        elif util >= 80:
            status = "ALERT_NEAR_LIMIT"
        clean_name = s["name"].replace(",", " ")
        lines.append(f"{s['id']},{clean_name},{s['zone']},{s['monthly_budget']:.2f},{s['current_spend']:.2f},{util}%,{s['total_requests']},{s['reused_count']},{status}\n")

    csv_data = "".join(lines)
    from flask import Response
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=pixelwise_district_spend_report.csv"}
    )

@app.route("/api/guided-scenarios", methods=["GET"])
def get_guided_scenarios():
    """Returns curated demonstration presets for evaluators and administrators."""
    scenarios = [
        {
            "id": "scenario-1",
            "title": "Scenario 1: Zero-AI Vector Synthesis (Worksheet)",
            "description": "Teacher requests an elephant coloring worksheet for class 1. PixelWise AI recognizes line art requirements and synthesizes clean SVG vector output at ₹0.05 instead of calling expensive diffusion (₹6.00).",
            "prompt": "Create an elephant colouring worksheet for a seven-year-old with thick outlines",
            "material_type": "worksheet",
            "grade_level": "kindergarten",
            "school_id": "SCH-001",
            "force_defect": False,
            "expected_outcome": "Fulfilled via Zero-AI SVG Vector Synthesizer at ₹0.05 (99.2% cost reduction)."
        },
        {
            "id": "scenario-2",
            "title": "Scenario 2: 300-School Shared Library Reuse",
            "description": "Teacher requests a monarch butterfly coloring page. PixelWise AI searches the district repository, finds an approved asset from another school, and serves it at ₹0.00.",
            "prompt": "Monarch butterfly outline coloring page with symmetrical wings",
            "material_type": "worksheet",
            "grade_level": "primary",
            "school_id": "SCH-002",
            "force_defect": False,
            "expected_outcome": "100% cost elimination via shared district cache reuse (₹0.00)."
        },
        {
            "id": "scenario-3",
            "title": "Scenario 3: Failure-Aware PIL Auto-Correction",
            "description": "A low-cost standard AI model generates a puppy outline with unwanted muddy background shading. QualityVerifier detects the defect. FailureEscalationManager applies adaptive PIL binarization for ₹0.02, delivering clean white outlines and saving a ₹5.50 regeneration.",
            "prompt": "Cartoon puppy dog line art for class 1 coloring activity",
            "material_type": "worksheet",
            "grade_level": "primary",
            "school_id": "SCH-003",
            "force_defect": True,
            "expected_outcome": "Defect caught and auto-corrected via PIL binarization at ₹0.02."
        },
        {
            "id": "scenario-4",
            "title": "Scenario 4: Mathematical E(C) Direct Escalation",
            "description": "Teacher requests an intricate District Annual Report poster (complexity 5). The router calculates that a standard model has a 75% failure rate, making advanced generation cheaper overall in expected total cost.",
            "prompt": "District Annual Report high-resolution commemorative scientific achievements poster",
            "material_type": "poster",
            "grade_level": "high",
            "school_id": "SCH-004",
            "force_defect": False,
            "expected_outcome": "Advanced PixelPro-HD allocated directly based on E(C) optimization."
        },
        {
            "id": "scenario-5",
            "title": "Scenario 5: School Budget Cap Enforcement",
            "description": "A school near its 80% monthly budget threshold requests an illustration. PixelWise AI strictly enforces eco resource allocation to guarantee policy compliance.",
            "prompt": "Friendly science robot illustration for student newsletter",
            "material_type": "flashcard",
            "grade_level": "middle",
            "school_id": "SCH-005",
            "force_defect": False,
            "expected_outcome": "Enforces PixelEco-1 due to school budget telemetry alert."
        }
    ]
    return jsonify({"scenarios": scenarios})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
