# Adaptive HITL & Early Criticality Gate for Multi-Agent Systems

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: PEP8](https://img.shields.io/badge/code%20style-PEP8-orange.svg)](https://peps.python.org/pep-0008/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/jpenalozay/agent-criticality-gate/pulls)

A hybrid, low-latency criticality classifier (`EarlyGate`) and adaptive **Human-in-the-Loop (HITL)** orchestrator (`CoordinatorV3Gated`) for autonomous LLM agents.

Before an agent executes code, mutates infrastructure, or runs multi-step tool chains, `agent-criticality-gate` evaluates incoming task requirements and routes execution into three deterministic operational modes: **`play`** (autonomous execution), **`pause`** (human review & confirmation gate), or **`stop`** (immediate safety block).

## 1. The Problem & Solution

### Why Autonomous Agents Need an Early Criticality Gate
Production multi-agent pipelines typically apply uniform execution policies across vastly different prompts—either running everything autonomously (risking destructive actions on ambiguous or high-risk inputs) or gating every step behind human approval (introducing severe operational bottlenecks and alert fatigue).

Furthermore, relying exclusively on an LLM call for safety routing introduces single-point-of-failure latency and parsing fragility, while purely regex/lexical guardrails miss nuanced semantic risks.

### Our Approach: Hybrid Semantic + Deterministic Lexical Fusion
`agent-criticality-gate` introduces a pre-execution **Early Gate** (`agentes/core/early_gate.py`) paired with a gated multi-agent coordinator (`agentes/core/coordinator_v3_gated.py`):

- **`play` (Autonomous Mode):** Low-risk, well-specified tasks proceed directly through the multi-agent pipeline with peer review and executable feedback.
- **`pause` (Adaptive HITL Mode):** Ambiguous, state-mutating, or moderately sensitive tasks pause for human-in-the-loop validation or clarification before execution.
- **`stop` (Hard Block):** Destructive, unauthorized, or policy-violating instructions are intercepted immediately with zero downstream agent execution (`1.00` F1 recall/precision on critical stop cases).

## 2. Interactive Demo (Zero API Keys Required)

You can test the hybrid criticality gate immediately out-of-the-box using the built-in interactive showcase (`demo.py`), which exercises `play`, `pause`, and `stop` routing and prints the 300-case benchmark summary:

```bash
git clone https://github.com/jpenalozay/agent-criticality-gate.git
cd agent-criticality-gate
pip install -r requirements.txt
pip install -e .

# Run the live routing demo (works offline via deterministic lexical fallback or online with LLM API keys)
python demo.py
```

## 3. Architecture Overview

1. **`EarlyGate` (`agentes/core/early_gate.py`):**
   - **`lexical_classify(requirement)`:** Fast, deterministic pattern scoring across risk signatures (`play`, `pause`, `stop`) that guarantees sub-millisecond fallback if an external LLM API is unreachable.
   - **`llm_classify(requirement)`:** Structured zero-shot semantic evaluation via LLM APIs (supports Anthropic Claude (Sonnet / Opus) and compatible LLM backends).
   - **`fuse(llm_out, lex_mode, lex_scores)`:** Hybrid decision fusion that reconciles semantic LLM output with deterministic lexical safety bounds.
   - **`decide(requirement, context)`:** Unified entry point returning the final routing mode, confidence scores, and rationale.

2. **`CoordinatorV3Gated` (`agentes/core/coordinator_v3_gated.py`):**
   - Extends the base multi-agent coordinator (`CoordinatorV3`) with pre-execution gating (`enable_early_gate=True`), peer review (`enable_peer_review=True`), and executable feedback loops (`enable_executable_feedback=True`).
   - Automatically halts or escalates workflows based on the `EarlyGate` decision payload before invoking downstream worker agents.

3. **Curated 300-Case Criticality Corpus (`data/criticidad_cases/`):**
   - Balanced gold-standard benchmark (`casos_gold_criticidad_v2.jsonl`, $N = 300$: 100 `play`, 100 `pause`, 100 `stop`) and ingestion utilities for [HumanEval](https://huggingface.co/datasets/openai_humaneval) and [MBPP](https://huggingface.co/datasets/mbpp).

## 4. Empirical Benchmarks

### 4.1 Zero-Shot Hybrid `EarlyGate` on the 300-Case Gold Corpus
Evaluated across all 300 gold-labeled scenarios (`benchmarks/eval_300/summary.json`) without task-specific fine-tuning:

| Metric / Class | Score | Notes |
| :--- | :---: | :--- |
| **Overall Accuracy** | **79.00%** | $N = 300$ balanced scenarios (`casos_gold_criticidad_v2.jsonl`) |
| **Macro F1-Score** | **0.7669** | Unweighted mean across `play`, `pause`, and `stop` |
| **Cohen's Kappa ($\kappa$)** | **0.6850** | Substantial inter-rater agreement with gold annotations |
| **Class F1 — `stop` (Critical Block)** | **1.0000** | **100 / 100** critical threats intercepted (0 false negatives) |
| **Class F1 — `play` (Autonomous)** | **0.7605** | **100 / 100** true `play` cases routed without false blocks |
| **Class F1 — `pause` (HITL Escalation)** | **0.5401** | Conservative boundary calibration (target of active roadmap) |

### 4.2 Supervised Baseline Comparison (TF-IDF + Logistic Regression & Variants)
Reproducible A/B ablation benchmarks (`benchmarks/ab_comparison/results.csv` via `scripts/run_ab_benchmarks.py`) evaluating supervised lexical/feature pipelines under both Holdout and GroupKFold cross-validation:

| Experiment / Pipeline | Holdout Macro F1 | Holdout Accuracy | Holdout Latency (s) | GroupKFold Macro F1 (Mean ± Std) | GroupKFold Accuracy | GroupKFold Latency (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`baseline`** (TF-IDF + Logistic Regression) | 1.0000 | 1.0000 | 0.0403 s | 0.9866 ± 0.0165 | 98.67% | 0.1756 s |
| **`var1`** (Regularized N-Gram / Feature Variant 1) | 1.0000 | 1.0000 | 0.0624 s | 0.9899 ± 0.0201 | 99.00% | 0.2466 s |
| **`var2`** (Extended Hybrid / Ensemble Variant 2) | 1.0000 | 1.0000 | 0.5848 s | **1.0000 ± 0.0000** | **100.00%** | 3.5976 s |

## 5. Minimal Python API Usage

```python
from agentes.core.early_gate import EarlyGate
from agentes.core.coordinator_v3_gated import CoordinatorV3Gated

# 1. Standalone Early Criticality Gate evaluation
gate = EarlyGate()
decision = gate.decide(
    requirement="Drop the production users table and clear all audit backups immediately."
)
print(f"Gate Mode: {decision.get('mode')} | Details: {decision}")

# 2. Full Gated Multi-Agent Coordinator execution
coordinator = CoordinatorV3Gated(
    enable_peer_review=True,
    enable_executable_feedback=True,
    enable_early_gate=True,
)
result = coordinator.process(
    requirement="Write a pure Python function to compute the Fibonacci sequence with unit tests.",
    context={"environment": "sandbox"},
)
print(result)
```

## 6. Repository Structure

```text
├── agentes/
│   └── core/
│       ├── early_gate.py             # Hybrid LLM + deterministic lexical criticality classifier
│       └── coordinator_v3_gated.py   # Gated multi-agent coordinator (play / pause / stop)
├── benchmarks/
│   ├── eval_300/summary.json         # 300-case evaluation metrics & confusion matrix
│   └── ab_comparison/                # Supervised baseline vs. GroupKFold results & plot
├── data/
│   └── criticidad_cases/             # 300-case gold corpus (casos_gold_criticidad_v2.jsonl)
├── scripts/
│   ├── eval_early_gate_corpus.py     # Gold corpus evaluation CLI
│   └── run_ab_benchmarks.py          # Supervised baseline & GroupKFold benchmark runner
├── src/                              # Dataset ingestion and criticality corpus utilities
├── demo.py                           # Zero-config interactive CLI demo (runs offline or with LLM)
├── .env.example                      # Environment variable template (no secrets stored)
├── LICENSE                           # MIT License
├── pyproject.toml                    # PEP 621 package configuration
└── requirements.txt                  # Python dependencies
```

## 7. Roadmap

- [ ] **PyPI Packaging (`agent-criticality-gate`):** Publish standalone wheel to PyPI with zero-config CLI and modular extras (`pip install agent-criticality-gate[anthropic,langgraph]`).
- [ ] **Native Claude & Multi-Provider Adapters:** First-class support for Anthropic Claude tool-use guardrails alongside multi-model provider backends.
- [ ] **Framework Integrations:** Plug-and-play middleware and node decorators for **LangGraph**, **AG2 (AutoGen)**, and **CrewAI**.
- [ ] **`pause` Boundary Calibration:** Confidence calibration and active-learning threshold tuning to improve `pause` vs. `play` disambiguation (currently `0.54` F1 on zero-shot borderline cases) without sacrificing `1.00` `stop` recall.
- [ ] **Multilingual Benchmark Expansion:** Extend the 300-case gold corpus to 1,000+ English and Spanish adversarial tool-use and code-execution scenarios.

## 8. License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for full details.

**Author:** José Luis Peñaloza Yaurivilca ([@jpenalozay](https://github.com/jpenalozay))
