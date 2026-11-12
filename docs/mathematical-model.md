# Mathematical Model: UAV Search-and-Rescue $k$-Coverage

## 1. Problem Definition
In UAV-assisted Search and Rescue (SAR) missions, timely and reliable detection of critical ground points (distress beacons, stranded personnel, lost hikers) requires redundant observation. Due to sensor noise, terrain occlusion, camera angle limitations, or false negatives, a single sighting is often insufficient for definitive localization.

We define the **$k$-Coverage Waypoint Selection Problem** as selecting the minimal subset of candidate aerial sensing waypoints such that every target interest point is simultaneously observed by at least $k$ distinct chosen waypoints.

---

## 2. Decision Variables
Let:
- $\mathcal{T} = \{t_1, t_2, \dots, t_M\}$ denote the set of $M$ ground targets requiring observation.
- $\mathcal{W} = \{w_1, w_2, \dots, w_N\}$ denote the set of $N$ candidate UAV sensing waypoints.
- $A \in \{0, 1\}^{M \times N}$ be the binary sensing coverage matrix, where:
  $$A_{ji} = \begin{cases} 1, & \text{if candidate waypoint } w_i \text{ can observe target } t_j \\ 0, & \text{otherwise} \end{cases}$$

The decision variables are binary indicator variables:
$$x_i \in \{0, 1\}, \quad \forall i \in \{1, \dots, N\}$$
where $x_i = 1$ if waypoint $w_i$ is selected for UAV sensing, and $x_i = 0$ otherwise.

---

## 3. Objective Function
The operational goal is to minimize total UAV deployment effort, flight time, and hover duration. In the standard unweighted formulation, this corresponds to minimizing the total number of selected waypoints:

$$\min_{\mathbf{x}} \sum_{i=1}^N x_i$$

*(Note: When waypoint costs $c_i > 0$ are assigned based on distance from base or terrain risk, the objective generalizes to $\min \sum_{i=1}^N c_i x_i$.)*

---

## 4. Coverage Constraints
Each target $t_j$ must receive at least $k$ independent observations from the selected subset of waypoints:

$$\sum_{i=1}^N A_{ji} x_i \ge k, \quad \forall j \in \{1, \dots, M\}$$

with integrality constraints:
$$x_i \in \{0, 1\}, \quad \forall i \in \{1, \dots, N\}$$

This problem is a generalization of the classic NP-hard Minimum Set Cover problem, formally known as **Minimum Multicover** or **$k$-Set Cover**.

---

## 5. Canonical Benchmark Dataset
To guarantee rigorous reproducibility across solvers, we define an exact, deterministic canonical benchmark instance:

- **Targets**: $M = 5$ (`T1`, `T2`, `T3`, `T4`, `T5`)
- **Candidate Waypoints**: $N = 6$ (`W1`, `W2`, `W3`, `W4`, `W5`, `W6`)
- **Required Coverage**: $k = 3$

### Binary Coverage Matrix $A$:
$$\begin{array}{c|cccccc}
& \text{W1} & \text{W2} & \text{W3} & \text{W4} & \text{W5} & \text{W6} \\
\hline
\text{T1} & 0 & 1 & 1 & 1 & 1 & 1 \\
\text{T2} & 1 & 0 & 1 & 1 & 1 & 1 \\
\text{T3} & 1 & 1 & 0 & 1 & 1 & 1 \\
\text{T4} & 1 & 1 & 1 & 0 & 1 & 1 \\
\text{T5} & 1 & 1 & 1 & 1 & 0 & 0 \\
\end{array}$$

### Mathematical Properties:
- **Target coverage potential**: Targets T1–T4 each have 5 potential covering waypoints; target T5 has only 4 covering waypoints (W1, W2, W3, W4).
- **Minimum selected waypoints**: $\text{Optimum} = 4$. Any subset of size $\le 3$ cannot satisfy $k=3$ across all targets.
- **Degeneracy / Multi-Optima**: There are **exactly 9 optimal subsets of size 4** that achieve complete feasibility ($k \ge 3$ for all 5 targets).

---

## 6. Significance of $k = 3$
In search-and-rescue localization:
- $k = 1$ is simple set cover, vulnerable to sensor blind spots, false negatives, and single-point-of-failure occlusions.
- $k = 2$ provides pairwise redundancy but cannot resolve ambiguous trilateration signals or disparate optical detections.
- $k = 3$ represents the operational sweet spot: it establishes tri-directional geometric cross-bearing, supports majority-voting consensus under noisy detection, and substantially increases the combinatorial complexity of the optimization landscape.

---

## 7. Exact vs. Greedy Solver Comparison

| Property | SciPy MILP (`scipy.optimize.milp`) | Greedy Heuristic (`GreedySolver`) |
| :--- | :--- | :--- |
| **Methodology** | Branch-and-Cut (HiGHS Simplex / Dual Interior-Point) | Myopic deficit-reduction greedy choice |
| **Optimality** | **Guaranteed globally optimal** | **Heuristic approximation** (no optimality guarantee) |
| **Worst-case Complexity** | Exponential $\mathcal{O}(2^N)$ in worst case | Polynomial $\mathcal{O}(N \cdot M)$ |
| **Tie-Breaking** | Dual simplex pivoting / branch order | Smallest waypoint index $i$ |
| **Role in Project** | Ground-truth baseline for quantum benchmark | Real-time polynomial-time fast comparison baseline |

---

## 8. Limitations & Abstraction Assumptions
1. **Abstract Sensing Disks**: The coverage matrix $A$ assumes an idealized binary sensing model. In real physical environments, RF and optical propagation are subject to antenna radiation patterns, log-normal shadowing, Fresnel clearance zones, multipath fading, and variable meteorological attenuation.
2. **Separation of Targets and Waypoints**: Targets are points of interest on the ground (e.g., in ravines or dense canopy); waypoints are navigable aerial coordinates. They exist in different altitude and operational domains.
3. **No Real RF Claim**: Synthetic sensing scenarios provide controlled algorithmic benchmarks and do not represent measured RF signal telemetry or physical search guarantees.

