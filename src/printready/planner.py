import re

from .knowledge import search_knowledge
from .models import BriefRequest, DesignSpec

ALIASES = {
    "width": "width",
    "largura": "width",
    "depth": "depth",
    "profundidade": "depth",
    "height": "height",
    "altura": "height",
    "wall": "wall",
    "parede": "wall",
    "clearance": "clearance",
    "folga": "clearance",
    "outer diameter": "outer_diameter",
    "diametro externo": "outer_diameter",
    "inner diameter": "inner_diameter",
    "diametro interno": "inner_diameter",
    "hole": "hole_diameter",
    "furo": "hole_diameter",
}


def plan_brief(request: BriefRequest) -> dict:
    text = request.brief.lower()
    spec = request.spec.model_dump()
    for template, words in {
        "enclosure": ("enclosure", "caixa"),
        "bracket": ("bracket", "suporte"),
        "adapter": ("adapter", "adaptador"),
    }.items():
        if any(re.search(r"\b" + word + r"\b", text) for word in words):
            spec["template"] = template
            break
    matched = []
    triple = re.search(
        r"(\d+(?:[.,]\d+)?)\s*[x*]\s*(\d+(?:[.,]\d+)?)\s*[x*]\s*"
        r"(\d+(?:[.,]\d+)?)\s*(mm|cm|inches|inch)?\b",
        text,
    )
    if triple and spec["template"] != "adapter":
        factor = {"cm": 10, "inch": 25.4, "inches": 25.4}.get(triple.group(4), 1)
        for key, value in zip(("width", "depth", "height"), triple.groups()[:3], strict=True):
            spec["parameters"][key] = float(value.replace(",", ".")) * factor
            matched.append(key)
    for alias, key in ALIASES.items():
        match = re.search(
            r"\b" + alias + r"\s*(?:[:=]|of|de)?\s*(\d+(?:[.,]\d+)?)"
            r"\s*(mm|cm|inches|inch)?\b",
            text,
        )
        if match:
            factor = {"cm": 10, "inch": 25.4, "inches": 25.4}.get(match.group(2), 1)
            spec["parameters"][key] = float(match.group(1).replace(",", ".")) * factor
            matched.append(key)
    for material in ("PLA", "PETG", "ABS"):
        if re.search(r"\b" + material.lower() + r"\b", text):
            spec["material"] = material
    if "k1c" in text:
        spec["printer"] = "creality-k1c"
    elif re.search(r"\ba1\b", text):
        spec["printer"] = "bambu-a1"
    validated = DesignSpec.model_validate(spec)
    return {
        "spec": validated.model_dump(),
        "mode": "bounded_local_parser",
        "matched_parameters": sorted(set(matched)),
        "questions": [] if matched else ["Confirm dimensions in the parameter controls before generating."],
        "evidence": search_knowledge(request.brief + " " + validated.template),
    }
