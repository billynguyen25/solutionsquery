# solutionsquery

Prompt AI agents with a problem you have and every agent will produce a different solution.

`solutionsquery` is a terminal "live bid" simulation built on that idea:

1. **Bidding phase** — you state a need. N agents (each with a distinct persona:
   architect, innovator, pragmatist, researcher, contrarian) bid concurrently,
   streaming their pitches live. Each bid is a structured proposal: title,
   summary, approach, pros, cons, effort.
2. **You pick the winner** — choose a bid by number (or `r` to re-bid).
3. **Spiral phase** — the winning agent iterates on implementation ("spiral"):
   each turn it critiques the project so far, plans the next step, and writes
   files (fenced `file` blocks) into the project directory, until it declares
   `STATUS: done`. The finished project — files plus a `SESSION.md` transcript —
   is returned on disk.

Zero third-party dependencies: Python 3.9+ standard library only. It talks to any
OpenAI-compatible `/chat/completions` endpoint.

## Setup

```bash
pip install -e .

export LLM_API_KEY=sk-...                      # required
export LLM_BASE_URL=https://api.openai.com/v1 # optional, default shown
export LLM_MODEL=gpt-4o-mini                   # optional, default shown
```

Works with OpenAI, Ollama (`LLM_BASE_URL=http://localhost:11434/v1`), vLLM, LM Studio, etc.

## Usage

```bash
solutionsquery "I need a CLI that tracks my reading list"
# or interactively:
solutionsquery
```

Then watch the bids stream in, pick the winner, and watch the spiral build the project.

Flags:

| Flag | Default | Meaning |
|---|---|---|
| `--agents N` | `SQ_AGENTS` or 3 | Number of bidding agents |
| `--pick N` | interactive | Auto-pick bid N (non-interactive runs) |
| `--max-iterations N` | `SQ_MAX_SPIRAL_ITERATIONS` or 8 | Spiral iteration cap |
| `--output-dir DIR` | `SQ_OUTPUT_DIR` or `./solutionsquery-output` | Where projects are written |
| `--model` / `--base-url` | env | Override model / endpoint |
| `--list-agents` | — | Show the personas |
| `--no-color` | — | Disable ANSI colors |

Output layout:

```
solutionsquery-output/projects/<timestamp>-<slug>/
  <files written by the winning agent>
  SESSION.md   # full transcript: need, all bids, spiral iterations, final summary
```

## Development

```bash
python -m unittest discover -s tests -v
```

Layout: `solutionsquery/llm.py` (streaming chat client), `agents.py` (personas +
prompts), `bid.py` (concurrent bidding), `spiral.py` (implementation loop),
`artifacts.py` (safe `file`-block parsing/writing), `session.py` (transcript),
`cli.py` (interactive flow).
