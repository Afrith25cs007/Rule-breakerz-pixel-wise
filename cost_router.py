from config import TIERS, AUTOCORRECT_COST

class CostRouter:
    """
    Module 2: Cost-Aware Generation Router
    Calculates the Expected Total Cost E(C) across all available options:
      E(C) = C_generation + C_verification + E(C_correction/retry)
    Selects the most cost-effective method meeting quality and policy constraints.
    """

    @classmethod
    def calculate_expected_costs(cls, classification: dict, autocorrect_enabled: bool = True) -> dict:
        complexity = classification.get("complexity_score", 3)
        zero_ai_eligible = classification.get("zero_ai_eligible", False)
        visual_style = classification.get("visual_style", "FULL_COLOR_ILLUSTRATION")

        options = {}

        # 1. Tier 0: Reuse
        options["TIER_0_REUSE"] = {
            "tier_id": "TIER_0_REUSE",
            "name": TIERS["TIER_0_REUSE"]["name"],
            "c_gen": 0.00,
            "c_verif": 0.00,
            "p_fail": 0.00,
            "expected_retry_cost": 0.00,
            "expected_total_cost": 0.00,
            "pass_rate_pct": 100,
            "viable": True, # set dynamically based on cache hit
            "resolution": TIERS["TIER_0_REUSE"]["resolution"],
            "formula_display": "₹0.00 + ₹0.00 + ₹0.00 = ₹0.00"
        }

        # 2. Tier 1: Zero-AI SVG Vector Engine
        p_fail_svg = 0.02
        c_gen_svg = TIERS["TIER_1_ZERO_AI_SVG"]["cost_gen"]
        c_verif_svg = TIERS["TIER_1_ZERO_AI_SVG"]["cost_verif"]
        retry_svg = round(p_fail_svg * 2.00, 2)
        e_c_svg = round(c_gen_svg + c_verif_svg + retry_svg, 2)

        options["TIER_1_ZERO_AI_SVG"] = {
            "tier_id": "TIER_1_ZERO_AI_SVG",
            "name": TIERS["TIER_1_ZERO_AI_SVG"]["name"],
            "c_gen": c_gen_svg,
            "c_verif": c_verif_svg,
            "p_fail": p_fail_svg,
            "expected_retry_cost": retry_svg,
            "expected_total_cost": e_c_svg,
            "pass_rate_pct": 98,
            "viable": zero_ai_eligible,
            "resolution": TIERS["TIER_1_ZERO_AI_SVG"]["resolution"],
            "formula_display": f"₹{c_gen_svg:.2f} + ₹{c_verif_svg:.2f} + (0.02 × ₹2.00) = ₹{e_c_svg:.2f}"
        }

        # 3. Tier 2: Eco AI (PixelEco-1)
        # Failure probability depends on complexity
        if complexity <= 2:
            p_fail_eco = 0.22 # simple images
        elif complexity == 3:
            p_fail_eco = 0.30 # average illustrations
        elif complexity == 4:
            p_fail_eco = 0.55 # detailed scenes
        else:
            p_fail_eco = 0.75 # intricate posters / historical scenes

        c_gen_eco = TIERS["TIER_2_ECO_AI"]["cost_gen"]
        c_verif_eco = TIERS["TIER_2_ECO_AI"]["cost_verif"]
        fallback_eco = TIERS["TIER_2_ECO_AI"]["fallback_cost"] + TIERS["TIER_3_ADVANCED_AI"]["cost_verif"]

        if autocorrect_enabled and visual_style == "LINE_ART_COLORING":
            # 60% of failures are gray shading cleanable via PIL thresholding at ₹0.02
            p_autocorrect = p_fail_eco * 0.60
            p_hard_escalate = p_fail_eco * 0.40
            retry_eco = round((p_autocorrect * AUTOCORRECT_COST) + (p_hard_escalate * fallback_eco), 2)
            formula_eco_str = f"₹{c_gen_eco:.2f} + ₹{c_verif_eco:.2f} + [({p_autocorrect:.2f} × ₹{AUTOCORRECT_COST:.2f}) + ({p_hard_escalate:.2f} × ₹{fallback_eco:.2f})]"
        else:
            retry_eco = round(p_fail_eco * fallback_eco, 2)
            formula_eco_str = f"₹{c_gen_eco:.2f} + ₹{c_verif_eco:.2f} + ({p_fail_eco:.2f} × ₹{fallback_eco:.2f})"

        e_c_eco = round(c_gen_eco + c_verif_eco + retry_eco, 2)

        options["TIER_2_ECO_AI"] = {
            "tier_id": "TIER_2_ECO_AI",
            "name": TIERS["TIER_2_ECO_AI"]["name"],
            "c_gen": c_gen_eco,
            "c_verif": c_verif_eco,
            "p_fail": p_fail_eco,
            "expected_retry_cost": retry_eco,
            "expected_total_cost": e_c_eco,
            "pass_rate_pct": int((1 - p_fail_eco) * 100),
            "viable": complexity <= 4,
            "resolution": TIERS["TIER_2_ECO_AI"]["resolution"],
            "formula_display": f"{formula_eco_str} = ₹{e_c_eco:.2f}"
        }

        # 4. Tier 3: Advanced AI (PixelPro-HD)
        p_fail_adv = 0.05 if complexity <= 4 else 0.08
        c_gen_adv = TIERS["TIER_3_ADVANCED_AI"]["cost_gen"]
        c_verif_adv = TIERS["TIER_3_ADVANCED_AI"]["cost_verif"]
        fallback_adv = c_gen_adv + c_verif_adv
        retry_adv = round(p_fail_adv * fallback_adv, 2)
        e_c_adv = round(c_gen_adv + c_verif_adv + retry_adv, 2)

        options["TIER_3_ADVANCED_AI"] = {
            "tier_id": "TIER_3_ADVANCED_AI",
            "name": TIERS["TIER_3_ADVANCED_AI"]["name"],
            "c_gen": c_gen_adv,
            "c_verif": c_verif_adv,
            "p_fail": p_fail_adv,
            "expected_retry_cost": retry_adv,
            "expected_total_cost": e_c_adv,
            "pass_rate_pct": int((1 - p_fail_adv) * 100),
            "viable": True,
            "resolution": TIERS["TIER_3_ADVANCED_AI"]["resolution"],
            "formula_display": f"₹{c_gen_adv:.2f} + ₹{c_verif_adv:.2f} + ({p_fail_adv:.2f} × ₹{fallback_adv:.2f}) = ₹{e_c_adv:.2f}"
        }

        return options

    @classmethod
    def route_request(cls, classification: dict, reuse_result: dict, policies: dict, school_budget_status: dict) -> dict:
        """
        Main routing decision pipeline.
        Considers reuse cache, procedural templates, expected total cost E(C), and district budget policies.
        """
        autocorrect_enabled = policies.get("autocorrect_enabled", True)
        options = cls.calculate_expected_costs(classification, autocorrect_enabled=autocorrect_enabled)
        
        # 1. First priority: Reusable asset hit
        if reuse_result.get("found"):
            chosen_tier = "TIER_0_REUSE"
            rationale = f"Matched approved district asset '{reuse_result['title']}' (Usage: {reuse_result['usage_count']} schools). Zero generation cost."
            return {
                "chosen_tier": chosen_tier,
                "tier_name": TIERS[chosen_tier]["name"],
                "rationale": rationale,
                "expected_total_cost": 0.00,
                "options": options,
                "is_reuse": True
            }

        # 2. Second priority: Zero-AI Vector Synthesis
        if classification.get("zero_ai_eligible") and options["TIER_1_ZERO_AI_SVG"]["viable"]:
            chosen_tier = "TIER_1_ZERO_AI_SVG"
            rationale = "Request satisfies zero-AI vector template constraints. Produces clean printable vector line art at ₹0 generation cost."
            return {
                "chosen_tier": chosen_tier,
                "tier_name": TIERS[chosen_tier]["name"],
                "rationale": rationale,
                "expected_total_cost": options[chosen_tier]["expected_total_cost"],
                "options": options,
                "is_reuse": False
            }

        # 3. Model selection based on expected total cost E(C) and complexity
        e_c_eco = options["TIER_2_ECO_AI"]["expected_total_cost"]
        e_c_adv = options["TIER_3_ADVANCED_AI"]["expected_total_cost"]
        complexity = classification.get("complexity_score", 3)

        # If complexity is very high (e.g. 5, Annual report / fine-art poster),
        # Eco AI failure rate makes E(C) worse or quality unviable.
        if complexity >= 5 or classification.get("visual_style") == "HIGH_RES_POSTER" and complexity >= 4:
            chosen_tier = "TIER_3_ADVANCED_AI"
            rationale = f"High visual complexity (score {complexity}/5) requires PixelPro-HD capable model. Lower tier has 75% failure probability, making advanced tier cheaper in expected total cost."
        elif school_budget_status.get("near_limit", False):
            chosen_tier = "TIER_2_ECO_AI"
            rationale = "School monthly spending near alert limit (>80%). Strict Eco AI allocation enforced per district budget policy."
        elif e_c_eco < e_c_adv and options["TIER_2_ECO_AI"]["viable"]:
            chosen_tier = "TIER_2_ECO_AI"
            rationale = f"PixelEco-1 delivers lowest expected total cost E(C) = ₹{e_c_eco:.2f} (vs ₹{e_c_adv:.2f} for Advanced AI) including potential verification and retry charges."
        else:
            chosen_tier = "TIER_3_ADVANCED_AI"
            rationale = f"PixelPro-HD selected: Expected cost ₹{e_c_adv:.2f} optimal for this request type."

        return {
            "chosen_tier": chosen_tier,
            "tier_name": TIERS[chosen_tier]["name"],
            "rationale": rationale,
            "expected_total_cost": options[chosen_tier]["expected_total_cost"],
            "options": options,
            "is_reuse": False
        }
