# CLAUDE.md — Expert Coding Agent

## Project Overview

A Python coding agent that **compounds expertise across debugging sessions** through empirical pattern recognition, automatic archetype formation, and execution-driven learning. Unlike typical AI coding agents that reset every session, this system builds a persistent "career" — session 100 is exponentially faster than session 1.

**Version:** 0.2.0
**Language:** Python 3.8+
**External dependencies:** None (stdlib only). Optional: `docker`, `matplotlib`.
**License:** MIT

## Repository Structure

```
Expert-Coding-Agent/
├── src/                           # Core system (~4,650 LOC, 11 modules)
│   ├── __init__.py                # Package version
│   ├── production_agent.py        # Main orchestration layer (Day 1)
│   ├── codebase_engine.py         # Git ops, test execution, multi-file editing (Day 1)
│   ├── code_analyzer.py           # AST-based code understanding (Day 2)
│   ├── test_generator.py          # Coverage gap detection & test creation (Day 3)
│   ├── refactoring_engine.py      # Safe refactoring with rollback (Day 4)
│   ├── coding_agent.py            # Integration layer with expertise
│   ├── knowledge_core.py          # Persistent pattern storage & decay
│   ├── failure_taxonomy.py        # Automatic archetype formation
│   ├── hypothesis_ordering.py     # Bayesian debugging via information gain
│   └── execution_engine.py        # Code execution (local + Docker)
│
├── docs/                          # Architecture docs, audit responses, roadmap
│   ├── README.md                  # Architecture & design principles
│   ├── WEEK_1_ROADMAP.md          # 7-day build plan
│   ├── DAY_*_COMPLETE.md          # Day completion summaries
│   ├── DAY_*_AUDIT_RESPONSE.md    # Audit findings & patch details
│   └── ...
│
├── test_compounding.py            # Core validation: expertise compounds
├── simulate_career.py             # 100+ session simulation with visualization
├── validate_day2.py               # Binary validation: code understanding
├── validate_day3.py               # Binary validation: test generation
├── validate_day4.py               # Binary validation: safe refactoring
├── verify_day3_patches.py         # Patch verification (3/3)
├── verify_day4_patches.py         # Patch verification (3/3)
├── verify_fixes.py                # All-fixes verification
├── demo_ordering.py               # Hypothesis ordering demo
├── demo_production.py             # Production agent demo
└── README.md                      # Project overview
```

## Architecture

```
Layer 5: ProductionCodingAgent     — orchestration, expertise integration
Layer 4: CodeAnalyzer              — AST parsing, dependency graphs, impact prediction
Layer 3: CodebaseExecutionEngine   — clone repos, run tests, multi-file editing
Layer 2: FailureTaxonomy + HypothesisOrderer — pattern learning, Bayesian debugging
Layer 1: KnowledgeCore             — persistent concepts/instances, confidence, decay
```

Each layer depends only on layers below it. The system enforces execution before persistence — no pattern is stored without empirical evidence.

## Running Tests & Validation

All validation scripts are standalone Python (no pytest/unittest framework). Run from the repo root:

```bash
# Core compounding validation (3/4 checks expected)
python test_compounding.py

# Day-specific binary validation (all should pass)
python validate_day2.py
python validate_day3.py
python validate_day4.py

# Patch verification
python verify_day3_patches.py    # 3/3 patches
python verify_day4_patches.py    # 3/3 patches
python verify_fixes.py

# Career simulation (100+ sessions, generates career_simulation.png)
python simulate_career.py --domain concurrency --sessions 100

# Demos
python demo_ordering.py
python demo_production.py
```

**Testing philosophy: binary validation only.** Tests return True or False. There are no soft passes, no "maybe," no inconclusive results. If detection/generation/refactoring doesn't work, the test fails hard.

## Code Conventions

- **Type hints throughout** (PEP 484 style with `Optional`, `List`, `Dict`, `Tuple`)
- **Dataclasses** for all structured data (`@dataclass`)
- **Enums** for categories (`PatternCategory`, `RefactoringType`, `OutcomeType`)
- **Naming:** PascalCase classes, snake_case functions/methods, UPPER_CASE constants, `_underscore` prefix for private methods
- **AST parsing** for code analysis (never regex for structural code understanding)
- **No external ML/LLM/RAG dependencies** in core — stdlib only
- **Dict-based JSON persistence** for expertise storage

## Design Principles

1. **Execution-driven** — code must run before patterns persist. No unexecuted code.
2. **Binary validation** — tests pass or fail, never "inconclusive."
3. **Capability before features** — prove the core loop works before adding integrations.
4. **Expertise compounds** — each session improves future sessions via archetype formation.
5. **Selective forgetting** — old/low-value patterns decay to prevent junk accumulation.
6. **Fail loudly** — the system blocks or rolls back rather than proceeding with uncertainty.

## Key Patterns to Preserve

- **Archetype formation:** 3+ similar failures automatically cluster into a reusable archetype.
- **Explanation gate:** code understanding must be proven complete before execution proceeds.
- **Test enforcement:** refactoring is blocked if affected functions lack test coverage.
- **Automatic rollback:** any refactoring that changes test counts or introduces failures is rolled back.
- **Confidence is empirical:** based on validation rate + severity + recency, not opinions.

## Implementation Status

- **Day 1** (complete): Production infrastructure — `codebase_engine.py`, `production_agent.py`
- **Day 2** (complete): Code understanding — `code_analyzer.py` with AST parsing, dependency graphs, impact prediction
- **Day 3** (complete): Test generation — `test_generator.py` with coverage gaps, assertion quality checks
- **Day 4** (complete): Safe refactoring — `refactoring_engine.py` with rollback guarantees
- **Day 5** (planned): Error recovery
- **Day 6** (planned): Integration testing
- **Day 7** (planned): Production hardening

## Common Development Tasks

**Adding a new capability:**
1. Create a new module in `src/` following the dataclass + type-hint conventions.
2. Wire it into `production_agent.py` at the appropriate layer.
3. Write a `validate_dayN.py` binary validation script (no soft passes).
4. Document in `docs/DAY_N_COMPLETE.md`.

**Fixing an audit finding:**
1. Apply the patch to the relevant source file.
2. Write a `verify_dayN_patches.py` verification script.
3. Document the fix in `docs/DAY_N_AUDIT_RESPONSE.md`.
4. Re-run the corresponding `validate_dayN.py` to confirm all checks pass.

**Running on a real project:**
```bash
python demo_production.py
# Or use validate_day2.py with a local path:
python validate_day2.py --project-path /path/to/repo
```
