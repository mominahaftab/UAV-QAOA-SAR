# Classical Benchmark & Experiment Protocol

## 1. Canonical Benchmark Specification
All solver implementations (Exact MILP, Enumeration Validator, Greedy Heuristic, and future QAOA quantum solvers) must be benchmarked against the standard canonical scenario:

- **Scenario Name**: `Canonical-5T-6W-k3`
- **Targets ($M=5$)**: `["T1", "T2", "T3", "T4", "T5"]`
- **Candidate Waypoints ($N=6$)**: `["W1", "W2", "W3", "W4", "W5", "W6"]`
- **Required Redundancy**: $k = 3$
- **Expected Minimum Objective**: 4 waypoints
- **Known Optimal Cardinality**: Exactly 9 subsets of size 4 satisfy all constraints.

---

## 2. Classical Solvers Reproduction Guide

### Executing via Python Script
```python
from backend.sar.scenario import get_canonical_benchmark_scenario
from backend.solvers.classical.milp import SciPyMILPSolver, BruteForceEnumerationValidator
from backend.solvers.classical.greedy import GreedySolver

# 1. Load canonical benchmark
scenario = get_canonical_benchmark_scenario()
problem = scenario.to_optimization_problem()

# 2. Run SciPy Exact MILP
milp_solver = SciPyMILPSolver()
milp_result = milp_solver.solve(problem)
print(f"MILP Selected Waypoints: {milp_result.selected_waypoints}")
print(f"MILP Minimum Waypoints: {milp_result.cost} (Feasible: {milp_result.is_feasible})")

# 3. Run Brute-Force Enumeration Validation
validator = BruteForceEnumerationValidator()
enum_result = validator.validate(problem)
print(f"Enumeration Optimum: {enum_result.min_waypoints}")
print(f"Number of Optima: {enum_result.num_optimal_combinations}")

# 4. Run Greedy Heuristic
greedy_solver = GreedySolver()
greedy_result = greedy_solver.solve(problem)
print(f"Greedy Selected Waypoints: {greedy_result.selected_waypoints}")
print(f"Greedy Feasible: {greedy_result.is_feasible}")
```

### Running Test Verification via Pytest
```bash
pytest tests/unit/test_classical_solvers.py -v
```

---

## 3. Runtime Measurement Methodology
1. **Precision Timing**: All solver runtimes are measured using `time.perf_counter()` to obtain sub-millisecond wall-clock resolution.
2. **Exclusion of Model Formulation**: The timing block begins immediately before problem ingestion by the core solver function and concludes as soon as solution decoding completes. Data generation and scenario validation times are excluded from solver execution time.
3. **Warm-up and Repetition Policy**: In larger benchmarking experiments, solvers are executed across 10 trials, with the first trial discarded as a warm-up to eliminate cold-start JIT and library loading artifacts. Runtimes are reported as mean $\pm$ standard deviation.

---

## 4. Random Seed Policy for Generated Scenarios
When evaluating scalable synthetic spatial scenarios beyond the canonical benchmark:
1. **Deterministic Pseudo-Random Generation**: All synthetic generators must accept an explicit integer random seed (`seed: int = 42`).
2. **Generator Isolation**: `numpy.random.default_rng(seed)` or `random.Random(seed)` instances must be instantiated locally inside generator functions rather than altering the global random state.
3. **Archived Artifacts**: Whenever synthetic scenarios are generated for benchmarking papers or demonstrations, the exact generated $(x, y)$ coordinate tuples and resulting binary matrices must be serialized to JSON/CSV for independent verification.

