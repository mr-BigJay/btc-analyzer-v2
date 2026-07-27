"""Data pipeline stages (Ch.3).

Collection → Validation → Normalization → Quality → Storage → Analysis …
"""

from src.pipeline.normalization import DataNormalizer, NormalizedRecord, NormalizedSnapshot, normalize_symbol
from src.pipeline.quality import DataQualityGate, QualityAssessment
from src.pipeline.validation import DataValidator, ValidationReport

__all__ = [
    "DataValidator",
    "ValidationReport",
    "DataNormalizer",
    "NormalizedRecord",
    "NormalizedSnapshot",
    "normalize_symbol",
    "DataQualityGate",
    "QualityAssessment",
]
