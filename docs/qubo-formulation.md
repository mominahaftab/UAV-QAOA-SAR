# QUBO Formulation for the k-Coverage Problem

## 1. Introduction and Purpose

This document explains how the k-coverage waypoint selection Integer Linear Program (ILP) is translated into a **Quadratic Unconstrained Binary Optimization (QUBO)** problem suitable for quantum optimization algorithms such as QAOA.

The core challenge is that quantum circuits naturally operate on **unconstrained** binary variables. The coverage inequality constraints ($\sum A_{ji} x_i \ge k$) must be absorbed into the objective using a **penalty function**.

---

## 2. Original ILP Problem

**Decision variables**: $x_i \in \{0, 1\}$ for each of $N$ candidate waypoints.

**Objective** (minimize waypoints selected):
$$\min \sum_{i=1}^N x_i$$

**Coverage constraints** (each of $M$ targets must receive $\ge k$ observations):
$$\sum_{i=1}^N A_{ji} x_i \ge k, \quad \forall j \in \{1,\ldots,M\}$$

For the canonical instance: $M=5$, $N=6$, $k=3$.

---

## 3. Binary Slack Variables

To convert the inequality constraints into equalities, we introduce **slack variables** $b_{j0}, b_{j1} \in \{0,1\}$ for each target $j$.

We model the **excess coverage** as:
$$s_j = b_{j0} + 2 \cdot b_{j1} \in \{0, 1, 2, 3\}$$

This covers all possible excess values using only 2 bits per target:

| $b_{j0}$ | $b_{j1}$ | $s_j$ |
|:---:|:---:|:---:|
| 0 | 0 | 0 |
| 1 | 0 | 1 |
| 0 | 1 | 2 |
| 1 | 1 | 3 |

> **Why 2 slack bits?** For the canonical instance, the maximum coverage any target can receive from all 6 waypoints is 5. With $k=3$ required, the maximum excess is $5 - 3 = 2$, which fits within $s_j \le 3$. So 2 slack bits are sufficient. For larger instances with higher excess, additional bits would be needed.

The equality constraint becomes:
$$\sum_{i=1}^N A_{ji} x_i - k - b_{j0} - 2 b_{j1} = 0 \quad \Rightarrow \quad R_j = 0$$

---

## 4. QUBO Objective with Penalty

We embed the constraints into the objective using a quadratic penalty:

$$F(\mathbf{x}, \mathbf{b}) = \underbrace{\sum_{i=1}^N x_i}_{\text{waypoint objective}} + \underbrace{A_P \sum_{j=1}^M R_j^2}_{\text{constraint penalty}}$$

where:
$$R_j = \sum_{i=1}^N A_{ji} x_i - k - b_{j0} - 2 b_{j1}$$

For the canonical 5T-6W-k3 instance: $A_P = 7$.

**Justification for $A_P = 7$**: The best feasible solution has objective value 4. Any infeasible binary assignment has $|R_j| \ge 1$ for at least one target, contributing at least $7 \times 1^2 = 7$ to the penalty. Since the waypoint objective is non-negative, an infeasible assignment cannot achieve $F < 7 > 4$. Therefore the QUBO minimum is achieved by feasible assignments. This reasoning is **specific to the canonical instance** and must be re-evaluated for other problem sizes or objective magnitudes.

---

## 5. Variable Ordering

The 16 binary variables for the canonical instance are ordered as:

| Index | Variable | Meaning |
|:---:|:---:|:---|
| 0 | $x_0$ | Waypoint W1 |
| 1 | $x_1$ | Waypoint W2 |
| 2 | $x_2$ | Waypoint W3 |
| 3 | $x_3$ | Waypoint W4 |
| 4 | $x_4$ | Waypoint W5 |
| 5 | $x_5$ | Waypoint W6 |
| 6 | $b_{0,0}$ | Slack bit 0 for Target T1 |
| 7 | $b_{0,1}$ | Slack bit 1 for Target T1 |
| 8 | $b_{1,0}$ | Slack bit 0 for Target T2 |
| 9 | $b_{1,1}$ | Slack bit 1 for Target T2 |
| 10 | $b_{2,0}$ | Slack bit 0 for Target T3 |
| 11 | $b_{2,1}$ | Slack bit 1 for Target T3 |
| 12 | $b_{3,0}$ | Slack bit 0 for Target T4 |
| 13 | $b_{3,1}$ | Slack bit 1 for Target T4 |
| 14 | $b_{4,0}$ | Slack bit 0 for Target T5 |
| 15 | $b_{4,1}$ | Slack bit 1 for Target T5 |

