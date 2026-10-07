from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import cadquery as cq
import numpy as np
import trimesh

from .models import PROFILES, DesignSpec


def build_parts(spec: DesignSpec) -> dict[str, cq.Workplane]:
    p = spec.parameters
    if spec.template == "enclosure":
        body = cq.Workplane("XY").box(p.width, p.depth, p.height, centered=(True, True, False))
        cavity = (
            cq.Workplane("XY")
            .workplane(offset=p.wall)
            .box(p.width - 2 * p.wall, p.depth - 2 * p.wall, p.height, centered=(True, True, False))
        )
        body = body.cut(cavity)
        r = max(p.wall * 1.4, p.hole_diameter / 2 + p.wall)
        # Overlap bosses with the walls; a tangent contact produces non-manifold STL edges.
        x, y = p.width / 2 - 0.75 * p.wall - r, p.depth / 2 - 0.75 * p.wall - r
        points = [(sx * x, sy * y) for sx in (-1, 1) for sy in (-1, 1)]
        for px, py in points:
            boss = cq.Workplane("XY").center(px, py).circle(r).extrude(p.height)
            body = body.union(boss)
        holes = cq.Workplane("XY").pushPoints(points).circle(p.hole_diameter / 2).extrude(p.height)
        body = body.cut(holes)
        lid = cq.Workplane("XY").box(p.width, p.depth, p.wall, centered=(True, True, False))
        # The locating lip is offset from the cavity by the explicit per-side clearance.
        lip_w, lip_d = p.width - 2 * p.wall - 2 * p.clearance, p.depth - 2 * p.wall - 2 * p.clearance
        lip = (
            cq.Workplane("XY")
            .workplane(offset=p.wall)
            .rect(lip_w, lip_d)
            .rect(lip_w - 2 * p.wall, lip_d - 2 * p.wall)
            .extrude(p.wall)
        )
        # Keep the lip clear of the screw bosses at all four corners.
        for px, py in points:
            lip = lip.cut(cq.Workplane("XY").center(px, py).circle(r + p.clearance).extrude(3 * p.wall))
        lid = lid.union(lip).cut(
            cq.Workplane("XY")
            .pushPoints(points)
            .circle(p.hole_diameter / 2 + p.clearance)
            .extrude(4 * p.wall)
        )
        return {"body": body, "lid": lid.translate((p.width + 8, 0, 0))}
    if spec.template == "bracket":
        base = cq.Workplane("XY").box(p.width, p.depth, p.wall, centered=(True, True, False))
        upright = cq.Workplane("XY").box(p.width, p.wall, p.height, centered=(True, True, False))
        upright = upright.translate((0, -p.depth / 2 + p.wall / 2, 0))
        bracket = base.union(upright)
        floor_points = [(sx * p.width / 4, p.depth / 4) for sx in (-1, 1)]
        floor_holes = cq.Workplane("XY").pushPoints(floor_points).circle(p.hole_diameter / 2).extrude(p.wall)
        bracket = bracket.cut(floor_holes)
        for x in (-p.width / 4, p.width / 4):
            hole = cq.Solid.makeCylinder(
                p.hole_diameter / 2,
                p.wall * 3,
                cq.Vector(x, -p.depth / 2 - p.wall, p.height * 0.65),
                cq.Vector(0, 1, 0),
            )
            bracket = bracket.cut(hole)
        return {"bracket": bracket}
    bore = p.inner_diameter / 2 + p.clearance
    neck = bore + p.wall
    flange = cq.Workplane("XY").circle(p.outer_diameter / 2).circle(bore).extrude(p.base_thickness)
    stem = (
        cq.Workplane("XY")
        .workplane(offset=p.base_thickness)
        .circle(neck)
        .circle(bore)
        .extrude(p.height - p.base_thickness)
    )
    return {"adapter": flange.union(stem)}


def export_3mf(meshes: dict[str, trimesh.Trimesh], target: Path):
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("", ns)
    model = ET.Element(f"{{{ns}}}model", {"unit": "millimeter", "xml:lang": "en-US"})
    resources, build = ET.SubElement(model, f"{{{ns}}}resources"), ET.SubElement(model, f"{{{ns}}}build")
    for index, (name, mesh) in enumerate(meshes.items(), start=1):
        obj = ET.SubElement(resources, f"{{{ns}}}object", {"id": str(index), "type": "model", "name": name})
        geometry = ET.SubElement(obj, f"{{{ns}}}mesh")
        vertices = ET.SubElement(geometry, f"{{{ns}}}vertices")
        for x, y, z in mesh.vertices:
            ET.SubElement(vertices, f"{{{ns}}}vertex", {"x": f"{x:.7g}", "y": f"{y:.7g}", "z": f"{z:.7g}"})
        triangles = ET.SubElement(geometry, f"{{{ns}}}triangles")
        for a, b, c in mesh.faces:
            ET.SubElement(triangles, f"{{{ns}}}triangle", {"v1": str(a), "v2": str(b), "v3": str(c)})
        ET.SubElement(build, f"{{{ns}}}item", {"objectid": str(index)})
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types '
            'xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="model" '
            'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?><Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            "</Relationships>",
        )
        archive.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))


