from xml.etree import ElementTree as ET
from zipfile import ZipFile

import cadquery as cq
import pytest
import trimesh
from pydantic import ValidationError

from printready.models import DesignSpec
from printready.service import generate_part
from printready.store import job_directory


@pytest.mark.parametrize("template,components", [("enclosure", 2), ("bracket", 1), ("adapter", 1)])
def test_generated_solid_roundtrip(template, components):
    job = generate_part(DesignSpec(template=template))
    directory = job_directory(job["id"])
    assert job["report"]["status"] == "geometry_validated"
    assert job["report"]["components"] == components
    assert all(check["status"] == "pass" for check in job["report"]["checks"])
    imported = cq.importers.importStep(str(directory / "model.step"))
    assert imported.val().isValid()
    assert len(imported.solids().vals()) == components
    mesh = trimesh.load_mesh(directory / "model.stl")
    assert mesh.is_watertight and mesh.volume > 0
    with ZipFile(directory / "model.3mf") as archive:
        xml = ET.fromstring(archive.read("3D/3dmodel.model"))
        ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
        assert xml.attrib["unit"] == "millimeter"
        assert len(xml.findall("m:resources/m:object", ns)) == components
        assert not any(name.endswith(".gcode") for name in archive.namelist())
    preview = trimesh.load(directory / "preview.glb")
    assert len(preview.geometry) == components
    assert preview.extents * 1000 == pytest.approx(job["report"]["dimensions"], abs=0.01)


def test_oversized_component_fails_build_envelope():
    spec = DesignSpec.model_validate({"parameters": {"width": 280}})
    report = generate_part(spec)["report"]
    assert report["status"] == "failed"
    assert next(c for c in report["checks"] if c["id"] == "build_volume")["status"] == "fail"


def test_separate_plates_are_not_silently_approved():
    report = generate_part(DesignSpec.model_validate({"parameters": {"width": 150}}))["report"]
    assert not report["layout_fits"]
    assert any("separate plates" in warning for warning in report["warnings"])


@pytest.mark.parametrize(
    "payload",
    [
        {"parameters": {"width": -1}},
        {"parameters": {"wall": float("nan")}},
        {"parameters": {"width": 20, "depth": 20, "wall": 10}},
        {"template": "adapter", "parameters": {"inner_diameter": 59}},
        {"printer": "unknown"},
        {"parameters": {"code": "import os"}},
    ],
)
def test_invalid_design_rejected_before_cad(payload):
    with pytest.raises(ValidationError):
        DesignSpec.model_validate(payload)


def test_adapter_clearance_is_applied_radially():
    job = generate_part(DesignSpec(template="adapter"))
    model = cq.importers.importStep(str(job_directory(job["id"]) / "model.step"))
    # The material volume follows the exact bore enlarged by clearance on both sides.
    import math

    p = job["spec"]["parameters"]
    bore = p["inner_diameter"] / 2 + p["clearance"]
    expected = math.pi * ((p["outer_diameter"] / 2) ** 2 - bore**2) * p["base_thickness"]
    expected += math.pi * ((bore + p["wall"]) ** 2 - bore**2) * (p["height"] - p["base_thickness"])
    assert model.val().Volume() == pytest.approx(expected, rel=1e-6)
