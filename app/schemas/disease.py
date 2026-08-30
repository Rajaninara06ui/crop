from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class DiseaseDetectionResponse(BaseModel):
    crop_name: str = "Tomato"
    disease_name: str = "Tomato Early Blight"
    crop: Optional[str] = "Tomato"
    possible_disease: Optional[str] = "Tomato Early Blight"
    confidence: float = 0.89
    symptoms: List[str] = []
    recommended_treatment: List[str] = []
    prevention_methods: List[str] = []
    prevention: List[str] = []
    severity: str = "medium"  # low | medium | high
    warning: Optional[str] = None
    is_demo: bool = False
