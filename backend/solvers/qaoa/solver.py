"""QAOA Solver for k-Coverage Waypoint Selection.

Implements a standard QAOA (Quantum Approximate Optimization Algorithm) workflow:
1. Construct cost Hamiltonian H_C from QUBO Ising form.
2. Build parameterized QAOA circuit (alternating cost and mixer unitaries).
3. Optimize variational parameters (gamma, beta) using SciPy with exact Statevector expectation.
4. Sample the final circuit on a local Qiskit Aer simulator.
5. Decode bitstrings into waypoint selections and evaluate coverage feasibility.

IMPORTANT SCIENTIFIC DISCLAIMERS:
- This implementation runs on a LOCAL QUANTUM CIRCUIT SIMULATOR (Qiskit Aer).
- It does NOT run on a real quantum computer or IBM quantum hardware.
- No quantum advantage or quantum speedup is claimed or implied.
- The quantum advantage of QAOA over classical methods for small instances is not established.
- Coverage feasibility is evaluated using the original abstract binary sensing model.
- QAOA may fail to sample the optimal solution; infeasible samples are explicitly reported.

References:
    Farhi et al. (2014), arXiv:1411.4028.
    Lee et al. (2026), arXiv:2609.01930.
"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator
from qiskit import transpile

from backend.solvers.base import BaseSolver, OptimizationProblem, OptimizationResult
from backend.solvers.qubo.formulation import QUBOProblem, build_qubo
from backend.solvers.qubo.conversion import IsingHamiltonian, qubo_to_ising


@dataclass
class QAOAResult:
    """Extended QAOA result with detailed quantum diagnostics.

    This is returned by QAOASolver.solve_qaoa() for full details.
    Use to_optimization_result() to convert to the standard BaseSolver interface.
    """
    # Status
    status: str                      # 'feasible' | 'no_feasible_sample' | 'error'
    warnings: List[str]

    # Solution
    selected_waypoints: List[int]    # Indices of waypoints in best feasible sample
    num_selected: int
    is_feasible: bool
    coverage_achieved: float         # 0.0 to 1.0

    # Energetics
    qubo_energy_best: float          # QUBO energy of best feasible sample (-inf if none)
    ising_expectation: float         # E[H_C] at optimized parameters
    optimality_gap: Optional[float]  # (qaoa_obj - classical_opt) / classical_opt

    # QAOA parameters
    gamma: List[float]
    beta: List[float]
    qaoa_depth_p: int
    objective_evaluations: int

    # Sampling statistics
    shots: int
    num_unique_bitstrings: int
    feasible_sample_count: int
    infeasible_sample_count: int
    feasible_rate: float
    best_feasible_frequency: int     # Number of times best solution was sampled
    best_feasible_bitstring: str     # Bitstring of best feasible solution

    # Runtime
    total_runtime_ms: float
    optimizer_runtime_ms: float
    sampling_runtime_ms: float

    # Configuration
    simulator_name: str
    random_seed: int
    optimizer: str
    max_iterations: int
    num_qubits: int

    def to_optimization_result(self) -> OptimizationResult:
        """Convert to standard BaseSolver OptimizationResult."""
        cost = float(self.num_selected) if self.is_feasible else float("inf")
        return OptimizationResult(
            solver_name="qaoa",
            selected_waypoints=self.selected_waypoints,
            num_selected=self.num_selected,
            is_feasible=self.is_feasible,
            coverage_achieved=self.coverage_achieved,
            execution_time_ms=self.total_runtime_ms,
            cost=cost,
            metadata={
                "status": self.status,
                "warnings": self.warnings,
                "gamma": self.gamma,
                "beta": self.beta,
                "qaoa_depth_p": self.qaoa_depth_p,
                "objective_evaluations": self.objective_evaluations,
                "ising_expectation": self.ising_expectation,
                "qubo_energy_best": self.qubo_energy_best,
                "optimality_gap": self.optimality_gap,
                "shots": self.shots,
                "num_unique_bitstrings": self.num_unique_bitstrings,
                "feasible_sample_count": self.feasible_sample_count,
                "infeasible_sample_count": self.infeasible_sample_count,
                "feasible_rate": self.feasible_rate,
                "best_feasible_frequency": self.best_feasible_frequency,
                "best_feasible_bitstring": self.best_feasible_bitstring,
                "simulator_name": self.simulator_name,
                "random_seed": self.random_seed,
                "optimizer": self.optimizer,
                "is_heuristic": True,
                "is_quantum_simulation": True,
                "quantum_advantage_claimed": False,
            },
        )


def _build_qaoa_circuit(cost_op: SparsePauliOp, p: int) -> QAOAAnsatz:
    """Construct the standard QAOA parameterized circuit using Qiskit's QAOAAnsatz."""
    return QAOAAnsatz(cost_operator=cost_op, reps=p)


