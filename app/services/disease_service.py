from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DiseaseDetectionResult:
    crop: Optional[str]
    possible_disease: Optional[str]
    confidence: float
    symptoms: List[str] = field(default_factory=list)
    recommended_treatment: List[str] = field(default_factory=list)
    prevention: List[str] = field(default_factory=list)
    warning: Optional[str] = None
    is_demo: bool = False


class DiseaseDetectionModel(ABC):
    @abstractmethod
    def predict(self, image_bytes: bytes, crop_hint: Optional[str] = None) -> DiseaseDetectionResult:
        pass


class MockDiseaseModel(DiseaseDetectionModel):
    _DEMO_DISEASES = [
        DiseaseDetectionResult(
            crop="Tomato",
            possible_disease="Tomato Early Blight",
            confidence=0.89,
            symptoms=[
                "Dark concentric rings/spots on older leaves",
                "Yellowing around lesions",
                "Premature leaf drop",
            ],
            recommended_treatment=[
                "Remove and destroy severely affected leaves",
                "Apply copper-based fungicide or Mancozeb 75 WP (2g/L)",
                "Improve field ventilation through proper spacing",
            ],
            prevention=[
                "Avoid overhead irrigation",
                "Maintain proper plant spacing for air circulation",
                "Rotate crops - avoid solanaceous crops consecutively",
                "Use certified disease-free seeds",
            ],
            warning=None,
            is_demo=True,
        ),
        DiseaseDetectionResult(
            crop="Tomato",
            possible_disease="Tomato Late Blight",
            confidence=0.84,
            symptoms=[
                "Water-soaked dark lesions on leaves and stems",
                "White fuzzy fungal growth under leaves during high humidity",
                "Rapid browning and collapse of foliage",
            ],
            recommended_treatment=[
                "Apply metalaxyl + mancozeb (Ridomil MZ) at 2.5 g/L",
                "Remove and safely dispose of infected plants",
                "Avoid spraying during high winds to prevent spore spread",
            ],
            prevention=[
                "Use resistant cultivars",
                "Ensure excellent field drainage",
                "Apply preventative bio-fungicides like Trichoderma viride",
            ],
            warning=None,
            is_demo=True,
        ),
    ]

    def predict(self, image_bytes: bytes, crop_hint: Optional[str] = None) -> DiseaseDetectionResult:
        import hashlib
        h = int(hashlib.md5(image_bytes[:256]).hexdigest(), 16)
        result = self._DEMO_DISEASES[h % len(self._DEMO_DISEASES)]
        result.is_demo = True
        return result


class TrainedDiseaseModel(DiseaseDetectionModel):
    def __init__(self, model_path: str) -> None:
        self.model_path = Path(model_path)
        self._model = None
        self._class_names: List[str] = []
        self._load()

    def _load(self) -> None:
        try:
            import torch
            import json
            self._model = torch.load(str(self.model_path), map_location="cpu")
            self._model.eval()
            class_file = self.model_path.with_suffix(".json")
            if class_file.exists():
                with open(class_file) as f:
                    self._class_names = json.load(f)
            logger.info("Loaded disease model: %s", self.model_path)
        except Exception as exc:
            logger.error("Failed to load disease model: %s", exc)
            raise

    def predict(self, image_bytes: bytes, crop_hint: Optional[str] = None) -> DiseaseDetectionResult:
        import io
        import torch
        from PIL import Image
        import torchvision.transforms as transforms

        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = transform(img).unsqueeze(0)
        with torch.no_grad():
            outputs = self._model(tensor)
            probs = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probs, 1)
        conf = float(confidence.item())
        idx = predicted.item()
        disease_name = self._class_names[idx] if self._class_names else f"Class_{idx}"
        return DiseaseDetectionResult(
            crop=crop_hint or "Crop",
            possible_disease=disease_name,
            confidence=conf,
            symptoms=[],
            recommended_treatment=[],
            prevention=[],
            is_demo=False,
        )


class DiseaseService:
    def __init__(self) -> None:
        self.threshold = settings.DISEASE_CONFIDENCE_THRESHOLD
        self._model = self._load_model()

    def _load_model(self) -> DiseaseDetectionModel:
        if settings.MOCK_MODE or not settings.DISEASE_MODEL_PATH:
            logger.info("Disease service: using mock model.")
            return MockDiseaseModel()
        try:
            return TrainedDiseaseModel(settings.DISEASE_MODEL_PATH)
        except Exception:
            logger.warning("Real disease model failed to load; using mock.")
            return MockDiseaseModel()

    def detect(self, image_bytes: bytes, crop_hint: Optional[str] = None) -> DiseaseDetectionResult:
        result = self._model.predict(image_bytes, crop_hint=crop_hint)
        if result.confidence < self.threshold:
            result.warning = (
                f"The AI is not fully confident about this result (confidence: {result.confidence:.0%}). "
                "Please consult a qualified agricultural expert or your local KVK for reliable diagnosis."
            )
        else:
            result.warning = "This AI result is advisory. Consult a qualified agricultural expert for serious crop damage."
        return result
