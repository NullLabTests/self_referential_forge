# Self-Referential Forge

**Darwin-style self-referential evolution — the forge that modifies its own source code to improve itself.**

Built atop the lineage: [`grounded_evolution`](https://github.com/NullLabTests/grounded_evolution) → [`grounded_agent_forge`](https://github.com/NullLabTests/grounded_agent_forge) → **`self_referential_forge`**.

---

## What This Is

A research platform for **execution-grounded agent blueprint evolution**. The forge writes, mutates, evaluates, and archives its own Python source — a closed-loop Darwinian process where the code that runs the evolution is itself the evolving population.

- **Self-Modification:** AST-level mutation operators (`insert_code`, `rewrite_function`, `add_parameter`, `swap_condition`, `duplicate_component`) rewrite the forge's own source at runtime.
- **Meta-Evolution:** A second-order loop adjusts operator selection weights, mutation rates, and crossover rates based on observed fitness deltas.
- **Multi-Objective Fitness:** Components are scored on correctness, complexity, novelty, and coverage — no external oracle required.
- **Safety Guardrails:** A safety validator blocks destructive patterns (`exec`/`eval`, dangerous imports, filesystem bombs).
- **Full Archival:** Every generation snapshot is persisted to disk for replay and analysis.
- **Live Dashboard:** FastAPI-based real-time visualization of fitness curves, operator usage, and population stats.

Built using **DeepSeek V4** as the underlying model for all LLM-driven operations.

---

## Quick Start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env with your LLM_API_KEY

# 3. Run the evolution loop
./run_forge.sh

# 4. (Optional) Launch dashboard alongside evolution
DASHBOARD=true ./run_forge.sh
```

## Project Structure

```
self_referential_forge/
├── forge/
│   ├── orchestrator.py      # Main evolution loop coordinator
│   └── self_modifier.py     # AST-level self-mutation engine
├── meta_evolution/
│   └── meta_evolver.py      # Second-order strategy adaptation
├── evaluators/
│   └── evaluator.py         # Multi-objective fitness evaluator
├── safety/
│   ├── safety_validator.py  # Mutation guardrails
│   └── safety_rules.json    # Configurable safety rules
├── archive/
│   └── archivist.py         # Snapshot persistence
├── benchmarks/
│   └── benchmark_runner.py  # Internal benchmark suite
├── dashboard/
│   └── main.py              # FastAPI visualization server
├── pyproject.toml           # Project metadata & dependencies
└── run_forge.sh             # Bash automation wrapper
```

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Meta-Evolver (second-order)                              │
│  ── Adjusts operator weights based on fitness deltas      │
│  ── Injects novelty on convergence                         │
└────────────────────┬───────────────────────────────────────┘
                     │ selects operator
                     ▼
┌────────────────────────────────────────────────────────────┐
│  Self-Modifier (AST mutation)                              │
│  ── insert_code, rewrite_function, add_parameter          │
│  ── swap_condition, duplicate_component                    │
└────────────────────┬───────────────────────────────────────┘
                     │ produces mutated source
                     ▼
┌────────────────────────────────────────────────────────────┐
│  Evaluator (multi-objective)                               │
│  ── correctness, complexity, novelty, coverage             │
└────────────────────┬───────────────────────────────────────┘
                     │ fitness scores
                     ▼
┌────────────────────────────────────────────────────────────┐
│  Safety Validator ── guardrails pass/fail                  │
└────────────────────┬───────────────────────────────────────┘
                     │ safe mutations
                     ▼
┌────────────────────────────────────────────────────────────┐
│  Archivist ── persist snapshot to disk                     │
└────────────────────────────────────────────────────────────┘
```

## Lineage

| Repository | Description |
|---|---|
| [grounded_evolution](https://github.com/NullLabTests/grounded_evolution) | First-generation evolution loop with Docker sandbox evaluation |
| [grounded_agent_forge](https://github.com/NullLabTests/grounded_agent_forge) | Multi-objective fitness, meta-evolution, self-tuning mutation |
| **self_referential_forge** (this) | Full self-modification — the forge rewrites its own source |

## License

MIT — see [LICENSE](LICENSE).
