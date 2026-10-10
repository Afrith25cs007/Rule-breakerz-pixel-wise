import uuid
import json
import os
import sqlite3
from config import DATABASE_PATH, BASELINE_COST_PER_IMAGE, DEFAULT_POLICIES, TIERS, AUTOCORRECT_COST
from modules.classifier import RequestClassifier
from modules.zero_ai_library import ZeroAILibrary
from modules.cost_router import CostRouter
from modules.verifier import QualityVerifier
from modules.escalation import FailureEscalationManager
from modules.generator import ImageGeneratorService

class PixelWiseOrchestrator:
    """
    Central Decision Pipeline:
    Coordinates Module 1 (Classifier), Module 2 (Router), Module 3 (Reuse/Zero-AI),
    Module 4 (Verifier), and Module 5 (Escalation) to produce an acceptable educational
    image at the minimum expected total cost.
    """

    @classmethod
    def get_policies(cls) -> dict:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM district_policies")
        rows = cursor.fetchall()
        conn.close()

        policies = dict(DEFAULT_POLICIES)
        for r in rows:
            try:
                policies[r["key"]] = json.loads(r["value"])
            except:
                pass
        return policies

    @classmethod
    def get_school(cls, school_id: str) -> dict:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schools WHERE id = ?", (school_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {
            "id": school_id,
            "name": f"School {school_id}",
            "monthly_budget": 500.0,
            "current_spend": 0.0,
            "total_requests": 0,
            "reused_count": 0
        }

    @classmethod
    def execute_request(cls, school_id: str, teacher_name: str, prompt: str,
                        material_type: str = "worksheet", grade_level: str = "primary",
                        force_defect: bool = False) -> dict:
        request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        policies = cls.get_policies()
        school_info = cls.get_school(school_id)

        budget_limit = school_info.get("monthly_budget", 500.0)
        curr_spend = school_info.get("current_spend", 0.0)
        near_limit = (curr_spend / budget_limit) >= policies.get("budget_alert_threshold", 0.8)
        school_budget_status = {
            "current_spend": curr_spend,
            "monthly_budget": budget_limit,
            "near_limit": near_limit
        }

        # Step 1: Intelligent Request Classification (Module 1)
        classification = RequestClassifier.classify(prompt, material_type, grade_level)

        # Step 2: Shared Library Reuse Check (Module 3)
        reuse_result = ZeroAILibrary.check_reuse_library(prompt, classification["detected_tags"], material_type)

        # Step 3: Cost-Aware Generation Router (Module 2)
        routing = CostRouter.route_request(classification, reuse_result, policies, school_budget_status)
        chosen_tier = routing["chosen_tier"]

        attempts_log = []
        actual_total_cost = 0.0
        final_status = "PENDING"
        image_url = None
        svg_content = None

        # Execution Branch A: Shared Library Reuse (Tier 0)
        if chosen_tier == "TIER_0_REUSE":
            ZeroAILibrary.increment_asset_usage(reuse_result["asset_id"])
            actual_total_cost = 0.00
            final_status = "DELIVERED_REUSED"
            if reuse_result["asset_type"] == "svg":
                svg_content = reuse_result["content"]
            else:
                image_url = reuse_result["content"]

            attempts_log.append({
                "attempt": 1,
                "tier": "TIER_0_REUSE",
                "tier_name": TIERS["TIER_0_REUSE"]["name"],
                "action": "Cache Hit / Library Reuse",
                "gen_cost": 0.00,
                "verif_cost": 0.00,
                "total_attempt_cost": 0.00,
                "verification_result": {
                    "passed": True,
                    "details": "Asset pre-verified and approved by district curriculum committee."
                },
                "status": "PASS"
            })

        # Execution Branch B: Zero-AI Vector Synthesis (Tier 1)
        elif chosen_tier == "TIER_1_ZERO_AI_SVG":
            svg_res = ZeroAILibrary.generate_procedural_svg(prompt, classification["detected_tags"], material_type)
            if svg_res["success"]:
                svg_content = svg_res["svg_content"]
                # Verify SVG
                verif = QualityVerifier.verify_svg(svg_content)
                actual_total_cost = verif["verification_cost"]
                final_status = "DELIVERED_PASS"

                attempts_log.append({
                    "attempt": 1,
                    "tier": "TIER_1_ZERO_AI_SVG",
                    "tier_name": TIERS["TIER_1_ZERO_AI_SVG"]["name"],
                    "action": "Zero-AI Vector Synthesis",
                    "gen_cost": 0.00,
                    "verif_cost": verif["verification_cost"],
                    "total_attempt_cost": actual_total_cost,
                    "verification_result": verif,
                    "status": "PASS"
                })
            else:
                # If SVG template matching failed, gracefully fallback to Eco AI
                chosen_tier = "TIER_2_ECO_AI"

        # Execution Branch C: AI Generation (Tier 2 or Tier 3)
        if chosen_tier in ["TIER_2_ECO_AI", "TIER_3_ADVANCED_AI"]:
            current_tier = chosen_tier
            current_prompt = prompt
            attempt_num = 1
            resolved = False

            while attempt_num <= policies.get("max_retries", 2) and not resolved:
                gen_cost = TIERS[current_tier]["cost_gen"]
                actual_total_cost += gen_cost

                # Generate image
                gen_res = ImageGeneratorService.generate(
                    current_prompt, current_tier, classification, request_id,
                    force_defect=(force_defect and attempt_num == 1)
                )
                image_url = gen_res["web_url"]
                img_filepath = gen_res["filepath"]

                # Quality Verification (Module 4)
                verif = QualityVerifier.verify_image(img_filepath, classification, current_tier)
                actual_total_cost += verif["verification_cost"]

                attempt_record = {
                    "attempt": attempt_num,
                    "tier": current_tier,
                    "tier_name": TIERS[current_tier]["name"],
                    "action": f"AI Generation ({gen_res['provider']})",
                    "gen_cost": gen_cost,
                    "verif_cost": verif["verification_cost"],
                    "total_attempt_cost": round(gen_cost + verif["verification_cost"], 2),
                    "verification_result": verif,
                    "status": "PASS" if verif["passed"] else "FAIL"
                }

                if verif["passed"]:
                    resolved = True
                    final_status = "DELIVERED_PASS" if attempt_num == 1 else "DELIVERED_ESCALATED"
                    attempts_log.append(attempt_record)
                    break

                # Image Failed Verification! Module 5: Failure-Aware Correction & Escalation
                attempt_record["defect"] = verif["defect"]
                attempts_log.append(attempt_record)

                # Attempt Inexpensive PIL Auto-Correction first
                if policies.get("autocorrect_enabled", True) and verif.get("can_autocorrect"):
                    corr_filename = f"{request_id}_autocorrected.png"
                    corr_filepath = os.path.join(os.path.dirname(img_filepath), corr_filename)
                    corr_res = FailureEscalationManager.attempt_autocorrection(
                        img_filepath, classification, verif["defect"], corr_filepath
                    )

                    actual_total_cost += corr_res.get("cost", AUTOCORRECT_COST)

                    if corr_res.get("success"):
                        # Auto-correction succeeded!
                        image_url = f"/static/generated/{corr_filename}"
                        final_status = "DELIVERED_AUTOCORRECTED"
                        resolved = True
                        attempts_log.append({
                            "attempt": attempt_num,
                            "tier": current_tier,
                            "tier_name": "PixelWise Local Vision Repair",
                            "action": "Inexpensive Auto-Correction (PIL Adaptive Binarization)",
                            "gen_cost": 0.00,
                            "verif_cost": corr_res.get("cost", AUTOCORRECT_COST),
                            "total_attempt_cost": corr_res.get("cost", AUTOCORRECT_COST),
                            "verification_result": {
                                "passed": True,
                                "details": corr_res["details"],
                                "metrics": corr_res["new_metrics"]
                            },
                            "status": "PASS"
                        })
                        break

                # Auto-correction not possible or failed. Evaluate Controlled Escalation
                escalation = FailureEscalationManager.evaluate_escalation(
                    current_attempt=attempt_num,
                    current_spend=actual_total_cost,
                    current_tier=current_tier,
                    defect=verif["defect"],
                    original_prompt=prompt,
                    classification=classification,
                    policies=policies
                )

                if escalation.get("should_escalate"):
                    # Escalate to next tier on next iteration
                    current_tier = escalation["next_tier"]
                    current_prompt = escalation["enhanced_prompt"]
                    attempt_num += 1
                else:
                    # Policy limit reached
                    final_status = "FAILED_POLICY_LIMIT"
                    break

        actual_total_cost = round(actual_total_cost, 2)
        baseline_cost = BASELINE_COST_PER_IMAGE
        cost_saved = round(max(0.0, baseline_cost - actual_total_cost), 2)
        savings_pct = round((cost_saved / baseline_cost) * 100, 1)

        # Record in SQLite
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO generation_requests (
            request_id, school_id, teacher_name, prompt, material_type, grade_level,
            visual_style, complexity_score, chosen_tier, routing_details, attempts_log,
            final_status, image_url, svg_content, actual_cost, baseline_cost,
            cost_saved, verified_pass
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, school_id, teacher_name, prompt, material_type, grade_level,
            classification["visual_style"], classification["complexity_score"],
            chosen_tier, json.dumps(routing), json.dumps(attempts_log),
            final_status, image_url, svg_content, actual_total_cost, baseline_cost,
            cost_saved, 1 if "DELIVERED" in final_status else 0
        ))

        # Update school records
        is_reused_or_zero = 1 if chosen_tier in ["TIER_0_REUSE", "TIER_1_ZERO_AI_SVG"] else 0
        cursor.execute("""
        UPDATE schools
        SET current_spend = ROUND(current_spend + ?, 2),
            total_requests = total_requests + 1,
            reused_count = reused_count + ?
        WHERE id = ?
        """, (actual_total_cost, is_reused_or_zero, school_id))

        conn.commit()
        conn.close()

        return {
            "request_id": request_id,
            "school_id": school_id,
            "teacher_name": teacher_name,
            "prompt": prompt,
            "material_type": material_type,
            "grade_level": grade_level,
            "classification": classification,
            "routing": routing,
            "attempts_log": attempts_log,
            "final_status": final_status,
            "asset_type": "svg" if svg_content else "image",
            "image_url": image_url,
            "svg_content": svg_content,
            "actual_cost": actual_total_cost,
            "baseline_cost": baseline_cost,
            "cost_saved": cost_saved,
            "savings_pct": savings_pct
        }
