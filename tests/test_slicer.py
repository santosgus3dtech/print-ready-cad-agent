from zipfile import ZipFile

import pytest

from printready.slicer import read_slice_metrics


def test_actual_bambu_header_style_and_version(tmp_path):
    target = tmp_path / "slice.3mf"
    with ZipFile(target, "w") as archive:
        archive.writestr(
            "Metadata/plate_1.gcode",
            "; model printing time: 1h 23m 15s; "
            "total estimated time: 1h 29m 32s\n; total filament weight [g] : 39.92\n",
        )
        archive.writestr(
            "3D/3dmodel.model", '<model><metadata name="Application">BambuStudio-test</metadata></model>'
        )
    result = read_slice_metrics(target)
    assert result["time"] == "1h 29m 32s"
    assert result["filament_g"] == 39.92
    assert result["slicer_version"] == "BambuStudio-test"


def test_geometry_only_3mf_is_not_a_slice(tmp_path):
    target = tmp_path / "geometry.3mf"
    with ZipFile(target, "w") as archive:
        archive.writestr("3D/3dmodel.model", "<model/>")
    with pytest.raises(ValueError, match="no embedded G-code"):
        read_slice_metrics(target)


def test_multiple_plates_do_not_report_first_plate_as_total(tmp_path):
    target = tmp_path / "multiple.3mf"
    with ZipFile(target, "w") as archive:
        for number in (1, 2):
            archive.writestr(
                f"Metadata/plate_{number}.gcode",
                "; total estimated time: 10m\n; total filament weight [g] : 5.0\n",
            )
        archive.writestr("3D/3dmodel.model", "<model/>")
    result = read_slice_metrics(target)
    assert result["gcode_files"] == 2
    assert result["metrics_scope"] == "multiple_plates_no_totals"
    assert "time" not in result
    assert "filament_g" not in result
