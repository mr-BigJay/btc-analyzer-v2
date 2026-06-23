import json
from dataclasses import asdict, is_dataclass
from enum import Enum

from src.analyzer.models import OverviewAnalysis


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def analysis_to_dict(analysis: OverviewAnalysis) -> dict:
    return json.loads(json.dumps(analysis, cls=EnhancedJSONEncoder))


def analysis_to_json(analysis: OverviewAnalysis) -> str:
    return json.dumps(analysis, cls=EnhancedJSONEncoder, ensure_ascii=False)
