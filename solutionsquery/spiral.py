from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .agents import Persona, build_system_prompt
from .artifacts import parse_file_blocks, write_file_ops
from .bid import Bid
from .llm import ChatClient

STATUS_RE = re.compile(r"^\s*STATUS:\s*(done|in_progress)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass
class SpiralStep:
    iteration: int
    status: str
    raw: str
    files_written: List[str] = field(default_factory=list)


@dataclass
class SpiralResult:
    steps: List[SpiralStep]
    project_dir: str
    final_text: str

    @property
    def iterations(self) -> int:
        return len(self.steps)

    @property
    def files(self) -> List[str]:
        seen: List[str] = []
        for step in self.steps:
            for path in step.files_written:
                if path not in seen:
                    seen.append(path)
        return seen


def kickoff_user_prompt(need: str, bid: Bid) -> str:
    bid_doc = {
        "title": bid.title,
        "summary": bid.summary,
        "approach": bid.approach,
        "pros": bid.pros,
        "cons": bid.cons,
        "effort": bid.effort,
    }
    return (
        "The original need:\n\n"
        f"{need}\n\n"
        "The winning bid you must now implement:\n\n"
        f"```json\n{json.dumps(bid_doc, indent=2)}\n```\n\n"
        "Begin iteration 1 now."
    )


def next_iteration_user_prompt(iteration: int, max_iterations: int, files_written: List[str]) -> str:
    listing = "\n".join(f"- {p}" for p in files_written) or "- (none yet)"
    return (
        f"Iteration {iteration} of at most {max_iterations}. "
        f"Files written so far:\n{listing}\n\n"
        "Critique the current state, then continue the spiral."
    )


def parse_status(raw: str) -> str:
    match = STATUS_RE.search(raw)
    return match.group(1).lower() if match else "in_progress"


def run_spiral(
    client: ChatClient,
    persona: Persona,
    need: str,
    bid: Bid,
    project_dir: str,
    max_iterations: int,
    on_token: Optional[Callable[[Persona, str], None]] = None,
    temperature: float = 0.4,
) -> SpiralResult:
    os.makedirs(project_dir, exist_ok=True)
    messages = [
        {"role": "system", "content": build_system_prompt(persona)},
        {"role": "user", "content": kickoff_user_prompt(need, bid)},
    ]
    steps: List[SpiralStep] = []
    final_text = ""

    for iteration in range(1, max_iterations + 1):
        def token(text: str, p: Persona = persona) -> None:
            if on_token is not None:
                on_token(p, text)

        raw = client.chat(messages, temperature=temperature, on_token=token)
        messages.append({"role": "assistant", "content": raw})
        status = parse_status(raw)
        ops = parse_file_blocks(raw)
        written = []
        for op in ops:
            try:
                written.extend(write_file_ops(project_dir, [op]))
            except ValueError:
                raw += f"\n\n[HARNESS] Ignored unsafe file path: {op.path}"
                messages[-1] = {"role": "assistant", "content": raw}
        step = SpiralStep(iteration=iteration, status=status, raw=raw, files_written=written)
        steps.append(step)
        final_text = raw
        if status == "done" or iteration == max_iterations:
            break
        messages.append(
            {
                "role": "user",
                "content": next_iteration_user_prompt(iteration + 1, max_iterations, written),
            }
        )

    return SpiralResult(steps=steps, project_dir=project_dir, final_text=final_text)
