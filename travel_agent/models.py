from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TripRequest(BaseModel):
    """Structured requirements kept in LangGraph state."""

    raw_request: str = ""
    origin: str = "Delhi"
    alternative_origins: list[str] = Field(default_factory=list)
    destination: str = "Goa"
    start_date: str = "2026-11-10"
    duration_days: int = Field(default=4, ge=1, le=30)
    travellers: int = Field(default=2, ge=1, le=12)
    budget: float = Field(default=60000, gt=0)
    currency: str = "INR"
    flight_class: Literal["economy", "business"] = "economy"
    flight_type: Literal["nonstop", "one_stop", "any"] = "any"
    max_layover_hours: float = Field(default=4, ge=0, le=24)
    stay_style: Literal["luxury", "hotel", "hostel", "room_share", "airbnb", "any"] = "hotel"
    activities: list[str] = Field(default_factory=lambda: ["beach", "food"])
    cuisines: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    date_flex_days: int = Field(default=0, ge=0, le=5)
    extension_days: int = Field(default=0, ge=0, le=3)

    @model_validator(mode="after")
    def normalize_lists(self) -> "TripRequest":
        self.alternative_origins = [x.strip() for x in self.alternative_origins if x.strip()]
        self.activities = [x.strip().lower() for x in self.activities if x.strip()]
        self.cuisines = [x.strip().lower() for x in self.cuisines if x.strip()]
        self.allergies = [x.strip().lower() for x in self.allergies if x.strip()]
        return self


class ApprovalDecision(BaseModel):
    approved: bool
    feedback: str = ""

