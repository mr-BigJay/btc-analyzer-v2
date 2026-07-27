"""Analysis layers package (Ch.6 §6.4)."""

from src.analysis.layers.futures import FuturesLayer
from src.analysis.layers.liquidity import LiquidityLayer
from src.analysis.layers.options import OptionsLayer
from src.analysis.layers.patterns import PatternLayer
from src.analysis.layers.spot import SpotLayer
from src.analysis.layers.structure import StructureLayer
from src.analysis.layers.technical import TechnicalLayer
from src.analysis.layers.volatility import VolatilityLayer

ALL_LAYERS = [
    SpotLayer,
    FuturesLayer,
    OptionsLayer,
    TechnicalLayer,
    StructureLayer,
    PatternLayer,
    VolatilityLayer,
    LiquidityLayer,
]

__all__ = [
    "SpotLayer",
    "FuturesLayer",
    "OptionsLayer",
    "TechnicalLayer",
    "StructureLayer",
    "PatternLayer",
    "VolatilityLayer",
    "LiquidityLayer",
    "ALL_LAYERS",
]
