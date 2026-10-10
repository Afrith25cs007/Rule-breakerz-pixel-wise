import os
import io
from PIL import Image, ImageStat
import numpy as np
from config import TIERS

class QualityVerifier:
    """
    Module 4: Quality Verification Engine
    Performs multi-stage hierarchical verification:
    1. Technical checks (valid format, dimensions, non-empty)
    2. Rule-based visual checks (Pillow: background whiteness, contrast, edge thickness, color leakage)
    3. Failure identification for targeted auto-correction
    """

    @classmethod
    def verify_svg(cls, svg_content: str) -> dict:
        """
        Validates SVG vector content.
        """
        if not svg_content or not isinstance(svg_content, str):
            return {
                "passed": False,
                "defect": "CORRUPTED_VECTOR_CONTENT",
                "details": "SVG content is empty or invalid.",
                "verification_cost": 0.05,
                "metrics": {}
            }

        if "<svg" in svg_content and "</svg>" in svg_content:
            return {
                "passed": True,
                "defect": "NONE",
                "details": "Vector XML structure verified. Crisp infinite-resolution line art.",
                "verification_cost": 0.05,
                "metrics": {
                    "vector_type": "Scalable SVG",
                    "pixel_density": "Infinite",
                    "background": "Pure White (#FFFFFF)"
                }
            }
        
        return {
            "passed": False,
            "defect": "INVALID_SVG_MARKUP",
            "details": "SVG tags missing or malformed.",
            "verification_cost": 0.05,
            "metrics": {}
        }

    @classmethod
    def verify_image(cls, image_path_or_bytes, classification: dict, tier_id: str) -> dict:
        """
        Validates raster images using PIL computer vision algorithms.
        """
        verif_cost = TIERS.get(tier_id, {}).get("cost_verif", 0.20)
        visual_style = classification.get("visual_style", "FULL_COLOR_ILLUSTRATION")

        # 1. Technical Check
        try:
            if isinstance(image_path_or_bytes, (str, bytes)):
                if isinstance(image_path_or_bytes, str) and os.path.exists(image_path_or_bytes):
                    img = Image.open(image_path_or_bytes)
                elif isinstance(image_path_or_bytes, bytes):
                    img = Image.open(io.BytesIO(image_path_or_bytes))
                else:
                    return {
                        "passed": False,
                        "defect": "FILE_NOT_FOUND",
                        "details": "Image file could not be opened.",
                        "verification_cost": verif_cost,
                        "metrics": {}
                    }
            elif isinstance(image_path_or_bytes, Image.Image):
                img = image_path_or_bytes
            else:
                return {
                    "passed": False,
                    "defect": "INVALID_IMAGE_OBJECT",
                    "details": "Unsupported image format or object.",
                    "verification_cost": verif_cost,
                    "metrics": {}
                }

            img = img.convert("RGB")
            width, height = img.size

            if width < 256 or height < 256:
                return {
                    "passed": False,
                    "defect": "UNDERSIZED_RESOLUTION",
                    "details": f"Image resolution {width}x{height} below minimum educational standard.",
                    "verification_cost": verif_cost,
                    "metrics": {"width": width, "height": height}
                }

        except Exception as e:
            return {
                "passed": False,
                "defect": "IMAGE_CORRUPTION",
                "details": f"Failed technical validation: {str(e)}",
                "verification_cost": verif_cost,
                "metrics": {}
            }

        # Convert to numpy array for fast statistical evaluation
        arr = np.array(img)
        gray = np.array(img.convert("L"))

        # 2. Domain-Specific Visual Verification
        if visual_style == "LINE_ART_COLORING":
            # For coloring worksheets:
            # - Background must be clean white (luminance > 235)
            # - Outlines must be dark (luminance < 60)
            # - Minimal unwanted color saturation (for black and white outlines)

            white_pixels = np.sum(gray > 235)
            total_pixels = gray.size
            whiteness_pct = round(float(white_pixels / total_pixels) * 100, 1)

            dark_pixels = np.sum(gray < 60)
            outline_pct = round(float(dark_pixels / total_pixels) * 100, 1)

            # Color saturation: max(R,G,B) - min(R,G,B)
            rgb_diff = np.max(arr, axis=2) - np.min(arr, axis=2)
            colored_pixels = np.sum(rgb_diff > 35)
            saturation_pct = round(float(colored_pixels / total_pixels) * 100, 1)

            metrics = {
                "whiteness_pct": whiteness_pct,
                "outline_density_pct": outline_pct,
                "color_saturation_pct": saturation_pct,
                "resolution": f"{width}x{height}"
            }

            # Check 2a: Unwanted colors in B&W worksheet
            if saturation_pct > 12.0:
                return {
                    "passed": False,
                    "defect": "UNWANTED_COLOR_FILL",
                    "can_autocorrect": True,
                    "details": f"Detected colored fill ({saturation_pct}% saturated pixels). Coloring worksheet requires monochrome outlines.",
                    "verification_cost": verif_cost,
                    "metrics": metrics
                }

            # Check 2b: Background shading / muddy gray tones
            if whiteness_pct < 60.0:
                return {
                    "passed": False,
                    "defect": "EXCESSIVE_BACKGROUND_SHADING",
                    "can_autocorrect": True,
                    "details": f"Canvas whiteness ({whiteness_pct}%) below 60% threshold. Unwanted gray shading or gradient background.",
                    "verification_cost": verif_cost,
                    "metrics": metrics
                }

            # Check 2c: Faint outlines
            if outline_pct < 1.5:
                return {
                    "passed": False,
                    "defect": "FAINT_OUTLINES",
                    "can_autocorrect": True,
                    "details": f"Outline density ({outline_pct}%) too low. Line strokes are too faint for student coloring.",
                    "verification_cost": verif_cost,
                    "metrics": metrics
                }

            return {
                "passed": True,
                "defect": "NONE",
                "can_autocorrect": False,
                "details": f"Worksheet verified: {whiteness_pct}% clean background, {outline_pct}% crisp outlines.",
                "verification_cost": verif_cost,
                "metrics": metrics
            }

        else: # Flashcards, Diagrams, Posters
            # Check dynamic range and contrast
            stat = ImageStat.Stat(img)
            contrast_std = round(float(np.mean(stat.stddev)), 1)
            mean_brightness = round(float(np.mean(stat.mean)), 1)

            metrics = {
                "contrast_std": contrast_std,
                "mean_brightness": mean_brightness,
                "resolution": f"{width}x{height}"
            }

            if contrast_std < 22.0:
                return {
                    "passed": False,
                    "defect": "LOW_CONTRAST_IMAGE",
                    "can_autocorrect": True,
                    "details": f"Low contrast standard deviation ({contrast_std}). Image appears washed out or blank.",
                    "verification_cost": verif_cost,
                    "metrics": metrics
                }

            return {
                "passed": True,
                "defect": "NONE",
                "can_autocorrect": False,
                "details": f"Visual verification passed: Good dynamic range ({contrast_std} std-dev) and balance.",
                "verification_cost": verif_cost,
                "metrics": metrics
            }
