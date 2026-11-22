"""solutionsquery — live multi-agent solution bidding with a spiral build phase."""

__version__ = "0.1.0"

from .agents import PERSONAS, Persona
from .bid import Bid, run_bidding
from .config import Config
from .llm import ChatClient, LLMError
from .spiral import SpiralResult, run_spiral

__all__ = [
    "PERSONAS",
    "Persona",
    "Bid",
    "run_bidding",
    "Config",
    "ChatClient",
    "LLMError",
    "SpiralResult",
    "run_spiral",
    "__version__",
]
