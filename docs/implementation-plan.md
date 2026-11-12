# Project Implementation Plan

## Project Title
**Quantum-Optimized UAV Waypoint Selection for Rapid Search-and-Rescue Localization**

---

## Phase Roadmap

### Phase 1: Project Scaffolding, Environment & Baseline Setup (Current)
- [x] Inspect workspace and runtime environments (Python 3.12 target, Node 24+).
- [x] Establish modular folder structure (`backend`, `frontend`, `tests`, `scripts`, `docs`).
- [x] Configure source control exclusions (`.gitignore`) and environment configurations (`.env.example`).
- [x] Create architectural specifications, academic references, and implementation plan.
- [x] Verify package compatibility for Qiskit, Qiskit Aer, FastAPI, SciPy, SQLAlchemy, and frontend tools.
- [x] Set up dependency manifests (`requirements.txt`, `package.json`).
- [ ] Present completed scaffolding for team and user approval before mathematical modeling.

---

### Phase 2: Mathematical Formulation & Sensing Geometry
- [ ] Define the $k$-coverage problem formulation:
  $$\min \sum_{j=1}^N x_j \quad \text{s.t.} \quad \sum_{j=1}^N A_{ij} x_j \ge k, \; \forall i \in \{1,\dots,M\}, \; x_j \in \{0, 1\}$$
- [ ] Implement geometry module:
  - Synthetic 2D target generation (uniform, clustered, or corridor-based).
  - Candidate waypoint generation (grid, randomized, or boundary-aware).
  - Sensor coverage disk calculation: $A_{ij} = 1$ if distance $(t_i, w_j) \le R_{\text{sensor}}$, else $0$.
- [ ] Implement QUBO mapping:
  - Penalty formulation for shortfall: $P \sum_{i=1}^M \left( \max(0, k - \sum_{j} A_{ij} x_j) \right)^2$ or via slack binary variables.
  - Automatic penalty multiplier ($P$) calculation ensuring feasibility dominance.
  - Conversion of QUBO to Ising spin Hamiltonian ($x_j = \frac{1 - Z_j}{2}$).
- [ ] Unit tests for geometry, sensing matrix generation, and QUBO matrix symmetry.

---

### Phase 3: Classical Baseline Solvers
- [ ] Define `BaseSolver` abstract interface:
  ```python
  class BaseSolver(ABC):
      @abstractmethod
      def solve(self, problem: OptimizationProblem) -> OptimizationResult: ...
  ```
- [ ] Implement `GreedySolver`:
  - Greedily selects waypoint covering maximum unmet target coverage until all targets reach $k$ or no progress is possible.
- [ ] Implement `SciPyMILPSolver`:
  - Formulates the exact binary integer linear program using `scipy.optimize.milp`.
  - Produces ground truth optimal solutions for benchmark comparisons.
- [ ] Unit tests verifying both classical solvers against known small test problems.

---

### Phase 4: QAOA Quantum Solver Module
- [ ] Implement `QAOASolver` utilizing Qiskit 1.x and Qiskit-Aer:
  - Construct Cost Hamiltonian ($H_C$) from QUBO as a `SparsePauliOp`.
  - Construct Mixer Hamiltonian ($H_M = \sum_j X_j$).
  - Build parameterized QAOA circuit ($p$ layers) using `QAOAAnsatz`.
  - Implement energy expectation evaluation using `qiskit_aer.AerSimulator` and `qiskit.primitives.StatevectorSampler`.
  - Outer-loop parameter optimization with `scipy.optimize.minimize` (COBYLA / Nelder-Mead).
  - Measurement decoding: extract most probable bitstrings, filter feasibility, evaluate approximation ratio.
- [ ] Comprehensive test suite comparing QAOA output against classical baselines on small instances (4–10 qubits).

---

### Phase 5: Database Layer & State Persistence
- [ ] Setup SQLAlchemy ORM models (`Mission`, `Target`, `Waypoint`, `OptimizationRun`).
- [ ] Configure database engine supporting SQLite (`sqlite:///...`) and PostgreSQL (`postgresql://...`).
- [ ] Initialize Alembic migration scripts.
- [ ] Create repository functions for storing and retrieving missions and benchmark runs.

---

### Phase 6: FastAPI Service Layer & REST API
- [ ] Build Pydantic request and response schemas (DTOs).
- [ ] Implement REST endpoints:
  - `POST /api/v1/missions`: Create a new mission and scenario.
  - `GET /api/v1/missions/{id}`: Retrieve scenario details.
  - `POST /api/v1/missions/{id}/optimize`: Trigger optimization with chosen solver (QAOA, SciPy, Greedy).
  - `GET /api/v1/missions/{id}/results`: Retrieve past runs and benchmark comparison metrics.
- [ ] Add integration tests using `httpx.AsyncClient` or FastAPI `TestClient`.

---

### Phase 7: Interactive Frontend Application
- [ ] Set up React + Vite + TypeScript application with Tailwind CSS.
- [ ] Implement mission parameter controls (grid size, number of targets, sensor radius, required $k$-coverage, QAOA layers $p$).
- [ ] Implement Plotly interactive charts:
  - 2D geographical map with targets, candidate waypoints, sensor coverage disks, and selected optimal waypoints.
  - QAOA convergence plot (energy vs. iteration).
  - Comparative bar charts (QAOA vs. Greedy vs. MILP execution time and waypoint count).
- [ ] API integration service for asynchronous mission execution.

---

### Phase 8: Benchmarking, Validation & Demonstration
- [ ] End-to-end integration test of the full workflow.
- [ ] Create reproducible benchmark scripts in `scripts/run_benchmarks.py`.
- [ ] Write user guide and presentation summary for the hackathon judging panel.

