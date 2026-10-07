import re

from rank_bm25 import BM25Okapi

DOCUMENTS = [
    {
        "id": "enclosure-design",
        "title": "Electronics enclosure: floor, bosses and lid",
        "text": "An electronics enclosure caixa eletronica has a floor, screw bosses and a separate lid. "
        "Confirm PCB dimensions, connector positions, screw diameter and internal height. "
        "The lid has a locating lip with explicit clearance. Check body and lid separately.",
        "template": "enclosure",
    },
    {
        "id": "fit-clearance",
        "title": "Fit clearance is a measured design input",
        "text": "Clearance folga encaixe is radial or per side, not a universal printing tolerance. "
        "Start with a calibration coupon and measure the printed result. A 0.3 mm example "
        "is only a demonstration value. Material shrinkage, orientation and machine calibration matter.",
        "template": "all",
    },
    {
        "id": "bracket-design",
        "title": "L-bracket: mounting holes and orientation",
        "text": "An L bracket suporte has perpendicular mounting faces, through holes and material "
        "around each hole. Printed layer orientation affects strength. This tool validates geometry, "
        "not load capacity. A structural or safety-critical application needs separate engineering.",
        "template": "bracket",
    },
    {
        "id": "adapter-design",
        "title": "Flanged adapter: bore and neck",
        "text": "A flanged adapter adaptador has an inner bore, neck wall and larger flange. "
        "Confirm whether the requested diameter is the measured mating part or the final bore. "
        "The bore in this template equals inner diameter plus twice radial clearance.",
        "template": "adapter",
    },
    {
        "id": "slicer-evidence",
        "title": "Slicing is a separate validation stage",
        "text": "Slicer fatiamento must use the exact printer, nozzle, filament and process profiles. "
        "A closed mesh alone does not establish printability. Record slicer version, preset names, "
        "warnings, time and filament. A geometry-only 3MF does not contain printer-ready G-code.",
        "template": "all",
    },
    {
        "id": "wall-features",
        "title": "Walls and small features",
        "text": "Wall parede thickness must be considered against nozzle diameter and extrusion width. "
        "Two nozzle diameters is a conservative template rule, not a measurement of arbitrary "
        "mesh thickness. Review thin details, bridges, overhangs and support in the slicer.",
        "template": "all",
    },
    {
        "id": "physical-approval",
        "title": "Physical printing requires a separate approval",
        "text": "An approved file is tied to its exact hash and printer profile. Printer telemetry "
        "must confirm readiness before any physical action. This public MVP has no upload, "
        "heat, movement or print-start tool. Physical results must be measured and documented.",
        "template": "all",
    },
]


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


INDEX = BM25Okapi([tokens(d["title"] + " " + d["text"]) for d in DOCUMENTS])


def search_knowledge(query: str, limit: int = 3) -> list[dict]:
    scores = INDEX.get_scores(tokens(query))
    ranked = sorted(zip(DOCUMENTS, scores, strict=True), key=lambda pair: pair[1], reverse=True)
    return [dict(doc, score=round(float(score), 4)) for doc, score in ranked[:limit] if score > 0]
