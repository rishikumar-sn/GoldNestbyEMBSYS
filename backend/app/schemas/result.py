from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class Segmentation(BaseModel):
    source: str
    score: float = Field(ge=0, le=1)
    refined_with_inspyrenet: bool = False


class Classification(BaseModel):
    label: str
    classification_score: float = Field(ge=0, le=1)
    gallery_match: bool
    gallery_similarity: float
    is_gold_jewelry: bool
    top_classes: list[dict]
    classification_source: str
    alternate_label: str | None = None
    needs_review: bool = False
    predicted_label: str | None = None
    confirmed_label: str | None = None
    confirmed_at: datetime | None = None
    confirmed: bool = False


class Instance(BaseModel):
    instance_id: str
    instance_number: int
    bbox: BBox
    segmentation: Segmentation
    classification: Classification
    artifacts: dict[str, str]


class AnalysisResult(BaseModel):
    job_id: str
    mode: str
    status: str = "completed"
    captured_at: datetime
    completed_at: datetime
    confirmed_at: datetime | None = None
    display_timezone: str
    physical_jewel_count: int
    type_counts: dict[str, int]
    count_confidence: float = Field(ge=0, le=1)
    instances: list[Instance]
    warnings: list[str]
    timings_ms: dict[str, float]
    model_versions: dict[str, str]
    artifacts: dict[str, str]
