<div align="center">

# 🧬 Self-Referential Forge

**Darwin-style evolution of the forge's own components — mutation operators, evaluators, safety guards, and meta-strategies evolve through self-modification.**

[![Status: Active](https://img.shields.io/badge/status-active-success?style=flat-square&logo=github&logoColor=white)](https://github.com/NullLabTests/grounded_agent_forge/tree/main/self_referential_forge)
[![License: MIT](https://img.shields.io/badge/License-MIT-67ac09?style=flat-square&logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-007ec6?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Dashboard-009688?style=flat-square&logo=fastapi&logoColor=white)](#dashboard)
[![Research](https://img.shields.io/badge/Research-Self--Referential%20Evolution-ff6b6b?style=flat-square&logo=arxiv&logoColor=white)](#research-context)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-8b5cf6?style=flat-square&logo=github&logoColor=white)](CONTRIBUTING.md)

[![Built With](https://img.shields.io/badge/Built%20With-DeepSeek%20V4-0A192F?style=flat-square&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgZmlsbD0ibm9uZSIgdmlld0JveD0iMCAwIDY0IDY0Ij48cGF0aCBmaWxsPSIjZmZmIiBkPSJNMzIgMkMxNS40MzEgMiAyIDE1LjQzMSAyIDMyczEzLjQzMSAzMCAzMCAzMCAzMC0xMy40MzEgMzAtMzBTNDguNTY5IDIgMzIgMnptMCA1NkMxNy42NjMgNTggNiA0Ni4zMzcgNiAzMnMxMS42NjMtMjYgMjYtMjYgMjYgMTEuNjYzIDI2IDI2LTExLjY2MyAyNi0yNiAyNnoiLz48cGF0aCBmaWxsPSIjZmZmIiBkPSJNMjIgMjNoMnYxOGgtMnpNMzYgMjNoMnYxOGgtMnoiLz48cGF0aCBmaWxsPSIjZmZmIiBkPSJNMjYgMjhoMTJ2MkgyNnpNMjYgMzJoMTJ2MkgyNnoiLz48L3N2Zz4=&label=AI%20Model)](https://deepseek.com)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-6C2EB5?style=flat-square&logo=linux&logoColor=white)](#setup)
[![Code Style](https://img.shields.io/badge/Code%20Style-ruff-261230?style=flat-square&logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)
[![Stars](https://img.shields.io/github/stars/NullLabTests/grounded_agent_forge?style=flat-square&logo=github&logoColor=white&color=gold)](https://github.com/NullLabTests/grounded_agent_forge)
[![Last Commit](https://img.shields.io/github/last-commit/NullLabTests/grounded_agent_forge?style=flat-square&logo=github&logoColor=white)](https://github.com/NullLabTests/grounded_agent_forge)

---

**Navigation** · [Overview](#overview) · [Project Lineage](#project-lineage) · [Self-Referential Approach](#self-referential-approach) · [Architecture](#architecture) · [Quick Start](#quick-start) · [Modules](#modules) · [Safety](#safety) · [Research](#research-context)

---

</div>

## ✦ Overview

The Self-Referential Forge is the **third generation** of evolutionary optimization at NullLabTests. Where its predecessors evolved prompts and then agent blueprints, this forge **evolves its own source code** — a Darwin-style self-referential loop where the genetic operators, evaluators, safety guards, and meta-strategies are themselves subject to mutation, selection, and inheritance.

### What Makes This Different

| Feature | Impact |
|---------|--------|
| 🧬 **Self-Modifying Operators** | Mutation operators rewrite the forge's own Python AST — inserting, deleting, and restructuring code at runtime |
| 🔄 **Second-Order Evolution** | The meta-evolver tracks which self-mutations improve evolution quality and adjusts selection pressure accordingly |
| 🛡️ **Safety-Guarded Mutation** | Every self-modification passes through a safety validator that blocks dangerous patterns (eval, exec, destructive I/O) |
| 📊 **Self-Evaluation** | Forge components are scored on syntax validity, code complexity, safety compliance, modular cohesion, and style consistency |
| 🗃️ **Immutable Archive** | Every evolution snapshot is gzip-compressed and stored, enabling full rollback and trajectory analysis |
| 🎛️ **Human-in-the-Loop** | Optional manual approval gate for every self-mutation |

### The Self-Referential Loop

```
   ┌─────────────────────────────────────────────────────────┐
   │  🧬 Forge Source Code (the entire forge package)         │
   │    ├── forge/orchestrator.py                             │
   │    ├── forge/self_modifier.py   ◄── MUTATION TARGET      │
   │    ├── evaluators/evaluator.py  ◄── MUTATION TARGET      │
   │    ├── safety/safety_validator.py ◄── MUTATION TARGET    │
   │    └── meta_evolution/*.py      ◄── MUTATION TARGET      │
   └────────────────────┬────────────────────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────────────────────┐
   │  🔧 SelfModifier applies genetic operators               │
   │    ├── insert_code     — inject logging/branching        │
   │    ├── rewrite_function — replace body with pass          │
   │    ├── add_parameter   — add optional param to function   │
   │    ├── swap_condition  — negate if-condition              │
   │    └── duplicate_component — clone class/func             │
   └────────────────────┬────────────────────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────────────────────┐
   │  🛡️ SafetyValidator checks mutation                      │
   │    └── Blocks: eval, exec, os.system, destructives       │
   └────────────────────┬────────────────────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────────────────────┐
   │  📊 SelfEvaluator scores the mutated component           │
   │    ├── syntax_validity   (AST parse)                     │
   │    ├── code_complexity   (node count, depth)             │
   │    ├── safety_compliance (dangerous patterns)            │
   │    ├── modular_cohesion  (imports, structure)            │
   │    └── style_consistency (indent, type hints)            │
   └────────────────────┬────────────────────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────────────────────┐
   │  🧠 MetaEvolver updates operator weights                 │
   │    ├── Positive delta → reinforce operator               │
   │    ├── Negative delta → penalize operator                │
   │    └── Stagnation → novelty boost                        │
   └────────────────────┬────────────────────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────────────────────┐
   │  🗃️ Archivist snapshots the state to disk                │
   └─────────────────────────────────────────────────────────┘
```

---

## 🧬 Project Lineage

```
┌──────────────────────────────────────────────────────────────────────┐
│                     self_referential_forge                             │
│                        (THIS PROJECT)                                  │
│  Evolves the forge's own source code — mutation operators,             │
│  evaluators, safety guards, and meta-strategies evolve through         │
│  self-modification. Second-order evolution loop with AST-level         │
│  mutations and safety-guarded self-modification.                       │
│                                                                         │
│  🧬 Self-modifying operators    🔄 Second-order meta-evolution          │
│  🛡️ Safety-guarded mutation     📊 Self-evaluation (6 dimensions)       │
│  🗃️ Immutable archive            🎛️ Human-in-the-loop optional          │
└──────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ evolves from · self-referential fork
┌──────────────────────────────────────────────────────────────────────┐
│                     grounded_agent_forge                               │
│  Evolves full agent blueprints (prompt + tools + memory + planning    │
│  + self-eval) in Docker sandbox with multi-objective fitness,         │
│  meta-evolution, and task specialization.                              │
│                                                                         │
│  🏗️ Agent-level evolution    📦 Docker sandboxed execution             │
│  🎯 8+ fitness dimensions    🔄 Self-tuning meta-evolution             │
│  📊 Real-time dashboard      🧩 Task specialization                    │
└──────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ builds on · evolves from
┌──────────────────────────────────────────────────────────────────────┐
│                      grounded_evolution                               │
│  Evolves text prompts with execution-grounded validation via AST       │
│  parse, pytest, and flake8. Two-loop system: lexical + grounded.      │
│                                                                         │
│  📝 203 evolution cycles    🏆 Best score: 39/80                       │
│  🔬 7 benchmark tasks       🔄 127 mutations + 76 crossovers           │
└──────────────────────────────────────────────────────────────────────┘
```

### Capability Comparison

| Capability | grounded_evolution | grounded_agent_forge | 🚀 self_referential_forge |
|------------|:---:|:---:|:---:|
| **Evolves text prompts** | ✅ | ✅ | ❌ |
| **Evolves agent blueprints** | ❌ | ✅ | ❌ |
| **Evolves its own source code** | ❌ | ❌ | ✅ |
| **AST-level self-mutation** | ❌ | ❌ | ✅ |
| **Safety-guarded modification** | ❌ | ❌ | ✅ |
| **Docker sandbox execution** | ❌ | ✅ | ❌ |
| **Multi-objective fitness** | ❌ | ✅ (8 dims) | ✅ (6 dims) |
| **Self-evaluation of components** | ❌ | ❌ | ✅ |
| **Second-order meta-evolution** | ❌ | ✅ | ✅ |
| **Novelty-driven exploration** | ❌ | ✅ | ✅ |
| **Immutable archive / rollback** | ❌ | ❌ | ✅ |
| **Human-in-the-loop mutations** | ❌ | ❌ | ✅ |
| **Real-time dashboard** | ❌ | ✅ | ✅ |
| **Auto-commit on improvement** | ✅ | ✅ | ✅ |

> **This project was built using DeepSeek V4 as the primary coding model.**

---

## 🔬 Self-Referential Approach

### Darwin-Style Evolution Applied to Software

The Self-Referential Forge applies Darwinian principles — variation, selection, and inheritance — not to biological organisms or even to generated prompts, but to **the forge's own implementation code**.

**Variation:** Each evolution cycle selects a champion component (the highest-fitness piece of forge source) and applies a random genetic operator: inserting code, rewriting function bodies, adding parameters, negating conditions, or duplicating components. These operators work directly on the Python AST.

**Selection:** The mutated component is scored across six fitness dimensions — syntax validity (does it parse?), code complexity (is it non-trivial?), safety compliance (no dangerous patterns?), modular cohesion (well-structured?), style consistency (clean code?), and test survival (do tests still pass?). The weighted sum determines the component's fitness.

**Inheritance:** High-fitness components remain in the population and serve as parents for future mutations. Low-fitness variants are pruned. The meta-evolver tracks which operators consistently produce fitness gains and adjusts selection weights accordingly — a second-order evolution where the *evolution strategy itself evolves*.

### Why Self-Referential?

Traditional evolutionary computation evolves solutions *within* a fixed framework (a genetic algorithm with hardcoded operators, fixed evaluation functions, static safety constraints). The self-referential forge removes these boundaries: the operators are mutatable, the evaluator is improvable, the safety rules are refinable.

This creates a system that can theoretically discover novel evolutionary strategies that a human designer would never have considered. The safety validator acts as the crucial guardrail — preventing the system from evolving destructive capabilities while still allowing creative exploration of the design space.

---

## 🏗️ Architecture

### Module Map

```
self_referential_forge/
│
├── forge/                          # ⚒️ Core evolution modules
│   ├── __init__.py                 # Package exports
│   ├── __main__.py                 # CLI entry point
│   ├── orchestrator.py             # Self-referential evolution loop
│   └── self_modifier.py            # AST-level code mutation engine
│
├── meta_evolution/                 # 🧠 Strategy adaptation
│   ├── __init__.py
│   └── meta_evolver.py            # Operator weight tuning + novelty
│
├── evaluators/                     # 📊 Self-evaluation
│   ├── __init__.py
│   └── evaluator.py               # 6-dimension fitness scoring
│
├── safety/                         # 🛡️ Tiered safety architecture
│   ├── __init__.py              # Exports SafetyValidator, SafetyTier, etc.
│   ├── policy.py               # Tier definitions, operator→tier mappings
│   ├── audit.py                # Hash-chained, tamper-evident audit log
│   ├── sandbox.py              # Fork-test-promote sandbox lifecycle
│   └── safety_validator.py     # Unified facade coordinating all safety
│
├── archive/                        # 🗃️ State persistence
│   ├── __init__.py
│   └── archivist.py               # Compressed snapshot management
│
├── benchmarks/                     # 📈 Internal quality benchmarks
│   ├── __init__.py
│   └── benchmark_suite.py         # 5 evolution quality metrics
│
├── dashboard/                      # 📊 Real-time web dashboard
│   └── main.py                    # FastAPI + auto-refreshing UI
│
├── self_modification/             # 🔄 Alternative import path
│   └── __init__.py                 # (re-exports from forge.self_modifier)
│
├── run_forge.sh                   # 🚀 Production shell wrapper
├── pyproject.toml                 # 📦 Project metadata
├── README.md                      # 📖 This file
└── .env.example                   # 🔐 Environment template
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **pip** (package installer)

### Setup

```bash
# Navigate to the self-referential forge
cd grounded_agent_forge/self_referential_forge

# Create virtual environment (optional but recommended)
python -m venv .venv && source .venv/bin/activate

# Install the forge
pip install -e .

# Configure environment (optional)
cp .env.example .env
```

### Run the Forge

```bash
# Infinite self-referential evolution (default)
bash run_forge.sh

# Run for 50 cycles
bash run_forge.sh --cycles 50

# Launch with the real-time dashboard
bash run_forge.sh --dashboard

# Require manual approval for each mutation
bash run_forge.sh --human-approval

# All together
bash run_forge.sh --cycles 100 --dashboard --human-approval --verbose
```

You can also run directly via Python:

```bash
python -m forge                          # Infinite evolution
python -m forge --cycles 50              # 50 cycles
python -m forge --dashboard              # + dashboard
python -m forge --verbose                # Debug logging
python -m forge --help                   # Show all options
```

### Launch the Dashboard

```bash
# Option A: Launch alongside the forge
python -m forge --dashboard

# Option B: Launch separately
uvicorn dashboard.main:app --host 0.0.0.0 --port 8000

# Open → http://localhost:8000
```

---

## 📦 Modules

### ⚒️ `forge/orchestrator.py` — Evolution Loop Coordinator

The central loop that drives self-modification:

- Validates the forge environment on startup
- Selects champion components via tournament selection
- Delegates mutation to `SelfModifier` with safety gates
- Evaluates fitness via `SelfEvaluator`
- Updates meta-evolution strategy via `MetaEvolver`
- Snapshots state via `Archivist`
- Supports human-in-the-loop approval gating
- Handles auto-commit for persistent improvement tracking

### 🔧 `forge/self_modifier.py` — AST Mutation Engine

Five genetic operators that mutate the forge's own Python source by rewriting the AST:

| Operator | Description |
|----------|-------------|
| `insert_code` | Injects a randomized logging or branching statement into a function body |
| `rewrite_function` | Replaces a random function body with `pass` (simplification operator) |
| `add_parameter` | Adds an optional `_extra_*` parameter to a random function |
| `swap_condition` | Negates a random if-condition (e.g., `if x:` → `if not x:`) |
| `duplicate_component` | Clones a random class or function definition |

### 🧠 `meta_evolution/meta_evolver.py` — Strategy Adaptation

Tracks operator performance and adjusts the evolution strategy:

- Weighted random operator selection based on historical success
- Fitness delta observation reinforces/penalizes operators
- Novelty boost triggers when stagnation is detected, amplifying low-weight operators
- Mutation rate dynamically adjusted based on recent delta

### 📊 `evaluators/evaluator.py` — Six-Dimension Fitness

| Dimension | Weight | What It Measures |
|-----------|:-----:|------------------|
| 🎯 **Syntax Validity** | 25% | Does the source parse as valid Python AST? |
| ⚙️ **Code Complexity** | 15% | Node count, function/class density, nesting depth |
| 🛡️ **Safety Compliance** | 25% | Absence of eval, exec, os.system, pickle, etc. |
| 🧩 **Modular Cohesion** | 15% | Import ordering, structural separation, `if __name__` |
| 🧪 **Test Survival** | 10% | Do existing tests still pass? (neutral if no tests) |
| 📐 **Style Consistency** | 10% | Line length, indentation discipline, type hints |

### 🛡️ `safety/safety_validator.py` — Guardrail System

Prevents the forge from evolving dangerous capabilities:

- **9 dangerous patterns** flagged: eval, exec, __import__, compile, os.system, subprocess, shutil.rmtree, git push, Docker destructive operations
- **4 critical patterns** flagged: os.remove, shutil.rmtree, Path.unlink
- **File boundary validation**: ensures mutations stay within the forge directory
- **Extension whitelist**: only `.py`, `.toml`, `.md`, `.json`, etc.
- **Directory blacklist**: `.git`, `__pycache__`, `node_modules`, `.venv`
- **Max file size**: 100KB per source file
- **Strict mode**: disallows os/subprocess/shutil imports in mutated code

### 🗃️ `archive/archivist.py` — Snapshot Manager

- Gzip-compressed JSON snapshots per generation
- Configurable max snapshot count (default: 100)
- Full rollback capability to any generation
- In-memory history with fitness trajectory access
- Auto-loads existing snapshots on init

---

## 🛡️ Safety Architecture

Self-modifying code demands a defense-in-depth approach. The safety system is built on **four independent layers**, each designed to be a complete barrier:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SELF-MODIFICATION SAFETY STACK                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─ TIER 3: BLOCKED (never allowed) ──────────────────────────────┐  │
│  │  eval(), exec(), compile(), __import__()                        │  │
│  │  os.system(), subprocess.*, shutil.rmtree()                     │  │
│  │  Path.unlink(), gc.collect()                                    │  │
│  │  Modifications to safety/ or archive/ modules                   │  │
│  │  Writes to .git/, __pycache__/, .venv/                           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                              ▲                                         │
│  ┌─ TIER 2: HUMAN APPROVAL ───────────────────────────────────────┐  │
│  │  swap_condition operator                                        │  │
│  │  Bare except: or broad except Exception:                       │  │
│  │  File write operations (open with w/wb/a mode)                  │  │
│  │  try: blocks (heuristic)                                        │  │
│  │  └─ Human must type 'y' at interactive prompt                   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                              ▲                                         │
│  ┌─ TIER 1: DRY RUN (sandbox required) ────────────────────────────┐  │
│  │  rewrite_function operator                                       │  │
│  │  add_parameter operator                                          │  │
│  │  duplicate_component operator                                    │  │
│  │  └─ Fails if: syntax error, AST violation, test failure          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                              ▲                                         │
│  ┌─ TIER 0: AUTOMATED (no gate) ───────────────────────────────────┐  │
│  │  insert_code operator (logging/branching injection)              │  │
│  │  └─ Still checked: syntax validity + dangerous pattern scan      │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  CROSS-CUTTING: SANDOX + AUDIT                                   │  │
│  │                                                                   │  │
│  │  ┌──────────────────┐  ┌────────────────────┐                    │  │
│  │  │  SANDBOX          │  │  AUDIT LOG          │                    │  │
│  │  │  fork → test →    │  │  hash-chained JSONL  │                    │  │
│  │  │  promote/rollback │  │  tamper-evident      │                    │  │
│  │  └──────────────────┘  └────────────────────┘                    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Tiered Policy (`safety/policy.py`)

Every mutation operator maps to a safety tier. The policy defines what is allowed at each tier:

| Tier | Name | Gate | Operators |
|------|------|------|-----------|
| 0 | `AUTOMATED` | None | `insert_code` |
| 1 | `DRY_RUN` | Sandbox tests must pass | `rewrite_function`, `add_parameter`, `duplicate_component` |
| 2 | `HUMAN_APPROVAL` | Interactive prompt | `swap_condition` |
| 3 | `BLOCKED` | Never allowed | eval, exec, os.system, subprocess, etc. |

The policy also enforces:
- **Blocked AST nodes**: `Exec`, `Eval`, `Call` (when used dangerously)
- **Blocked imports**: os, subprocess, shutil, signal, ctypes, socket, multiprocessing
- **Protected modules**: The `safety/` and `archive/` packages are immune to mutation
- **Path restrictions**: Only `.py`, `.toml`, `.md`, `.json`, etc. files within the forge root

### Layer 2: Sandbox Testing (`safety/sandbox.py`)

Every Tier 1+ mutation must pass through the **fork-test-promote** lifecycle:

```
  BEFORE                          AFTER (if tests pass)
    │                                 ▲
    ▼                                 │
  ┌─────────────────────────────────────────┐
  │  1. FORK: Copy source to temp sandbox    │
  │  2. MUTATE: Apply operator to sandbox    │
  │  3. VALIDATE:                             │
  │     ├─ Syntax check (ast.parse)          │
  │     ├─ AST safety scan (blocked nodes)   │
  │     ├─ Dangerous pattern scan (regex)    │
  │     └─ Unit test execution (pytest)      │
  │  4. PROMOTE: Write to live file          │
  │     OR                                    │
  │     ROLLBACK: Restore original source     │
  └─────────────────────────────────────────┘
```

### Layer 3: Hash-Chained Audit Log (`safety/audit.py`)

Every mutation — whether approved or rejected — is recorded in an **append-only, hash-chained audit log**. Each entry contains:

| Field | Description |
|-------|-------------|
| `timestamp` | Unix timestamp of the mutation |
| `mutation_id` | Unique UUID for the mutation |
| `operator` | Name of the mutation operator |
| `tier` | Safety tier at which it was assessed |
| `component_path` | Relative path to the mutated component |
| `source_hash_before` | SHA-256 of source before mutation |
| `source_hash_after` | SHA-256 of source after mutation |
| `safety_verdict` | approved, rejected, or rolled_back |
| `safety_violations` | List of violations (if rejected) |
| `human_approver` | Who approved (if Tier 2) |
| `sandbox_result` | passed, failed, or skipped |
| `prev_hash` | SHA-256 of the previous entry |
| `entry_hash` | SHA-256 of this entry |

The `prev_hash` → `entry_hash` chain provides **tamper evidence**: modifying an entry changes its hash, breaking the chain for all subsequent entries. The chain can be verified at any time:

```python
from safety import AuditLog
audit = AuditLog()
chain_ok, issues = audit.verify_chain()
```

### Layer 4: Environment Validation (`safety/safety_validator.py`)

Before any mutation cycle begins, the safety validator performs a full environment scan:
- All forge source files must parse as valid Python
- No blocked modules are imported in forge source
- The forge root directory is writable and accessible
- The audit log chain is intact from the previous run

### Human-in-the-Loop Gates

| Scenario | Mechanism |
|----------|-----------|
| Tier 2 operator selected | Interactive prompt: `Approve this self-modification? [y/N]` |
| `--human-approval` flag | Every mutation, regardless of tier, requires approval |
| Consecutive safety failures | Forge halts after `max_consecutive_failures` (default: 5) |
| Audit chain violation | Error logged immediately upon detection |

### Rollback Mechanisms

| Mechanism | Trigger | Scope |
|-----------|---------|-------|
| **Git revert** | Auto-commit before each mutation; `git revert` on failure | Full file |
| **Archive restore** | Snapshots every generation; `rollback_to(N)` | Full state |
| **Sandbox rollback** | Mutation fails sandbox tests | Single file |
| **Safety violation** | Dangerous pattern detected | Mutation cancelled (no write) |

### Red Team Scenarios

| Attack | Defense |
|--------|---------|
| Mutation inserts `eval()` | Blocked at Tier 3 — never allowed |
| Mutation imports `os` to delete files | Blocked at Tier 3 — blocked import |
| Mutation modifies safety code | Blocked — protected module |
| Mutation writes outside forge root | Blocked — path sandboxing |
| Operator tries to escape tier | Blocked — operator→tier mapping is immutable policy |
| Audit log is tampered | Detected — hash chain breaks on next verification |
| Sandbox test is skipped | Impossible — Tier 1+ requires sandbox pass before promote |

### Safety Checklist for Production Use

- [ ] Always use `--human-approval` for unattended runs
- [ ] Review `.env.example` and set `HUMAN_APPROVAL=true`
- [ ] Verify the audit log chain before each session
- [ ] Run in a dedicated directory or container
- [ ] Ensure git is initialized for rollback capability
- [ ] Set `META_PATH` to a persistent, backed-up location
- [ ] Review `safety/policy.py` before adding new operators
- [ ] Never disable safety (`--safety-off`) in production

---

## 🔬 Research Context

### What This Project Explores

| Research Direction | Description |
|-------------------|-------------|
| 🧬 **Self-Referential Evolution** | Can a system improve its own evolutionary algorithm by mutating its own source code? |
| 🔄 **Second-Order Adaptation** | Does tracking operator-level fitness deltas lead to more efficient evolution than fixed-operator GAs? |
| 🛡️ **Safe Self-Modification** | Can safety guardrails be designed that are robust enough to allow creative exploration while preventing destructive outcomes? |
| 📊 **Self-Evaluation Accuracy** | Do AST-level fitness metrics (syntax, complexity, safety) correlate with actual evolution quality? |
| 🗃️ **Evolutionary Memory** | Does maintaining an immutable archive of all mutations improve the system's ability to roll back from local optima? |

### What This Is NOT

- ❌ A claim of AGI, sentience, or consciousness
- ❌ An unconstrained recursive self-improvement system
- ❌ A production-ready code generator

✅ It is a **well-scoped experimental platform** for studying how genetic algorithms can safely modify their own implementation — with strong guardrails, immutable history, and full human oversight.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Credits

| Contribution | Link |
|-------------|------|
| 🧬 **Predecessor** | [grounded_agent_forge](https://github.com/NullLabTests/grounded_agent_forge) — full agent blueprint evolution platform |
| 📜 **Inspiration** | [grounded_evolution](https://github.com/NullLabTests/grounded_evolution) — execution-grounded prompt evolution with 203 evolution cycles |
| 🤖 **Primary Coding Model** | DeepSeek V4 — used as the primary AI coding model for this entire project |

---

<div align="center">

**Made with 🧬 by NullLabTests · Evolution is the ultimate optimizer**

[![License](https://img.shields.io/github/license/NullLabTests/grounded_agent_forge?style=flat-square)](LICENSE)
[![Issues](https://img.shields.io/github/issues/NullLabTests/grounded_agent_forge?style=flat-square&logo=github)](https://github.com/NullLabTests/grounded_agent_forge/issues)

</div>
