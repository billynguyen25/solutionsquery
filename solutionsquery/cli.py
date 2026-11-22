from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from dataclasses import replace
from datetime import datetime
from typing import List, Optional

from .agents import PERSONAS, Persona
from .bid import Bid, run_bidding
from .config import Config
from .llm import ChatClient, LLMError
from .session import save_session
from .spiral import run_spiral

RESET = "\033[0m"
BOLD = "\033[1m"


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "project"


class LivePrinter:
    """Thread-safe live output: streamed tokens are tagged with the speaking agent."""

    def __init__(self, use_color: bool = True) -> None:
        self.use_color = use_color
        self._lock = threading.Lock()
        self._current: Optional[str] = None

    def agent_token(self, persona: Persona, text: str) -> None:
        with self._lock:
            if self._current != persona.name:
                if self.use_color:
                    prefix = f"{persona.color}{BOLD}[{persona.name}]{RESET}"
                else:
                    prefix = f"[{persona.name}]"
                sys.stdout.write(f"\n{prefix} ")
                self._current = persona.name
            sys.stdout.write(text)
            sys.stdout.flush()

    def line(self, text: str = "") -> None:
        with self._lock:
            self._current = None
            print(text, flush=True)

    def header(self, text: str) -> None:
        bar = "─" * max(0, 64 - len(text))
        self.line()
        self.line(f"{BOLD}── {text} {bar}{RESET}" if self.use_color else f"-- {text} {bar}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solutionsquery",
        description=(
            "Live bid simulation: multiple AI agents each propose a different solution "
            "to your need, you pick the winner, and that agent spirals until the "
            "finished project is written to disk."
        ),
    )
    parser.add_argument("need", nargs="?", help="The need/problem to solve (prompted if omitted).")
    parser.add_argument("--agents", type=int, default=None, help="Number of bidding agents (default: SQ_AGENTS or 3).")
    parser.add_argument("--pick", type=int, default=None, help="Auto-pick this bid number instead of asking interactively.")
    parser.add_argument("--max-iterations", type=int, default=None, help="Spiral iteration cap (default: SQ_MAX_SPIRAL_ITERATIONS or 8).")
    parser.add_argument("--output-dir", default=None, help="Where projects are written (default: SQ_OUTPUT_DIR or ./solutionsquery-output).")
    parser.add_argument("--model", default=None, help="Override LLM_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override LLM_BASE_URL.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors.")
    parser.add_argument("--list-agents", action="store_true", help="List the bidding personas and exit.")
    return parser


def select_personas(count: int) -> List[Persona]:
    base = len(PERSONAS)
    personas: List[Persona] = []
    for i in range(max(1, count)):
        persona = PERSONAS[i % base]
        if i >= base:
            persona = replace(persona, name=f"{persona.name}#{i // base + 1}")
        personas.append(persona)
    return personas


def print_bid_card(printer: LivePrinter, number: int, bid: Bid) -> None:
    if not bid.ok:
        printer.line(f"{number}. {bid.persona.name} — FAILED: {bid.error}")
        return
    printer.line(f"{number}. {bid.persona.name} — {bid.title or '(untitled)'}  [{bid.effort or 'n/a'}, {bid.elapsed:.1f}s]")
    if bid.summary:
        printer.line(f"   {bid.summary}")
    if bid.approach:
        printer.line("   Approach:")
        for step in bid.approach:
            printer.line(f"     - {step}")
    if bid.pros:
        printer.line(f"   Pros: {', '.join(bid.pros)}")
    if bid.cons:
        printer.line(f"   Cons: {', '.join(bid.cons)}")
    printer.line()


def choose_winner(printer: LivePrinter, bids: List[Bid], pick: Optional[int], client: ChatClient, need: str, on_agent_token) -> tuple:
    """Return (bids, winner_index). Supports 'r' to re-bid interactively."""
    while True:
        if pick is not None:
            if not 1 <= pick <= len(bids):
                printer.line(f"--pick must be between 1 and {len(bids)}.")
                return bids, None
            return bids, pick - 1
        answer = input(f"Pick the winning bid [1-{len(bids)}, 'r' to re-bid]: ").strip().lower()
        if answer == "r":
            printer.header("Re-bidding...")
            bids = run_bidding(client, [b.persona for b in bids], need, on_agent_token=on_agent_token)
            for i, b in enumerate(bids, 1):
                print_bid_card(printer, i, b)
            pick = None
            continue
        if answer.isdigit() and 1 <= int(answer) <= len(bids):
            return bids, int(answer) - 1
        printer.line("Invalid choice.")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    config = Config.from_env()
    if args.model:
        config.model = args.model
    if args.base_url:
        config.base_url = args.base_url
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.agents:
        config.num_agents = args.agents
    if args.max_iterations:
        config.max_spiral_iterations = args.max_iterations

    printer = LivePrinter(use_color=not args.no_color)

    if args.list_agents:
        for i, persona in enumerate(PERSONAS, 1):
            printer.line(f"{i}. {persona.name} — {persona.style}")
        return 0

    need = args.need or input("What do you need solved? ").strip()
    if not need:
        printer.line("A need is required.")
        return 2

    config.require_api_key()
    client = ChatClient(config.api_key, config.base_url, config.model, timeout=config.timeout)
    personas = select_personas(config.num_agents)

    try:
        printer.header(f"Bidding phase — {len(personas)} agents on: {need!r}")
        bids = run_bidding(client, personas, need, on_agent_token=printer.agent_token)
        printer.line()
        if any(not b.ok for b in bids):
            printer.line("Some bids failed; see below.")
        for i, bid in enumerate(bids, 1):
            print_bid_card(printer, i, bid)

        bids, winner_index = choose_winner(printer, bids, args.pick, client, need, printer.agent_token)
        if winner_index is None:
            return 2
        winner = bids[winner_index]
        if not winner.ok:
            printer.line("Cannot spiral on a failed bid. Re-run or pick another.")
            return 2

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        project_dir = os.path.join(
            config.output_dir, "projects", f"{timestamp}-{slugify(need)}"
        )
        printer.header(
            f"Spiral phase — {winner.persona.name} implementing "
            f"'{winner.title or 'the winning bid'}'"
        )
        printer.line(f"Project dir: {project_dir}")
        printer.line(f"Iteration cap: {config.max_spiral_iterations}")

        result = run_spiral(
            client,
            winner.persona,
            need,
            winner,
            project_dir,
            config.max_spiral_iterations,
            on_token=printer.agent_token,
        )
        printer.line()
        printer.header("Finished project")
        printer.line(f"Iterations: {result.iterations}")
        printer.line("Files:")
        for path in result.files:
            printer.line(f"  {path}")
        printer.line()
        printer.line(result.final_text.strip())
        session_path = save_session(project_dir, need, bids, winner_index, result)
        printer.line()
        printer.line(f"Project:  {os.path.abspath(project_dir)}")
        printer.line(f"Session:  {os.path.abspath(session_path)}")
        return 0
    except LLMError as exc:
        printer.line(f"LLM error: {exc}")
        return 1
    except KeyboardInterrupt:
        printer.line("\nInterrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
