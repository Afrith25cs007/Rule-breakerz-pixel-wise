import sqlite3
import json
import os
import random
import datetime
from config import DATABASE_PATH, DEFAULT_POLICIES, TOTAL_SCHOOLS_COUNT, DISTRICT_ZONES, BASELINE_COST_PER_IMAGE

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Schools table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schools (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        zone TEXT NOT NULL,
        monthly_budget REAL NOT NULL,
        current_spend REAL NOT NULL DEFAULT 0.0,
        total_requests INTEGER NOT NULL DEFAULT 0,
        reused_count INTEGER NOT NULL DEFAULT 0
    )
    """)

    # District Policies
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS district_policies (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Shared Library Assets (Zero-AI & Approved Cache)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS library_assets (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        grade_level TEXT NOT NULL,
        tags TEXT NOT NULL,
        asset_type TEXT NOT NULL, -- 'svg' or 'image'
        content TEXT NOT NULL, -- SVG code or image relative path
        thumbnail_url TEXT,
        usage_count INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Generation Requests
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generation_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE NOT NULL,
        school_id TEXT NOT NULL,
        teacher_name TEXT NOT NULL,
        prompt TEXT NOT NULL,
        material_type TEXT NOT NULL,
        grade_level TEXT NOT NULL,
        visual_style TEXT NOT NULL,
        complexity_score INTEGER NOT NULL,
        chosen_tier TEXT NOT NULL,
        routing_details TEXT NOT NULL, -- JSON
        attempts_log TEXT NOT NULL, -- JSON array
        final_status TEXT NOT NULL, -- DELIVERED_PASS, DELIVERED_AUTOCORRECTED, DELIVERED_REUSED, FAILED_POLICY_LIMIT
        image_url TEXT,
        svg_content TEXT,
        actual_cost REAL NOT NULL,
        baseline_cost REAL NOT NULL,
        cost_saved REAL NOT NULL,
        verified_pass INTEGER NOT NULL DEFAULT 1,
        flagged_by_teacher INTEGER DEFAULT 0,
        flag_feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (school_id) REFERENCES schools(id)
    )
    """)

    conn.commit()

    # Check if schools table is populated
    cursor.execute("SELECT COUNT(*) FROM schools")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_data(conn)

    conn.close()

