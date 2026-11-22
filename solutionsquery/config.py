from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    num_agents: int = 3
    max_spiral_iterations: int = 8
    output_dir: str = "solutionsquery-output"
    timeout: int = 180

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            api_key=os.environ.get("LLM_API_KEY", ""),
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            num_agents=_int_env("SQ_AGENTS", 3),
            max_spiral_iterations=_int_env("SQ_MAX_SPIRAL_ITERATIONS", 8),
            output_dir=os.environ.get("SQ_OUTPUT_DIR", "solutionsquery-output"),
            timeout=_int_env("SQ_TIMEOUT", 180),
        )

    def require_api_key(self) -> None:
        if not self.api_key:
            raise SystemExit(
                "LLM_API_KEY is not set. Export LLM_API_KEY (and optionally "
                "LLM_BASE_URL / LLM_MODEL) pointing at any OpenAI-compatible "
                "chat completions endpoint."
            )


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default
