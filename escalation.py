import os
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
from config import AUTOCORRECT_COST, TIERS
from modules.verifier import QualityVerifier

class FailureEscalationManager:
    """
    Module 5: Failure-Aware Correction & Escalation
    Performs:
    1. Targeted inexpensive image-processing auto-correction (PIL binarization/contrast fix) at ₹0.02
    2. Controlled escalation to Advanced AI if auto-correction is unsuitable or fails
    3. Policy and budget enforcement (max retries, max budget cap)
    """

    @classmethod
    def attempt_autocorrection(cls, image_path: str, classification: dict, defect: str, save_path: str) -> dict:
        """
        Attempts local image-processing repair using PIL algorithms.
        Cost: ₹0.02 (negligible compared to ₹5.50 regeneration).
        """
        try:
            img = Image.open(image_path)
            visual_style = classification.get("visual_style", "FULL_COLOR_ILLUSTRATION")

            if visual_style == "LINE_ART_COLORING":
                # Convert to grayscale
                gray = img.convert("L")
                
                # Boost contrast first
                enhancer = ImageEnhance.Contrast(gray)
                boosted = enhancer.enhance(1.8)

                # Binarization / thresholding: convert muddy gray background to pure 255
                # and darken outlines to pure 0
                arr = np.array(boosted)
                # Adaptive threshold: values above 165 become 255 (white), below 110 become 0 (black)
                # values in between are scaled smoothly
                output = np.where(arr > 165, 255, arr)
                output = np.where(output < 110, 0, output)
                
                corrected_img = Image.fromarray(output.astype(np.uint8)).convert("RGB")
                corrected_img.save(save_path, "PNG")

                # Re-verify the corrected image
                reverify = QualityVerifier.verify_image(corrected_img, classification, "TIER_2_ECO_AI")

                if reverify["passed"]:
                    return {
                        "success": True,
                        "cost": AUTOCORRECT_COST,
                        "method": "PIL_ADAPTIVE_BINARIZATION",
                        "corrected_path": save_path,
                        "details": "Repaired muddy background to pure white canvas and reinforced black outlines.",
                        "new_metrics": reverify["metrics"]
                    }
                else:
                    return {
                        "success": False,
                        "cost": AUTOCORRECT_COST,
                        "method": "PIL_ADAPTIVE_BINARIZATION",
                        "details": f"Auto-correction attempted but image still exhibits defect: {reverify['defect']}.",
                        "metrics": reverify["metrics"]
                    }

            else:
                # For non-coloring images with low contrast
                enhancer = ImageEnhance.Contrast(img)
                enhanced = enhancer.enhance(1.5)
                enhancer_sharp = ImageEnhance.Sharpness(enhanced)
                final_img = enhancer_sharp.enhance(1.3)
                final_img.save(save_path, "PNG")

                reverify = QualityVerifier.verify_image(final_img, classification, "TIER_2_ECO_AI")
                return {
                    "success": reverify["passed"],
                    "cost": AUTOCORRECT_COST,
                    "method": "PIL_CONTRAST_SHARPEN",
                    "corrected_path": save_path if reverify["passed"] else None,
                    "details": "Contrast and sharpness normalization applied.",
                    "new_metrics": reverify["metrics"]
                }

        except Exception as e:
            return {
                "success": False,
                "cost": 0.00,
                "method": "NONE",
                "details": f"Auto-correction failed due to processing error: {str(e)}"
            }

    @classmethod
    def evaluate_escalation(cls, current_attempt: int, current_spend: float, current_tier: str,
                            defect: str, original_prompt: str, classification: dict, policies: dict) -> dict:
        """
        Determines whether to escalate to a more capable model or enforce policy limits.
        """
        max_retries = policies.get("max_retries", 2)
        max_budget = policies.get("max_request_budget", 8.00)

        # Check if attempts exceeded
        if current_attempt >= max_retries:
            return {
                "should_escalate": False,
                "reason": f"District policy limit reached ({max_retries} maximum attempts). Generation halted to prevent uncontrolled cloud expenditure.",
                "policy_blocked": True
            }

        # Check target tier and cost
        next_tier = "TIER_3_ADVANCED_AI"
        next_tier_cost = TIERS[next_tier]["cost_gen"] + TIERS[next_tier]["cost_verif"]

        if (current_spend + next_tier_cost) > max_budget:
            return {
                "should_escalate": False,
                "reason": f"Projected total cost (₹{current_spend + next_tier_cost:.2f}) would exceed district per-request budget cap of ₹{max_budget:.2f}.",
                "policy_blocked": True
            }

        # Craft enhanced prompt for the escalated model
        enhanced_prompt = original_prompt
        visual_style = classification.get("visual_style", "FULL_COLOR_ILLUSTRATION")

        if visual_style == "LINE_ART_COLORING":
            enhanced_prompt = f"Pure black outline vector line art for coloring page, thick clean black contour lines on pure white paper, zero shading, no color fill, educational worksheet: {original_prompt}"
        elif visual_style in ["DIAGRAM", "LABELED_FLASHCARD"]:
            enhanced_prompt = f"Educational infographic diagram, crystal clear labels, high contrast educational illustration: {original_prompt}"
        else:
            enhanced_prompt = f"High fidelity educational poster, 8k resolution, photorealistic sharp detail, professional lighting: {original_prompt}"

        return {
            "should_escalate": True,
            "next_tier": next_tier,
            "tier_name": TIERS[next_tier]["name"],
            "additional_cost_est": next_tier_cost,
            "enhanced_prompt": enhanced_prompt,
            "reason": f"Escalated from {TIERS[current_tier]['name']} to {TIERS[next_tier]['name']} to resolve defect '{defect}'. Justified by budget policy."
        }
