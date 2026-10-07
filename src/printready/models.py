from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    width: float = Field(default=80, ge=20, le=400)
    depth: float = Field(default=55, ge=20, le=400)
    height: float = Field(default=28, ge=8, le=400)
    wall: float = Field(default=2.4, ge=0.8, le=12)
    clearance: float = Field(default=0.3, ge=0.05, le=2)
    hole_diameter: float = Field(default=3.2, ge=2, le=10)
    outer_diameter: float = Field(default=60, ge=20, le=300)
    inner_diameter: float = Field(default=32, ge=4, le=280)
    base_thickness: float = Field(default=4, ge=1.2, le=20)


class DesignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    template: Literal["enclosure", "bracket", "adapter"] = "enclosure"
    printer: Literal["bambu-a1", "creality-k1c"] = "bambu-a1"
    material: Literal["PLA", "PETG", "ABS"] = "PLA"
    nozzle: Literal[0.2, 0.4, 0.6, 0.8] = 0.4
    parameters: Parameters = Field(default_factory=Parameters)

    @model_validator(mode="after")
    def manufacturable_parameters(self):
        p = self.parameters
        if self.template == "enclosure":
            boss_radius = max(p.wall * 1.4, p.hole_diameter / 2 + p.wall)
            if min(p.width, p.depth) <= 2 * p.wall + 4 * boss_radius + 2:
                raise ValueError("Enclosure is too small for its walls and screw bosses.")
            if p.height <= p.wall * 2 + p.clearance:
                raise ValueError("Height must leave an internal cavity above the floor.")
            if p.clearance >= p.wall:
                raise ValueError("Lid clearance must be smaller than wall thickness.")
        elif self.template == "bracket":
            if p.wall * 3 >= min(p.width, p.depth, p.height):
                raise ValueError("Bracket dimensions must exceed three wall thicknesses.")
            if p.hole_diameter + 2 * p.wall >= min(p.width, p.depth, p.height):
                raise ValueError("Mounting holes need enough surrounding material.")
        elif p.inner_diameter + 4 * p.wall >= p.outer_diameter:
            raise ValueError("Adapter flange needs room around the bore and neck.")
        elif p.height <= p.base_thickness:
            raise ValueError("Adapter height must exceed its flange thickness.")
        return self


class BriefRequest(BaseModel):
    brief: str = Field(min_length=1, max_length=1500)
    spec: DesignSpec = Field(default_factory=DesignSpec)


PROFILES = {
    "bambu-a1": {"name": "Bambu Lab A1", "build_volume": [256, 256, 256]},
    "creality-k1c": {"name": "Creality K1C", "build_volume": [220, 220, 250]},
}
