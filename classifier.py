import re

class RequestClassifier:
    """
    Module 1: Intelligent Request Classification
    Analyses prompt text, material type, and target audience to classify visual style,
    complexity, quality constraints, and Zero-AI eligibility.
    """

    COLORING_KEYWORDS = {
        "coloring", "colouring", "outline", "outlines", "black and white", "black & white",
        "b&w", "monochrome", "line art", "tracing", "trace", "contour", "coloring sheet",
        "coloring page", "stencil", "fill", "no shading", "thick lines", "drawings to color"
    }

    DIAGRAM_KEYWORDS = {
        "diagram", "flashcard", "water cycle", "solar system", "anatomy", "labeled",
        "labels", "parts of", "flowchart", "fraction", "pie chart", "shapes", "geometry",
        "cell structure", "plant cell", "photosynthesis", "map", "schematic"
    }

    HIGH_FIDELITY_KEYWORDS = {
        "poster", "annual report", "detailed", "photorealistic", "historical", "civilization",
        "complex", "high resolution", "cinematic", "intricate", "fine art", "masterpiece",
        "celebration", "conference", "presentation", "district report", "architectural", "realistic"
    }

    SUBJECT_VOCABULARY = [
        "elephant", "butterfly", "lion", "cat", "dog", "owl", "fish", "turtle", "dinosaur",
        "bird", "horse", "tree", "flower", "water cycle", "solar system", "planets",
        "shapes", "geometric shapes", "fraction", "plant cell", "human heart", "volcano",
        "robot", "rocket", "apple", "banana", "book", "pencil", "school", "car"
    ]

    @classmethod
    def classify(cls, prompt: str, material_type: str = "worksheet", grade_level: str = "primary") -> dict:
        prompt_lower = prompt.lower()
        
        # 1. Detect tags / subject tokens
        detected_tags = []
        for subj in cls.SUBJECT_VOCABULARY:
            if re.search(r'\b' + re.escape(subj) + r'\b', prompt_lower):
                detected_tags.append(subj)

        # 2. Check keyword matches
        has_coloring_kw = any(kw in prompt_lower for kw in cls.COLORING_KEYWORDS)
        has_diagram_kw = any(kw in prompt_lower for kw in cls.DIAGRAM_KEYWORDS)
        has_high_kw = any(kw in prompt_lower for kw in cls.HIGH_FIDELITY_KEYWORDS)

        # 3. Determine Visual Style & Complexity
        visual_style = "FULL_COLOR_ILLUSTRATION"
        complexity_score = 3
        zero_ai_eligible = False
        quality_priority = "AESTHETIC_FIDELITY"
        explanation = ""

        # Material type heuristics combined with prompt cues
        if material_type == "worksheet" or has_coloring_kw:
            if "detailed" in prompt_lower and not has_coloring_kw:
                visual_style = "FULL_COLOR_ILLUSTRATION"
                complexity_score = 3
                quality_priority = "AESTHETIC_FIDELITY"
                explanation = "Educational worksheet with custom illustration elements."
            else:
                visual_style = "LINE_ART_COLORING"
                complexity_score = 1 if (grade_level in ["kindergarten", "primary"] and not has_high_kw) else 2
                quality_priority = "CLEAN_OUTLINE_NO_SHADING"
                zero_ai_eligible = True
                explanation = "Simple black-and-white line art outline suitable for student coloring or tracing."

        elif material_type == "flashcard" or has_diagram_kw:
            visual_style = "DIAGRAM" if has_diagram_kw else "LABELED_FLASHCARD"
            complexity_score = 2 if grade_level in ["kindergarten", "primary"] else 3
            quality_priority = "READABLE_LABELS_EDUCATIONAL"
            zero_ai_eligible = True if any(t in ["water cycle", "solar system", "shapes", "fraction", "plant cell"] for t in detected_tags) else False
            explanation = "Educational reference visual or diagram with labeled subject concepts."

        elif material_type == "poster" or has_high_kw:
            if has_coloring_kw:
                visual_style = "LINE_ART_COLORING"
                complexity_score = 2
                quality_priority = "CLEAN_OUTLINE_NO_SHADING"
                explanation = "Coloring poster for classroom group activity."
            else:
                visual_style = "HIGH_RES_POSTER"
                complexity_score = 5 if any(k in prompt_lower for k in ["annual report", "historical", "intricate", "detailed scene"]) else 4
                quality_priority = "AESTHETIC_HIGH_FIDELITY"
                zero_ai_eligible = False
                explanation = "High-fidelity presentation or commemorative poster requiring rich textures and composition."

        else: # Generic / custom
            if has_high_kw:
                visual_style = "HIGH_RES_POSTER"
                complexity_score = 4
                quality_priority = "AESTHETIC_HIGH_FIDELITY"
                explanation = "Detailed multi-element composition."
            elif has_coloring_kw:
                visual_style = "LINE_ART_COLORING"
                complexity_score = 1
                quality_priority = "CLEAN_OUTLINE_NO_SHADING"
                zero_ai_eligible = True
                explanation = "Black and white outline drawing."
            else:
                visual_style = "FULL_COLOR_ILLUSTRATION"
                complexity_score = 3
                quality_priority = "AESTHETIC_FIDELITY"
                explanation = "Standard educational illustration."

        return {
            "visual_style": visual_style,
            "complexity_score": complexity_score,
            "quality_priority": quality_priority,
            "zero_ai_eligible": zero_ai_eligible,
            "detected_tags": detected_tags,
            "explanation": explanation
        }