def generate_geometry(spec: DesignSpec, directory: Path) -> dict:
    parts = build_parts(spec)
    meshes = {}
    measurements = []
    scene = trimesh.Scene()
    for index, (name, part) in enumerate(parts.items()):
        path = directory / f"{name}.stl"
        cq.exporters.export(part, str(path), tolerance=0.05, angularTolerance=0.1)
        mesh = trimesh.load_mesh(path, process=True)
        meshes[name] = mesh
        display_mesh = mesh.copy()
        display_mesh.visual.face_colors = [21, 137, 137, 255] if index == 0 else [100, 177, 190, 255]
        scene.add_geometry(display_mesh, node_name=name, geom_name=name)
        measurements.append(
            {
                "name": name,
                "dimensions": np.round(mesh.extents, 3).tolist(),
                "volume_mm3": round(float(part.val().Volume()), 3),
                "watertight": bool(mesh.is_watertight),
                "positive_volume": bool(mesh.is_volume),
                "cad_valid": bool(part.val().isValid()),
                "shells": len(mesh.split(only_watertight=False)),
            }
        )
    cq.exporters.export(
        cq.Compound.makeCompound([p.val() for p in parts.values()]), str(directory / "model.step")
    )
    trimesh.util.concatenate(list(meshes.values())).export(directory / "model.stl")
    # glTF uses meters, while manufacturing artifacts and reports use millimeters.
    scene.scaled(0.001).export(str(directory / "preview.glb"))
    export_3mf(meshes, directory / "model.3mf")
    build_volume = PROFILES[spec.printer]["build_volume"]
    fits = all(
        all(a <= b + 0.001 for a, b in zip(m["dimensions"], build_volume, strict=True)) for m in measurements
    )
    collisions = []
    names = list(parts)
    for i, name in enumerate(names):
        for other in names[i + 1 :]:
            volume = parts[name].intersect(parts[other]).val().Volume()
            if volume > 0.0001:
                collisions.append([name, other])
    wall_ok = spec.parameters.wall >= 2 * spec.nozzle
    checks = [
        {
            "id": "watertight",
            "label": "Closed mesh",
            "status": "pass" if all(m["watertight"] for m in measurements) else "fail",
            "detail": "Every generated component has a closed triangle mesh.",
        },
        {
            "id": "solid",
            "label": "Positive volume",
            "status": "pass"
            if all(m["positive_volume"] and m["cad_valid"] for m in measurements)
            else "fail",
            "detail": "Exact CAD solids and mesh orientation checked.",
        },
        {
            "id": "build_volume",
            "label": "Build volume",
            "status": "pass" if fits else "fail",
            "detail": f"Per-component check against {' x '.join(map(str, build_volume))} mm.",
        },
        {
            "id": "wall",
            "label": "Wall feature rule",
            "status": "pass" if wall_ok else "warning",
            "detail": (
                f"Template wall {spec.parameters.wall:g} mm; nozzle {spec.nozzle:g} mm. "
                "Not a mesh-wide thickness measurement."
            ),
        },
        {
            "id": "collisions",
            "label": "Part intersections",
            "status": "pass" if not collisions else "fail",
            "detail": "Exact solid intersections in the exported print layout.",
        },
    ]
    all_mesh = trimesh.util.concatenate(list(meshes.values()))
    layout_fits = all(a <= b for a, b in zip(all_mesh.extents, build_volume, strict=True))
    warnings = (
        [] if layout_fits else ["Combined layout exceeds the plate. Arrange components on separate plates."]
    )
    if spec.material == "ABS" and spec.printer == "bambu-a1":
        warnings.append(
            "ABS on an open A1 needs material/process review; geometry checks do not approve this setup."
        )
    return {
        "status": "failed" if any(c["status"] == "fail" for c in checks) else "geometry_validated",
        "checks": checks,
        "parts": measurements,
        "components": len(parts),
        "volume_mm3": round(sum(m["volume_mm3"] for m in measurements), 3),
        "dimensions": np.round(all_mesh.extents, 3).tolist(),
        "build_volume": build_volume,
        "warnings": warnings,
        "layout_fits": layout_fits,
        "scope": "Generated template geometry only. Slicing and physical fit are separate validations.",
    }
