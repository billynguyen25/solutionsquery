from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .agents import Persona, bid_system_prompt
from .llm import ChatClient

JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass
class Bid:
    persona: Persona
    raw: str
    elapsed: float = 0.0
    title: str = ""
    summary: str = ""
    approach: List[str] = field(default_factory=list)
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    effort: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


def parse_bid(raw: str) -> Dict:
    match = JSON_BLOCK_RE.search(raw)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    stripped = JSON_BLOCK_RE.sub("", raw)
    first_line = next((ln.strip() for ln in stripped.splitlines() if ln.strip()), "")
    return {"title": first_line[:80], "summary": raw.strip()}


def bid_user_prompt(need: str) -> str:
    return f"The user's need:\n\n{need}\n"


def _as_str_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def run_bidding(
    client: ChatClient,
    personas: List[Persona],
    need: str,
    on_agent_token: Optional[Callable[[Persona, str], None]] = None,
) -> List[Bid]:
    bids: List[Optional[Bid]] = [None] * len(personas)

    def work(index: int, persona: Persona) -> None:
        messages = [
            {"role": "system", "content": bid_system_prompt(persona)},
            {"role": "user", "content": bid_user_prompt(need)},
        ]

        def token(text: str, p: Persona = persona) -> None:
            if on_agent_token is not None:
                on_agent_token(p, text)

        started = time.monotonic()
        try:
            raw = client.chat(messages, temperature=0.9, on_token=token)
            data = parse_bid(raw)
            bids[index] = Bid(
                persona=persona,
                raw=raw,
                elapsed=time.monotonic() - started,
                title=str(data.get("title", "")).strip(),
                summary=str(data.get("summary", "")).strip(),
                approach=_as_str_list(data.get("approach")),
                pros=_as_str_list(data.get("pros")),
                cons=_as_str_list(data.get("cons")),
                effort=str(data.get("effort", "")).strip(),
            )
        except Exception as exc:
            bids[index] = Bid(
                persona=persona,
                raw="",
                elapsed=time.monotonic() - started,
                error=str(exc),
            )

    with ThreadPoolExecutor(max_workers=max(1, len(personas))) as pool:
        futures = [pool.submit(work, i, p) for i, p in enumerate(personas)]
        for future in futures:
            future.result()

    return [b for b in bids if b is not None]