def seed_data(conn):
    cursor = conn.cursor()

    # Seed Default Policies
    for k, v in DEFAULT_POLICIES.items():
        cursor.execute("INSERT OR REPLACE INTO district_policies (key, value) VALUES (?, ?)", (k, json.dumps(v)))

    # Seed 300 Schools
    school_prefixes = ["St. Mary's", "Lincoln", "Oakridge", "Valley View", "Beacon", "Greenwood", "Riverside", "Hilltop", "Sunflower", "Maple Leaf", "Cambridge", "Evergreen", "Harmony", "Pioneer", "Horizon", "Crestview", "Apex", "Bright Horizons", "Cedar Grove", "Summit"]
    school_types = ["Primary School", "Elementary School", "Middle School", "Model High School", "Public School", "Vidyalaya", "Grammar School"]

    schools = []
    for i in range(1, TOTAL_SCHOOLS_COUNT + 1):
        school_id = f"SCH-{i:03d}"
        prefix = school_prefixes[(i - 1) % len(school_prefixes)]
        stype = school_types[(i * 3) % len(school_types)]
        zone = DISTRICT_ZONES[(i - 1) % len(DISTRICT_ZONES)]
        name = f"{prefix} {stype} #{((i-1)//20) + 1}"
        budget = 500.00
        schools.append((school_id, name, zone, budget, 0.0, 0, 0))

    cursor.executemany("""
    INSERT INTO schools (id, name, zone, monthly_budget, current_spend, total_requests, reused_count)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, schools)

    # Seed Curated Library Assets
    curated_assets = [
        ("AST-001", "Elephant Outline Coloring Worksheet", "worksheet", "kindergarten", "elephant,animal,outline,coloring,black and white,simple,safari", "svg", "ELEPHANT_SVG", None, 45),
        ("AST-002", "Monarch Butterfly Outline Coloring Page", "worksheet", "primary", "butterfly,insect,outline,coloring,wings,line art,nature", "svg", "BUTTERFLY_SVG", None, 58),
        ("AST-003", "Water Cycle Labeled Diagram", "flashcard", "primary", "water cycle,evaporation,condensation,precipitation,clouds,rain,science,diagram", "svg", "WATER_CYCLE_SVG", None, 38),
        ("AST-004", "Solar System Planetary Chart", "poster", "middle", "solar system,planets,sun,orbit,space,astronomy,earth,mars,jupiter", "svg", "SOLAR_SYSTEM_SVG", None, 31),
        ("AST-005", "Basic Geometric Tracing Shapes", "worksheet", "kindergarten", "shapes,circle,square,triangle,star,tracing,geometry,math", "svg", "GEOMETRIC_SHAPES_SVG", None, 64),
        ("AST-006", "Friendly Lion Head Coloring Sheet", "worksheet", "primary", "lion,animal,mane,coloring,safari,wildlife,outline", "svg", "LION_SVG", None, 29),
        ("AST-007", "Plant Cell Anatomy Flashcard", "flashcard", "middle", "cell,plant cell,chloroplast,nucleus,biology,science,vacuole", "svg", "PLANT_CELL_SVG", None, 24),
        ("AST-008", "Fraction Pie Chart Visualizer", "flashcard", "primary", "fraction,pie chart,math,halves,quarters,thirds,division", "svg", "FRACTION_SVG", None, 35)
    ]

    for ast in curated_assets:
        cursor.execute("""
        INSERT INTO library_assets (id, title, category, grade_level, tags, asset_type, content, thumbnail_url, usage_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ast)

    # Seed Realistic Historical Generation Requests (~140 historical records over the past 30 days)
    sample_teachers = ["Mrs. Sharma", "Mr. Davis", "Ms. Ananya", "Mr. Thompson", "Dr. Rao", "Mrs. Jennifer", "Mr. Patel", "Ms. Garcia", "Mrs. Wilson", "Mr. Kabir"]
    sample_prompts = [
        ("Create an elephant colouring worksheet for a seven-year-old with thick outlines", "worksheet", "kindergarten", "LINE_ART_COLORING", 1, "TIER_1_ZERO_AI_SVG", 0.05, "DELIVERED_PASS"),
        ("Monarch butterfly coloring page with symmetrical wings and clear outlines", "worksheet", "primary", "LINE_ART_COLORING", 1, "TIER_0_REUSE", 0.00, "DELIVERED_REUSED"),
        ("Water cycle educational diagram showing evaporation, condensation, precipitation", "flashcard", "primary", "DIAGRAM", 2, "TIER_1_ZERO_AI_SVG", 0.05, "DELIVERED_PASS"),
        ("Basic geometric shapes tracing exercise for preschool class", "worksheet", "kindergarten", "LINE_ART_COLORING", 1, "TIER_0_REUSE", 0.00, "DELIVERED_REUSED"),
        ("Friendly cartoon robot playing soccer illustration for student newsletter", "flashcard", "primary", "FULL_COLOR_ILLUSTRATION", 3, "TIER_2_ECO_AI", 2.00, "DELIVERED_PASS"),
        ("District Annual Science Fair celebratory presentation poster high resolution", "poster", "high", "HIGH_RES_POSTER", 5, "TIER_3_ADVANCED_AI", 5.85, "DELIVERED_PASS"),
        ("Solar system planets in order from the sun educational visual", "poster", "middle", "DIAGRAM", 3, "TIER_1_ZERO_AI_SVG", 0.05, "DELIVERED_PASS"),
        ("Simple puppy dog line art for class 1 coloring without background shading", "worksheet", "primary", "LINE_ART_COLORING", 2, "TIER_2_ECO_AI", 2.02, "DELIVERED_AUTOCORRECTED"),
        ("Ancient Indus Valley Civilization historical market detailed scene", "poster", "middle", "HIGH_RES_POSTER", 4, "TIER_3_ADVANCED_AI", 5.85, "DELIVERED_PASS"),
        ("Plant cell organelles labeled biology flashcard for class 7", "flashcard", "middle", "DIAGRAM", 3, "TIER_0_REUSE", 0.00, "DELIVERED_REUSED"),
        ("Math fraction pie chart showing 1/2, 1/4 and 3/4 visually", "flashcard", "primary", "DIAGRAM", 2, "TIER_0_REUSE", 0.00, "DELIVERED_REUSED"),
        ("Lion face line drawing coloring sheet with no gray shading", "worksheet", "kindergarten", "LINE_ART_COLORING", 1, "TIER_0_REUSE", 0.00, "DELIVERED_REUSED"),
        ("Detailed environmental conservation poster depicting renewable energy and clean cities", "poster", "high", "HIGH_RES_POSTER", 5, "TIER_3_ADVANCED_AI", 5.85, "DELIVERED_PASS"),
        ("Apple and banana fruit flashcard with bold outlines and clear colors", "flashcard", "kindergarten", "FULL_COLOR_ILLUSTRATION", 2, "TIER_2_ECO_AI", 2.00, "DELIVERED_PASS"),
        ("Dinosaur T-rex black and white outline for coloring activity", "worksheet", "primary", "LINE_ART_COLORING", 2, "TIER_2_ECO_AI", 2.02, "DELIVERED_AUTOCORRECTED")
    ]

    now = datetime.datetime.now()
    historical_rows = []
    
    # Generate 140 historical requests across random schools
    for req_idx in range(140):
        prompt_data = random.choice(sample_prompts)
        school_num = random.randint(1, 45) # concentrate requests on first 45 schools for realism
        school_id = f"SCH-{school_num:03d}"
        teacher = random.choice(sample_teachers)
        req_id = f"REQ-HIST-{1000 + req_idx}"
        
        # Random date in last 30 days
        days_ago = random.randint(0, 29)
        hours_ago = random.randint(0, 23)
        req_time = (now - datetime.timedelta(days=days_ago, hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")

        prompt, mat_type, grade, vstyle, comp, tier, actual_c, status = prompt_data
        
        # Slight cost jitter if Eco AI
        if tier == "TIER_2_ECO_AI" and status == "DELIVERED_PASS":
            actual_c = 2.00
        elif tier == "TIER_2_ECO_AI" and status == "DELIVERED_AUTOCORRECTED":
            actual_c = 2.02 # 1.80 + 0.20 + 0.02

        baseline_c = BASELINE_COST_PER_IMAGE
        cost_saved = round(baseline_c - actual_c, 2)

        routing_json = json.dumps({
            "chosen_tier": tier,
            "rationale": f"Routed based on expected total cost E(C) minimization for {mat_type}.",
            "expected_cost": actual_c
        })

        attempts = [{
            "attempt": 1,
            "tier": tier,
            "action": "Initial Generation",
            "cost": actual_c,
            "result": "PASS" if status != "DELIVERED_AUTOCORRECTED" else "AUTOCORRECTED"
        }]

        historical_rows.append((
            req_id, school_id, teacher, prompt, mat_type, grade, vstyle, comp,
            tier, routing_json, json.dumps(attempts), status,
            "/static/placeholders/sample.png", None, actual_c, baseline_c, cost_saved,
            1, 0, "", req_time
        ))

    cursor.executemany("""
    INSERT INTO generation_requests (
        request_id, school_id, teacher_name, prompt, material_type, grade_level,
        visual_style, complexity_score, chosen_tier, routing_details, attempts_log,
        final_status, image_url, svg_content, actual_cost, baseline_cost,
        cost_saved, verified_pass, flagged_by_teacher, flag_feedback, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, historical_rows)

    # Update schools spend and count aggregates
    cursor.execute("""
    SELECT school_id, COUNT(*) as cnt, SUM(actual_cost) as tot_spend, 
           SUM(CASE WHEN chosen_tier IN ('TIER_0_REUSE', 'TIER_1_ZERO_AI_SVG') THEN 1 ELSE 0 END) as reused
    FROM generation_requests
    GROUP BY school_id
    """)
    aggregates = cursor.fetchall()
    for row in aggregates:
        cursor.execute("""
        UPDATE schools
        SET total_requests = ?, current_spend = ?, reused_count = ?
        WHERE id = ?
        """, (row["cnt"], round(row["tot_spend"], 2), row["reused"], row["school_id"]))

    conn.commit()
