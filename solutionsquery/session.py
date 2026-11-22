from __future__ import annotations

import os
from typing import List

from .bid import Bid
from .spiral import SpiralResult


def _bid_section(index: int, bid: Bid) -> str:
    lines = [f"### Bid {index} — {bid.persona.name}"]
    if not bid.ok:
        lines.append(f"\nFAILED: {bid.error}")
        return "\n".join(lines)
    lines += [
        "",
        f"- Title: {bid.title or '(untitled)'}",
        f"- Effort: {bid.effort or 'n/a'}",
        f"- Summary: {bid.summary or '(none)'}",
    ]
    if bid.approach:
        lines.append("- Approach:")
        lines += [f"  - {step}" for step in bid.approach]
    if bid.pros:
        lines.append("- Pros:")
        lines += [f"  - {p}" for p in bid.pros]
    if bid.cons:
        lines.append("- Cons:")
        lines += [f"  - {c}" for c in bid.cons]
    lines += ["", "Raw reply:", "", "```", bid.raw, "```"]
    return "\n".join(lines)


def save_session(
    project_dir: str,
    need: str,
    bids: List[Bid],
    winner_index: int,
    spiral: SpiralResult,
) -> str:
    lines = [
        "# solutionsquery session",
        "",
        "## Need",
        "",
        need,
        "",
        "## Bids",
        "",
    ]
    for i, bid in enumerate(bids, 1):
        marker = " (WINNER)" if i == winner_index + 1 else ""
        lines.append(f"{i}. {bid.persona.name}{marker}")
    lines.append("")
    for i, bid in enumerate(bids, 1):
        lines.append(_bid_section(i, bid))
        lines.append("")
    lines += [
        "## Spiral",
        "",
        f"Winner: {bids[winner_index].persona.name}",
        f"Iterations: {spiral.iterations}",
        f"Project dir: {spiral.project_dir}",
        "",
        "### Files",
        "",
    ]
    lines += [f"- {p}" for p in spiral.files] or ["- (none)"]
    lines += ["", "### Iterations", ""]
    for step in spiral.steps:
        lines += [
            f"#### Iteration {step.iteration} — status: {step.status}",
            "",
            "```",
            step.raw,
            "```",
            "",
        ]
        if step.files_written:
            lines.append("Files written: " + ", ".join(f"`{p}`" for p in step.files_written))
            lines.append("")
    lines += ["### Final", "", "```", spiral.final_text, "```", ""]
    path = os.path.join(project_dir, "SESSION.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path
