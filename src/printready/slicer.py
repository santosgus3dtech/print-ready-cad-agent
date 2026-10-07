import hashlib
import json
import os
import re
import subprocess
import threading
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .store import job_directory, save_job

SLICE_LOCK = threading.Lock()


def executable() -> Path | None:
    candidates = [
        os.getenv("PRINTREADY_SLICER", ""),
        "C:/Program Files/Bambu Studio/bambu-studio.exe",
        "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
    ]
    return next((Path(p) for p in candidates if p and Path(p).is_file()), None)


def capabilities() -> dict:
    binary = executable()
    return {
        "available": binary is not None,
        "name": "Bambu Studio" if binary else None,
        "physical_controls": False,
        "profile_policy": "Exact local presets only",
    }


def resolve_profile(name: str, index: dict[str, dict], stack: tuple[str, ...] = ()) -> dict:
    if name in stack:
        raise ValueError("Cyclic slicer preset inheritance.")
    if name not in index:
        raise ValueError(f"Missing slicer preset dependency: {name}")
    profile = index[name]
    resolved = {}
    if profile.get("inherits"):
        resolved.update(resolve_profile(profile["inherits"], index, (*stack, name)))
    for dependency in profile.get("include", []):
        resolved.update(resolve_profile(dependency, index, (*stack, name)))
    resolved.update({key: value for key, value in profile.items() if key not in {"inherits", "include"}})
    return resolved


def preset_index(directory: Path) -> dict[str, dict]:
    profiles = {}
    for path in directory.rglob("*.json"):
        try:
            profile = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(profile, dict):
                profiles[profile.get("name", path.stem)] = profile
        except (OSError, ValueError):
            continue
    return profiles


def read_slice_metrics(path: Path) -> dict:
    metrics = {}
    with ZipFile(path) as archive:
        gcodes = [name for name in archive.namelist() if name.endswith(".gcode")]
        if not gcodes:
            raise ValueError("Slicer output contains no embedded G-code.")
        text = archive.read(gcodes[0]).decode("utf-8", errors="replace")
        time = re.search(
            r";\s*(?:total estimated time|estimated printing time[^:=]*)\s*[:=]\s*([^;\r\n]+)", text
        ) or re.search(r";\s*model printing time\s*[:=]\s*([^;\r\n]+)", text)
        grams = re.search(r";\s*(?:total )?filament (?:used|weight)\s*\[g\]\s*[:=]\s*([\d.]+)", text)
        if time and len(gcodes) == 1:
            metrics["time"] = time.group(1).strip()
        if grams and len(gcodes) == 1:
            metrics["filament_g"] = float(grams.group(1))
        metrics["gcode_files"] = len(gcodes)
        metrics["metrics_scope"] = "single_plate" if len(gcodes) == 1 else "multiple_plates_no_totals"
        model = ET.fromstring(archive.read("3D/3dmodel.model"))
        application = next((node.text for node in model if node.attrib.get("name") == "Application"), None)
        if application:
            metrics["slicer_version"] = application
    return metrics


def slice_model(job: dict) -> dict:
    spec = job["spec"]
    result = {"status": "unavailable"}
    binary = executable()
    if job["report"]["status"] == "failed":
        result["detail"] = "Resolve failed geometry checks before slicing."
    elif not binary:
        result["detail"] = "No local Bambu Studio executable was found."
    elif spec["printer"] != "bambu-a1":
        result["detail"] = "K1C slicing requires an exact K1C profile and a separate OrcaSlicer adapter."
    elif spec["material"] == "ABS":
        result["detail"] = "ABS on the open A1 is not approved by this demonstration workflow."
    else:
        directory = job_directory(job["id"])
        profile_directory = binary.parent / "resources" / "profiles" / "BBL"
        try:
            profiles = preset_index(profile_directory)
            nozzle = f"{spec['nozzle']:g}"
            machine_name = f"Bambu Lab A1 {nozzle} nozzle"
            process_name = {
                "0.2": "0.10mm Standard @BBL A1 0.2 nozzle",
                "0.4": "0.20mm Standard @BBL A1",
                "0.6": "0.30mm Standard @BBL A1 0.6 nozzle",
                "0.8": "0.40mm Standard @BBL A1 0.8 nozzle",
            }[nozzle]
            filament_name = f"Generic {spec['material']} @BBL A1"
            if nozzle == "0.2":
                filament_name += " 0.2 nozzle"
            names = [machine_name, process_name, filament_name]
            paths = []
            for kind, name in zip(("machine", "process", "filament"), names, strict=True):
                profile = resolve_profile(name, profiles)
                if kind == "machine" and profile.get("printer_model") != "Bambu Lab A1":
                    raise ValueError("Machine profile does not match Bambu Lab A1.")
                path = directory / f"slicer-{kind}.json"
                path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
                paths.append(path)
            output = directory / "sliced.3mf"
            output.unlink(missing_ok=True)
            command = [
                str(binary),
                "--debug",
                "2",
                "--arrange",
                "1",
                "--load-settings",
                f"{paths[0]};{paths[1]}",
                "--load-filaments",
                str(paths[2]),
                "--curr-bed-type",
                "Textured PEI Plate",
                "--slice",
                "0",
                "--outputdir",
                str(directory),
                "--export-3mf",
                "sliced.3mf",
                str(directory / "model.3mf"),
            ]
            with SLICE_LOCK:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=120,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            (directory / "slicer.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
            if completed.returncode != 0 or not output.is_file():
                raise ValueError(f"Slicer did not produce a validated output (exit {completed.returncode}).")
            metrics = read_slice_metrics(output)
            result = {
                "status": "completed",
                "printer_profile": machine_name,
                "process_profile": process_name,
                "filament_profile": filament_name,
                "engine": "Bambu Studio",
                "physical_controls": False,
                **metrics,
            }
            job["artifacts"]["sliced.3mf"] = {
                "url": f"/api/jobs/{job['id']}/files/sliced.3mf",
                "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            result = {"status": "failed", "detail": str(error)}
    job["slicer"] = result
    save_job(job)
    (job_directory(job["id"]) / "report.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job
