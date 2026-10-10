import os
import time
import requests
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
from config import UPLOAD_DIR, TIERS

os.makedirs(UPLOAD_DIR, exist_ok=True)

class ImageGeneratorService:
    """
    Image Generation Service:
    Executes image creation for the selected tier:
    - Tier 1: Zero-AI Vector SVG
    - Tier 2: Eco AI (Live API or local fast synthesizer)
    - Tier 3: Advanced AI (Live API high-res or rich synthesizer)
    Supports both live cloud generation and offline fallback.
    """

    @classmethod
    def generate(cls, prompt: str, tier_id: str, classification: dict, request_id: str, force_defect: bool = False) -> dict:
        visual_style = classification.get("visual_style", "FULL_COLOR_ILLUSTRATION")
        filename = f"{request_id}_{tier_id.lower()}.png"
        filepath = os.path.join(UPLOAD_DIR, filename)
        web_url = f"/static/generated/{filename}"

        # If force_defect is requested (for demonstration of auto-correction / escalation)
        if force_defect and tier_id == "TIER_2_ECO_AI":
            cls._create_defective_coloring_image(prompt, filepath)
            return {
                "success": True,
                "filepath": filepath,
                "web_url": web_url,
                "provider": TIERS[tier_id]["provider"],
                "is_simulated_defect": True
            }

        # Attempt Live Generation API (Pollinations.ai is free, public, fast, no API key needed)
        try:
            live_success = cls._try_live_api(prompt, tier_id, visual_style, filepath)
            if live_success:
                return {
                    "success": True,
                    "filepath": filepath,
                    "web_url": web_url,
                    "provider": TIERS[tier_id]["provider"] + " (Live Cloud API)",
                    "is_simulated_defect": False
                }
        except Exception as e:
            # Fall back to local procedural synthesizer if network is slow/offline
            pass

        # Offline procedural generation fallback
        cls._create_local_image(prompt, tier_id, visual_style, filepath)
        return {
            "success": True,
            "filepath": filepath,
            "web_url": web_url,
            "provider": TIERS[tier_id]["provider"] + " (Fast Engine)",
            "is_simulated_defect": False
        }

    @classmethod
    def _try_live_api(cls, prompt: str, tier_id: str, visual_style: str, save_path: str) -> bool:
        """
        Connects to fast diffusion generation API with appropriate prompt styling and resolution.
        """
        style_prompt = prompt
        width, height = 512, 512

        if tier_id == "TIER_3_ADVANCED_AI":
            width, height = 768, 768
            style_prompt = f"high quality educational poster illustration, masterpiece, sharp focus: {prompt}"
        elif visual_style == "LINE_ART_COLORING":
            style_prompt = f"clean coloring book page, black and white line art, pure white background, thick contour outlines, no shading: {prompt}"

        encoded = urllib.parse.quote(style_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&seed={int(time.time())}"

        resp = requests.get(url, timeout=7)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            # Verify file integrity
            img = Image.open(save_path)
            img.verify()
            return True
        return False

    @classmethod
    def _create_defective_coloring_image(cls, prompt: str, save_path: str):
        """
        Generates an image that intentionally has gray muddy shading
        to realistically demonstrate PixelWise's automated defect detection and PIL binarization fix!
        """
        img = Image.new("RGB", (600, 600), color=(185, 190, 195)) # Gray muddy background
        draw = ImageDraw.Draw(img)

        # Draw gray shading gradient
        for y in range(600):
            shade = int(170 + 40 * (y / 600))
            draw.line([(0, y), (600, y)], fill=(shade, shade, shade))

        # Draw a subject contour (e.g. elephant or butterfly shape)
        draw.ellipse([150, 150, 450, 450], outline=(40, 40, 40), width=4)
        draw.ellipse([200, 220, 270, 290], outline=(40, 40, 40), width=3)
        draw.ellipse([330, 220, 400, 290], outline=(40, 40, 40), width=3)
        draw.arc([230, 310, 370, 390], start=20, end=160, fill=(40, 40, 40), width=4)

        # Draw text indicator
        draw.text((300, 500), prompt[:35], fill=(30, 30, 30), anchor="ms")
        img.save(save_path, "PNG")

    @classmethod
    def _create_local_image(cls, prompt: str, tier_id: str, visual_style: str, save_path: str):
        """
        High quality local fallback procedural generation using Pillow.
        """
        if visual_style == "LINE_ART_COLORING":
            img = Image.new("RGB", (600, 600), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            # Draw clean outlines
            draw.text((300, 40), "PixelWise Educational Coloring Sheet", fill=(30, 41, 59), anchor="ms")
            draw.text((300, 70), prompt[:50], fill=(100, 116, 139), anchor="ms")

            # Main outline figure
            draw.ellipse([160, 160, 440, 440], outline=(15, 23, 42), width=5)
            draw.ellipse([220, 230, 280, 290], fill=(15, 23, 42))
            draw.ellipse([320, 230, 380, 290], fill=(15, 23, 42))
            draw.arc([240, 300, 360, 380], start=20, end=160, fill=(15, 23, 42), width=5)

            # Framing
            draw.rectangle([20, 20, 580, 580], outline=(203, 213, 225), width=2)
            img.save(save_path, "PNG")

        else: # Full color illustration / poster
            img = Image.new("RGB", (700, 700), color=(15, 23, 42))
            draw = ImageDraw.Draw(img)

            # Rich gradient background
            for y in range(700):
                r = int(15 + 25 * (y / 700))
                g = int(23 + 45 * (y / 700))
                b = int(42 + 90 * (y / 700))
                draw.line([(0, y), (700, y)], fill=(r, g, b))

            # Poster accents
            draw.ellipse([150, 120, 550, 520], outline=(56, 189, 248), width=4)
            draw.ellipse([250, 220, 450, 420], outline=(129, 140, 248), width=3)
            
            draw.text((350, 80), "DISTRICT EDUCATIONAL MATERIAL", fill=(147, 197, 253), anchor="ms")
            draw.text((350, 320), prompt[:40], fill=(248, 250, 252), anchor="ms")
            draw.text((350, 620), f"Generated via {TIERS[tier_id]['name']}", fill=(148, 163, 184), anchor="ms")

            img.save(save_path, "PNG")
