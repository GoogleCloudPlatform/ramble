---
name: ramble-results-analyzer
description: "Guide for extracting Figures of Merit (FOMs), evaluating experiment success criteria, comparing performance metrics across matrix dimensions, and generating benchmark summary reports."
---

# Ramble Results Analyzer Guide

This skill provides guidelines for analyzing Ramble experiment outputs, extracting Figures of Merit (FOMs), calculating performance metrics (e.g., speedup, scaling efficiency), and producing structured benchmark summary reports.

---

## 1. Running Workspace Analysis

After experiment execution finishes, run the analysis command:

```bash
ramble -D <workspace_name> workspace analyze
```

This command parses output files across all experiment instances in `<workspace>/experiments/`, evaluates `success_criteria`, extracts `figure_of_merit` directives, and writes output files:
- `<workspace>/results.latest.txt` (Human-readable plain text summary)
- `<workspace>/results.latest.json` (Structured JSON representation)
- `<workspace>/results.latest.yaml` (Structured YAML representation)

---

## 2. Understanding Results Structure

The results file organizes data hierarchically:
- **Experiment Scope**: Application name, workload name, experiment name.
- **Variables**: Final evaluated key-value pairs for the run (e.g., `n_nodes`, `n_ranks`, `processes_per_node`, `compiler`).
- **Success Criteria**: Evaluation results (`PASSED` or `FAILED`).
- **Figures of Merit (FOMs)**: Parsed numerical or string metrics (e.g., execution time, GFLOPS, throughput) with units and context.

---

## 3. Performance & Scaling Analysis

When analyzing experiment sweeps, evaluate key high-performance computing metrics:

### A. Speedup ($S_N$)
$$S_N = \frac{T_1}{T_N}$$
Where $T_1$ is runtime on 1 node (or baseline configuration) and $T_N$ is runtime on $N$ nodes.

### B. Parallel Scaling Efficiency ($E_N$)
$$E_N = \frac{S_N}{N} = \frac{T_1}{N \cdot T_N}$$

### C. Matrix Sweep Comparisons
When performing A/B testing across compilers, MPI versions, or cloud machine types:
1. Group experiments by primary variant (e.g., `machine_type` or `compiler`).
2. Compare FOM values (e.g., `Time (s)` or `FOM/sec`) for identical workloads and rank counts.
3. Identify performance deltas percentage: $\frac{\text{FOM}_A - \text{FOM}_B}{\text{FOM}_B} \times 100\%$.

---

## 4. Generating Benchmark Summary Reports

When asked to summarize results, present findings in a structured Markdown report:

### Report Template

```markdown
# Benchmark Analysis Report: <Application / Workload Name>

## Executive Summary
- **Primary Metric**: <FOM Name> (<Units>)
- **Best Configuration**: <Experiment Name / Machine Type / Rank Count>
- **Peak Performance**: <Value> <Units>

## Scaling & Performance Summary

| Nodes | Ranks | Machine / Compiler | FOM (<Units>) | Speedup | Scaling Efficiency | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 16 | gcc-12 | 124.5 | 1.00x | 100.0% | PASSED |
| 2 | 32 | gcc-12 | 68.2 | 1.83x | 91.3% | PASSED |
| 4 | 64 | gcc-12 | 37.1 | 3.36x | 83.9% | PASSED |

## Key Insights & Observations
1. **Scaling Trend**: Scaling remains above 80% up to 4 nodes (64 ranks).
2. **Bottlenecks**: Performance leveling observed beyond 8 nodes due to interconnect communication overhead.
3. **Recommendations**: Recommended production allocation is 4 nodes per job.
```