def _compute_expectation_statevector(
    ansatz: QAOAAnsatz,
    cost_op: SparsePauliOp,
    params: np.ndarray,
) -> float:
    """Compute exact expectation value <psi(params)|H_C|psi(params)> using statevector.

    Decomposes the ansatz into elementary gates to evaluate fast without expm.
    """
    gate_circuit = ansatz.decompose().decompose()
    bound_circuit = gate_circuit.assign_parameters(params)
    sv = Statevector(bound_circuit)
    return float(np.real(sv.expectation_value(cost_op)))


def _precompute_diagonal_energies(ising: IsingHamiltonian) -> np.ndarray:
    """Precompute Ising Hamiltonian diagonal energies for all 2^N basis states.

    In Qiskit statevector indexing, basis state integer index `idx` maps to qubit
    assignments where qubit `i` has value `(idx >> i) & 1`.
    """
    n = ising.num_qubits
    energies = np.zeros(2**n, dtype=np.float64)
    for idx in range(2**n):
        bits = np.array([(idx >> i) & 1 for i in range(n)], dtype=np.float64)
        energies[idx] = ising.evaluate_ising_fast(bits)
    return energies


def _decode_bitstring(
    bitstring: str,
    num_qubits: int,
    num_waypoints: int,
    num_targets: int,
) -> Tuple[List[int], List[int]]:
    """Decode a measurement bitstring into waypoint bits and slack bits.

    Qiskit AerSimulator returns bitstrings with the RIGHTMOST bit = qubit 0.
    For a bitstring of length num_qubits:
        qubit i corresponds to bitstring[num_qubits - 1 - i]

    Variable ordering matches the QUBO formulation:
        qubits 0..N-1 : waypoint variables x_0..x_{N-1}
        qubits N..N+2M-1 : slack variables b_j0, b_j1 (j=0..M-1)
    """
    bs = bitstring.replace(" ", "").zfill(num_qubits)[-num_qubits:]
    bits = [int(bs[num_qubits - 1 - i]) for i in range(num_qubits)]
    waypoint_bits = bits[:num_waypoints]
    slack_bits = bits[num_waypoints:]
    return waypoint_bits, slack_bits


def _check_feasibility(
    waypoint_bits: List[int],
    coverage_matrix: List[List[int]],
    k_coverage: int,
) -> Tuple[bool, float, List[int]]:
    """Check coverage feasibility for a waypoint selection against the original matrix."""
    A = np.array(coverage_matrix, dtype=int)
    x = np.array(waypoint_bits, dtype=int)
    counts = A @ x
    satisfied = int(np.sum(counts >= k_coverage))
    m = A.shape[0]
    is_feasible = (satisfied == m)
    coverage_ratio = satisfied / m if m > 0 else 0.0
    return is_feasible, coverage_ratio, counts.tolist()


