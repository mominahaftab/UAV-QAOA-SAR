# UAV-QAOA-SAR: Quantum-Optimized UAV Waypoint Selection for Rapid Search-and-Rescue Localization

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.x%20%7C%201.x-6929C4.svg)](https://qiskit.org)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Project Overview

**UAV-QAOA-SAR** is an open-source, reproducible decision-support application built for university quantum-computing hackathons and research demonstrations.

The mission objective is to select the **minimum number of UAV sensing waypoints** required to provide at least **$k$-fold coverage** across all critical ground target locations (e.g., victims, signal beacons, lost hikers) within an emergency Search-and-Rescue (SAR) search perimeter.

The optimization engine maps the NP-hard $k$-coverage Multicover problem to a **Quadratic Unconstrained Binary Optimization (QUBO)** problem and executes the **Quantum Approximate Optimization Algorithm (QAOA)** locally using **Qiskit** and **Qiskit Aer** simulation. It directly benchmarks quantum solutions against classical heuristics (Greedy) and exact Mathematical Programming (SciPy MILP).

---

## 2. Architecture & Design Principles

1. **Independent Mathematical Formulation**: Geometry, sensing matrices, and QUBO translations are completely decoupled from FastAPI.
2. **Classical Solvers Independent of Quantum Libraries**: Classical baseline solvers (Greedy, SciPy MILP) have zero dependencies on Qiskit.
3. **Dedicated QAOA Solver Module**: The quantum circuit generation, cost/mixer Hamiltonians, and Aer simulation run in an isolated module adhering to `BaseSolver`.
4. **Decoupled Database Persistence**: Database persistence (SQLAlchemy ORM + Alembic) is strictly decoupled from the optimization logic.
5. **Decoupled Web Frontend**: React + Vite + TypeScript frontend communicates with the backend exclusively via standard HTTP REST endpoints.
6. **Zero Cloud Hardware Requirement**: Local execution powered by `qiskit-aer` without requiring IBM Quantum API keys.
7. **No Synthetic Misrepresentation**: Synthetic SAR coordinates and sensor models are mathematically explicit; no real RF measurements are fabricated.

Detailed architecture specifications are documented in [`docs/architecture.md`](file:///c:/UAV-QAOA-SAR/docs/architecture.md).

---

## 3. Repository Structure

```
c:\UAV-QAOA-SAR
├── .env.example                # Sample environment variables
├── .gitignore                  # Git exclusion rules
├── .python-version             # Python version target (3.12)
├── README.md                   # Project overview & setup instructions
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py       # REST API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Pydantic BaseSettings configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy database entities
│   │   └── session.py          # Database engine & session maker
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic DTO request/response schemas
│   ├── sar/
│   │   └── __init__.py         # Sensing matrix & spatial geometry
│   ├── services/
│   │   └── __init__.py         # Mission & optimization orchestrator
│   └── solvers/
│       ├── __init__.py
│       ├── base.py             # BaseSolver, OptimizationProblem, OptimizationResult
│       ├── classical/
│       │   └── __init__.py     # Greedy & SciPy MILP solvers
│       └── qaoa/
│           └── __init__.py     # Qiskit QAOA quantum solver
├── docs/
│   ├── architecture.md         # Full system architecture specification
│   ├── implementation-plan.md  # Step-by-step phased engineering roadmap
│   └── references.md           # Academic & technical citations
├── frontend/
│   ├── index.html
│   ├── package.json            # Node/React dependencies
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx             # Root dashboard component
│       ├── main.tsx            # React application entry
│       ├── index.css           # Global styling
│       ├── services/
│       │   └── api.ts          # REST client communicating with FastAPI
│       └── types/
│           └── index.ts        # TypeScript data transfer models
├── scripts/                    # Reproducibility & demonstration scripts
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── __init__.py
    │   └── test_config.py      # Core unit tests
    └── integration/
        ├── __init__.py
        └── test_api_health.py  # End-to-end API health tests
```

---

## 4. Getting Started & Setup Guide

### Prerequisites
- **Python**: Version 3.12 (or 3.13)
- **Node.js**: Version 18+ (tested with Node 24+)
- **Git**: Installed and available in PATH

---

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/your-username/UAV-QAOA-SAR.git
cd UAV-QAOA-SAR

# Copy environment variables
cp .env.example .env
```

---

### Step 2: Backend Setup (Python)

1. **Create and Activate Virtual Environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Backend Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

3. **Run Unit & Integration Tests**:
   ```bash
   pytest tests/
   ```

4. **Launch the FastAPI Backend**:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Interactive Swagger API docs will be accessible at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Step 3: Frontend Setup (React + Vite + TypeScript)

1. **Navigate to the Frontend Directory**:
   ```bash
   cd frontend
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Build the Production Bundle**:
   ```bash
   npm run build
   ```

4. **Launch Vite Development Server**:
   ```bash
   npm run dev
   ```
   The UI will be accessible at: [http://localhost:5173](http://localhost:5173)

---

## 5. UI Features & User Experience

### Section 1: Freight-Train Scroll-Scrubbed Cinematic Landing Page
- **Scroll-Controlled Recon Video**: Responsive 1080p/720p aerial reconnaissance video strictly scrubbed by window scroll position via a piecewise polynomial seek mapper (`video.currentTime`). Never autoplays or loops.
- **Exo 2 Typography**: 4-line typography headline (`SEARCH SMARTER. / COVER FASTER. / RESPOND BETTER. / SAVE LIVES.`) in Exo 2 ExtraBold 800 with soft drop shadows and cream `#F7F5EF` palette.
- **5 Mirrored Architecture Blocks**: Alternating cards detailing $k$-coverage resilience, exact QUBO/Ising mapping with penalty bounds ($\lambda > 6.0$), QAOA circuit optimization, multi-solver classical benchmarking, and FastAPI mission control.
- **Technical Credibility Section**: Transition pull-up into 4 editorial pillars addressing realistic NISQ sampling rates (29% feasible yield at $p=1$), mathematical penalty thresholds, classical dual-verification, and zero false speedup claims.

### Section 2: Interactive UAV Mission Control & Radar Telemetry
- **2D Coordinate Radar Map**: Interactive SVG canvas displaying ground targets ($T_1 \dots T_5$), candidate waypoints ($W_1 \dots W_6$), active sensing beams, and node tooltips.
- **4-Way Solver Execution**: Execute and inspect solutions across **QAOA** (with configurable depth $p$, shots, penalty $\lambda$, max iterations, and seed), **SciPy MILP** (exact Branch-and-Cut), **Brute Force** ($2^N$ exhaustive enumeration), and **Greedy** heuristics.
- **Direct Multi-Solver Benchmark**: One-click side-by-side benchmark table comparing feasibility, waypoint count, runtime (ms), and optimality gap across all four solvers.
- **Historical Run Audit**: Browse, reload, and review past optimization runs persisted in SQLite/PostgreSQL.

---

## 6. Implementation Status

- **Phase 1: Project Scaffolding & Virtual Environment** ✅ (Complete)
- **Phase 2: Mathematical Formulation & Classical Solvers (MILP, Brute-Force, Greedy)** ✅ (Complete)
- **Phase 3: QUBO Formulation & High-Speed QAOA Solver** ✅ (Complete)
- **Phase 4: FastAPI REST API, Alembic Database Migrations & Persistence** ✅ (Complete)
- **Phase 5: Cinematic Landing Page & Interactive UAV Mission Control UI** ✅ (Complete)

All 93 automated pytest unit and integration tests passing. Clean TypeScript compilation with Vite bundle packaging.

