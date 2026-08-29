from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class DiseaseDetectionResponse(BaseModel):
    crop: Optional[str] = None
    possible_disease: Optional[str] = None
    confidence: float
    symptoms: List[str] = []
    recommended_treatment: List[str] = []
    prevention: List[str] = []
    warning: Optional[str] = None
    is_demo: bool = False
