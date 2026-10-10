# District and Model Configuration for PixelWise AI
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "generated")
DATABASE_PATH = os.path.join(BASE_DIR, "pixelwise.db")

# Currency Symbol
CURRENCY = "₹"

# Baseline system cost per image (Standard naive approach: always uses premium model settings)
BASELINE_COST_PER_IMAGE = 6.00

# Available Generation Tiers and Providers
TIERS = {
    "TIER_0_REUSE": {
        "id": "TIER_0_REUSE",
        "name": "Shared Library Asset Reuse",
        "provider": "PixelWise Semantic Cache",
        "category": "Zero-AI Cache",
        "cost_gen": 0.00,
        "cost_verif": 0.00,
        "typical_pass_rate": 1.00,
        "resolution": "Vector / Original HD",
        "description": "Reuses verified, approved educational asset from the district library at ₹0 cost."
    },
    "TIER_1_ZERO_AI_SVG": {
        "id": "TIER_1_ZERO_AI_SVG",
        "name": "Zero-AI SVG Vector Engine",
        "provider": "PixelWise Vector Synthesizer",
        "category": "Procedural SVG",
        "cost_gen": 0.00,
        "cost_verif": 0.05,
        "typical_pass_rate": 0.98,
        "resolution": "Infinite Vector (Scalable)",
        "description": "Generates crisp black-and-white coloring line art or geometric diagrams procedurally without generative AI."
    },
    "TIER_2_ECO_AI": {
        "id": "TIER_2_ECO_AI",
        "name": "PixelEco-1 (Standard AI)",
        "provider": "Standard Diffusion / Fast Model",
        "category": "Standard AI",
        "cost_gen": 1.80,
        "cost_verif": 0.20,
        "typical_pass_rate": 0.74,
        "fallback_tier": "TIER_3_ADVANCED_AI",
        "fallback_cost": 5.50,
        "resolution": "512x512 / 768x768",
        "description": "Cost-effective AI generation for ordinary illustrations and non-critical assets."
    },
    "TIER_3_ADVANCED_AI": {
        "id": "TIER_3_ADVANCED_AI",
        "name": "PixelPro-HD (Advanced AI)",
        "provider": "High-Fidelity Capable Diffusion",
        "category": "Advanced AI",
        "cost_gen": 5.50,
        "cost_verif": 0.35,
        "typical_pass_rate": 0.95,
        "fallback_tier": "TIER_3_ADVANCED_AI",
        "fallback_cost": 5.50,
        "resolution": "1024x1024 High-Res",
        "description": "High-capability model for intricate historical scenes, full-colour posters, and complex posters."
    }
}

# Image Processing & Auto-Correction Costs
AUTOCORRECT_COST = 0.02

# Default District Policies
DEFAULT_POLICIES = {
    "max_retries": 2,
    "max_request_budget": 8.00,
    "autocorrect_enabled": True,
    "prefer_zero_ai": True,
    "school_monthly_budget": 500.00,
    "budget_alert_threshold": 0.80, # 80% of budget triggers alert
    "enforce_worksheet_eco": True
}

# 5 District Zones serving 300 schools
DISTRICT_ZONES = ["North Zone", "South Zone", "East Zone", "West Zone", "Central Zone"]
TOTAL_SCHOOLS_COUNT = 300