---

## 6. Binary Identity Reduction ($z_i^2 = z_i$)

Expanding $R_j^2$ produces squared terms like $z_i^2$ for binary $z_i \in \{0,1\}$. Using $z_i^2 = z_i$:
- $A_{ji}^2 x_i^2 = A_{ji} x_i$ (since $A_{ji} \in \{0,1\}$)  
- $b_{j0}^2 = b_{j0}$,  $b_{j1}^2 = b_{j1}$

This reduction moves squared binary terms to the **linear (diagonal) part** of the QUBO matrix.

---

## 7. QUBO Matrix Convention

The QUBO is stored as a symmetric $16 \times 16$ matrix $Q$ where:
- **Diagonal** $Q_{ii}$: Linear coefficient of $z_i$ (incorporating $z_i^2 = z_i$)
- **Upper-triangle** $Q_{ij}$ ($i < j$): Coefficient of the interaction term $z_i z_j$

Energy evaluation formula:
$$F(\mathbf{z}) = \sum_i Q_{ii} z_i + \sum_{i < j} Q_{ij} z_i z_j + \text{offset}$$

where `offset` is the constant term from expanding $k^2$ across all targets.

---

## 8. QUBO-to-Ising Conversion

Quantum circuits work with **Pauli-Z** operators. We use the mapping:
$$z_i = \frac{1 - Z_i}{2}$$

where $Z_i$ is the Pauli-Z operator on qubit $i$ (eigenvalues $\pm 1$).

Substituting:

**Linear term:**
$$Q_{ii} z_i = \frac{Q_{ii}}{2} - \frac{Q_{ii}}{2} Z_i$$

**Quadratic term** ($i < j$):
$$Q_{ij} z_i z_j = \frac{Q_{ij}}{4} \left(I - Z_i - Z_j + Z_i Z_j\right)$$

Collecting all contributions:
$$H_C = C \cdot I + \sum_i h_i Z_i + \sum_{i < j} J_{ij} Z_i Z_j$$

where:
- $C = \text{offset} + \sum_i \frac{Q_{ii}}{2} + \sum_{i<j} \frac{Q_{ij}}{4}$  (constant / identity coefficient)
- $h_i = -\frac{Q_{ii}}{2} - \frac{1}{4}\sum_{j \ne i} Q_{\min(i,j), \max(i,j)}$  (Z coefficients)
- $J_{ij} = \frac{Q_{ij}}{4}$  (ZZ coupling coefficients, $i < j$)

### Qiskit Pauli-String Bit Ordering

In Qiskit's `SparsePauliOp`, a Pauli string of length $n$ has its **rightmost character correspond to qubit 0**. For qubit $i$, the character position in the string is $(n-1-i)$.

For example, for $n=16$ qubits: the string `"Z" + "I"*15` (Z at position 0 of string) corresponds to $Z_{15}$ (qubit 15, the **last** variable $b_{4,1}$), **not** $Z_0$.

The implementation explicitly maps variable index $i$ to string position $n-1-i$ to maintain correct correspondence.

---

## 9. Validation

The exhaustive validation test (`test_ising_exhaustive_all_65536_assignments`) confirms that:
$$\text{QUBO energy}(\mathbf{z}) = \text{Ising energy}(\mathbf{z}), \quad \forall \mathbf{z} \in \{0,1\}^{16}$$

across all $2^{16} = 65{,}536$ computational basis states. This validates the QUBO matrix construction, binary identity application, and Ising conversion identically.