class QAOASolver(BaseSolver):
    """QAOA solver for k-coverage UAV waypoint selection.

    Implements a complete QAOA workflow:
    1. Builds QUBO from OptimizationProblem.
    2. Converts QUBO to Ising Hamiltonian (SparsePauliOp).
    3. Builds parameterized QAOA circuit decomposed to native gates.
    4. Optimizes variational parameters using SciPy with exact Statevector probabilities.
    5. Samples the optimized circuit on AerSimulator.
    6. Decodes and evaluates all measurement outcomes.

    Note: This runs entirely on a LOCAL SIMULATOR. No quantum hardware is used.
    No quantum advantage over classical solvers is claimed or demonstrated.
    """

    def __init__(
        self,
        qaoa_depth: int = 1,
        shots: int = 2000,
        penalty: float = 7.0,
        optimizer: str = "COBYLA",
        max_iterations: int = 200,
        random_seed: int = 42,
        classical_optimum: Optional[float] = None,
    ):
        self.qaoa_depth = qaoa_depth
        self.shots = shots
        self.penalty = penalty
        self.optimizer = optimizer
        self.max_iterations = max_iterations
        self.random_seed = random_seed
        self.classical_optimum = classical_optimum

    @property
    def name(self) -> str:
        return "qaoa"

    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        """Satisfy BaseSolver interface. Calls solve_qaoa and converts to OptimizationResult."""
        qaoa_result = self.solve_qaoa(problem)
        return qaoa_result.to_optimization_result()

    def solve_qaoa(self, problem: OptimizationProblem) -> QAOAResult:
        """Full QAOA solve returning extended QAOAResult with diagnostic metadata."""
        total_start = time.perf_counter()
        warn_list: List[str] = []

        # 1. Build QUBO
        qubo = build_qubo(
            problem.sensing_matrix,
            k_coverage=problem.k_coverage,
            penalty=self.penalty,
        )
        num_qubits = qubo.num_variables

        # 2. Convert to Ising Hamiltonian
        ising = qubo_to_ising(qubo)
        cost_op = ising.pauli_op

        # 3. Build parameterized QAOA circuit pre-decomposed to native gates
        # Decomposing into elementary gates avoids calling scipy.sparse.linalg.expm
        raw_ansatz = _build_qaoa_circuit(cost_op, p=self.qaoa_depth)
        gate_ansatz = raw_ansatz.decompose().decompose()

        # Precompute diagonal energies for exact expectation evaluation:
        # E[H_C] = sum_z p(z) * E(z) = probs @ diagonal_energies
        diagonal_energies = _precompute_diagonal_energies(ising)

        # 4. Parameter optimization using exact statevector expectation
        rng = np.random.default_rng(self.random_seed)
        x0 = np.concatenate([
            rng.uniform(0.1, np.pi, self.qaoa_depth),
            rng.uniform(0.1, np.pi / 2, self.qaoa_depth),
        ])

        eval_count = 0

        def objective(params: np.ndarray) -> float:
            nonlocal eval_count
            eval_count += 1
            bound_circuit = gate_ansatz.assign_parameters(params)
            sv = Statevector(bound_circuit)
            probs = sv.probabilities()
            return float(probs @ diagonal_energies)

        opt_start = time.perf_counter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            opt_result = minimize(
                objective,
                x0,
                method=self.optimizer,
                options={"maxiter": self.max_iterations, "rhobeg": 0.5},
            )
        opt_time_ms = (time.perf_counter() - opt_start) * 1000.0

        optimized_params = opt_result.x
        ising_expectation = float(opt_result.fun)

        p = self.qaoa_depth
        gamma_opt = optimized_params[:p].tolist()
        beta_opt = optimized_params[p:].tolist()

        if not opt_result.success:
            warn_list.append(f"Optimizer did not converge: {opt_result.message}")

        # 5. Build measurement circuit and sample on AerSimulator
        sample_start = time.perf_counter()
        bound_circuit = gate_ansatz.assign_parameters(optimized_params)
        meas_circuit = bound_circuit.copy()
        meas_circuit.measure_all()

        sim = AerSimulator(method="statevector")
        qc_t = transpile(meas_circuit, sim)
        sim_result = sim.run(qc_t, shots=self.shots, seed_simulator=self.random_seed).result()
        counts: Dict[str, int] = sim_result.get_counts()
        sample_time_ms = (time.perf_counter() - sample_start) * 1000.0

        # 6. Decode and evaluate all sampled bitstrings
        feasible_samples: List[Tuple[float, int, List[int], str]] = []
        feasible_count = 0
        infeasible_count = 0

        for bitstring, count in counts.items():
            wp_bits, sl_bits = _decode_bitstring(
                bitstring, num_qubits, problem.num_waypoints, problem.num_targets
            )
            is_feas, cov_ratio, _ = _check_feasibility(
                wp_bits, problem.sensing_matrix, problem.k_coverage
            )
            if is_feas:
                obj_val = float(sum(wp_bits))
                selected_idxs = [i for i, b in enumerate(wp_bits) if b == 1]
                feasible_samples.append((obj_val, count, selected_idxs, bitstring))
                feasible_count += count
            else:
                infeasible_count += count

        total_runtime_ms = (time.perf_counter() - total_start) * 1000.0

        # 7. Select best feasible result (lowest waypoint objective, then highest frequency)
        if feasible_samples:
            feasible_samples.sort(key=lambda t: (t[0], -t[1]))
            best_obj, best_count, best_waypoints, best_bitstring = feasible_samples[0]

            is_feas, coverage_ratio, cov_counts = _check_feasibility(
                [1 if i in best_waypoints else 0 for i in range(problem.num_waypoints)],
                problem.sensing_matrix,
                problem.k_coverage,
            )

            wp_bits, sl_bits = _decode_bitstring(
                best_bitstring, num_qubits, problem.num_waypoints, problem.num_targets
            )
            full_bits = np.array(wp_bits + sl_bits, dtype=float)
            qubo_energy_best = qubo.evaluate_fast(full_bits)

            opt_gap: Optional[float] = None
            classical_opt = self.classical_optimum if self.classical_optimum is not None else 4.0
            if classical_opt > 0:
                opt_gap = (best_obj - classical_opt) / classical_opt

            feasible_rate = feasible_count / self.shots

            return QAOAResult(
                status="feasible",
                warnings=warn_list,
                selected_waypoints=best_waypoints,
                num_selected=len(best_waypoints),
                is_feasible=True,
                coverage_achieved=coverage_ratio,
                qubo_energy_best=qubo_energy_best,
                ising_expectation=ising_expectation,
                optimality_gap=opt_gap,
                gamma=gamma_opt,
                beta=beta_opt,
                qaoa_depth_p=p,
                objective_evaluations=eval_count,
                shots=self.shots,
                num_unique_bitstrings=len(counts),
                feasible_sample_count=feasible_count,
                infeasible_sample_count=infeasible_count,
                feasible_rate=feasible_rate,
                best_feasible_frequency=best_count,
                best_feasible_bitstring=best_bitstring,
                total_runtime_ms=total_runtime_ms,
                optimizer_runtime_ms=opt_time_ms,
                sampling_runtime_ms=sample_time_ms,
                simulator_name="AerSimulator(statevector)",
                random_seed=self.random_seed,
                optimizer=self.optimizer,
                max_iterations=self.max_iterations,
                num_qubits=num_qubits,
            )
        else:
            warn_list.append(
                f"No feasible sample found in {self.shots} shots. "
                f"Infeasible count: {infeasible_count}."
            )
            return QAOAResult(
                status="no_feasible_sample",
                warnings=warn_list,
                selected_waypoints=[],
                num_selected=0,
                is_feasible=False,
                coverage_achieved=0.0,
                qubo_energy_best=float("inf"),
                ising_expectation=ising_expectation,
                optimality_gap=None,
                gamma=gamma_opt,
                beta=beta_opt,
                qaoa_depth_p=p,
                objective_evaluations=eval_count,
                shots=self.shots,
                num_unique_bitstrings=len(counts),
                feasible_sample_count=0,
                infeasible_sample_count=infeasible_count,
                feasible_rate=0.0,
                best_feasible_frequency=0,
                best_feasible_bitstring="",
                total_runtime_ms=total_runtime_ms,
                optimizer_runtime_ms=opt_time_ms,
                sampling_runtime_ms=sample_time_ms,
                simulator_name="AerSimulator(statevector)",
                random_seed=self.random_seed,
                optimizer=self.optimizer,
                max_iterations=self.max_iterations,
                num_qubits=num_qubits,
            )
