"""API request models."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from emberline.regions import get_region
from emberline.science.grid import GridSpec
from emberline.science.quality import QualityPolicy

Metric = Literal["frp_sum_mw", "active_1km", "det_count"]
ModelChoice = Literal["auto", "huber", "theilsen", "quantile", "isotonic"]


class AnalyzeRequest(BaseModel):
    """Exactly one of `bbox`, `geojson` or `region_id` selects the area."""

    bbox: tuple[float, float, float, float] | None = Field(
        default=None, description="west, south, east, north in degrees"
    )
    geojson: dict[str, Any] | None = Field(
        default=None, description="Polygon or MultiPolygon geometry, Feature or FeatureCollection"
    )
    region_id: str | None = Field(default=None, description="id of a curated preset")
    start: date
    end: date
    quality_policy: QualityPolicy = Field(default_factory=QualityPolicy)
    grid: GridSpec = Field(default_factory=GridSpec)
    metric: Metric = "frp_sum_mw"
    model: ModelChoice = "auto"
    synthetic: bool = Field(default=False, description="use SYNTHETIC development data")

    @model_validator(mode="after")
    def _one_area(self) -> AnalyzeRequest:
        given = [x for x in (self.bbox, self.geojson, self.region_id) if x is not None]
        if len(given) != 1:
            raise ValueError("give exactly one of bbox, geojson or region_id")
        if self.region_id is not None:
            try:
                get_region(self.region_id)
            except KeyError as exc:
                raise ValueError(f"unknown region_id {self.region_id!r}") from exc
        return self


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued | running | done | error
    stage: str | None = None
    error: str | None = None
    cached: bool = False
