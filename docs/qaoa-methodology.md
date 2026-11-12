# QAOA Methodology

## 1. What Is QAOA?

The **Quantum Approximate Optimization Algorithm (QAOA)** is a variational quantum algorithm introduced by Farhi, Goldstone, and Gutmann (2014). It is designed to find approximate solutions to combinatorial optimization problems encoded as Hamiltonians.

QAOA alternates between two operations (a **cost unitary** and a **mixer unitary**) for $p$ layers and uses a classical optimizer to tune the variational parameters.

> **Important**: QAOA is an **approximate** algorithm. It does not guarantee finding the global optimum, particularly at low circuit depths ($p=1$ or $p=2$). We make no claims of quantum advantage or quantum speedup in this implementation.

---

## 2. Initial Superposition

The QAOA circuit begins by placing all $n$ qubits into an **equal superposition**:
$$|+\rangle^{\otimes n} = H^{\otimes n} |0\rangle^{\otimes n} = \frac{1}{\sqrt{2^n}} \sum_{\mathbf{z} \in \{0,1\}^n} |\mathbf{z}\rangle$$

This gives every computational basis state (every binary assignment) equal initial amplitude.

---

## 3. Cost Hamiltonian and Cost Unitary

The **cost Hamiltonian** $H_C$ is derived from the QUBO Ising form:
$$H_C = C \cdot I + \sum_i h_i Z_i + \sum_{i < j} J_{ij} Z_i Z_j$$

The **cost unitary** at angle $\gamma$ applies a phase proportional to the energy of each state:
$$U_C(\gamma) = e^{-i \gamma H_C}$$

States with lower QUBO energy gain favorable phases under this unitary, steering the quantum distribution toward low-energy (better) solutions.

---

## 4. Mixer Hamiltonian and Mixer Unitary

The **standard transverse-field mixer** is:
$$H_B = \sum_{i=1}^n X_i$$

The **mixer unitary** at angle $\beta$ applies independent X-rotations to each qubit:
$$U_B(\beta) = e^{-i \beta H_B} = \bigotimes_{i=1}^n e^{-i \beta X_i} = \bigotimes_{i=1}^n R_x(2\beta)$$

The mixer allows transitions between states, enabling exploration of the binary solution space. This is an **unconstrained mixer**: it can produce both feasible and infeasible bitstrings. Feasibility is checked after measurement.

---

## 5. Variational Parameters: $\gamma$ and $\beta$

For a QAOA circuit of depth $p$, there are $2p$ variational parameters:
$$\boldsymbol{\gamma} = [\gamma_1, \ldots, \gamma_p], \quad \boldsymbol{\beta} = [\beta_1, \ldots, \beta_p]$$

- **$\gamma_l$** (cost angle): Controls how strongly the cost Hamiltonian is applied in layer $l$. Larger $\gamma$ creates larger phase differences between high- and low-energy states.
- **$\beta_l$** (mixer angle): Controls how much the mixer rotates the state in layer $l$. Balances exploration vs. exploitation.

The optimal parameters are found by minimizing the expectation value $\langle H_C \rangle$.

---

## 6. QAOA Circuit Structure

For depth $p$, the QAOA circuit is:
$$|\psi(\boldsymbol{\gamma}, \boldsymbol{\beta})\rangle = U_B(\beta_p) U_C(\gamma_p) \cdots U_B(\beta_1) U_C(\gamma_1) |+\rangle^{\otimes n}$$

The circuit is implemented using Qiskit's `QAOAAnsatz`, which constructs this automatically from the cost Hamiltonian.

---

## 7. Classical Parameter Optimization

We use **SciPy** to find optimal $(\boldsymbol{\gamma}, \boldsymbol{\beta})$ by minimizing:
$$\mathcal{L}(\boldsymbol{\gamma}, \boldsymbol{\beta}) = \langle \psi(\boldsymbol{\gamma}, \boldsymbol{\beta}) | H_C | \psi(\boldsymbol{\gamma}, \boldsymbol{\beta}) \rangle$$

During optimization, we use **ideal statevector simulation** (Qiskit's `StatevectorEstimator`) which computes exact expectation values without shot noise. This provides stable gradient estimates for the classical optimizer.

The optimizer used is **COBYLA** (Constrained Optimization By Linear Approximations), a gradient-free method suitable for variational quantum circuits.

---

## 8. Measurement and Shot Counts

After finding optimal parameters, the QAOA circuit is executed on **Qiskit Aer** (local quantum circuit simulator) with $n_{\text{shots}}$ measurement repetitions.

Each measurement outcome is a **bitstring** $\mathbf{z} \in \{0,1\}^{16}$. The default configuration uses **2,000 shots** for the canonical benchmark.

> **Note**: The measurement simulation is performed on a LOCAL Qiskit Aer simulator. This does NOT run on a real quantum computer or IBM quantum hardware.

---

## 9. How Bitstrings Become Waypoint Selections

Each measured bitstring encodes all 16 binary variables:
- **Bits 0–5**: Waypoint decision variables $x_0, \ldots, x_5$
- **Bits 6–15**: Slack variables $b_{j0}, b_{j1}$ for targets $j=0,\ldots,4$

Qiskit returns bitstrings with the **rightmost character = qubit 0**. The decoder maps character position $(n-1-i)$ to qubit $i$.

Only the **waypoint bits** (indices 0–5) are used for coverage evaluation. The slack bits are decoded separately but are not used in the coverage check.

---

## 10. Feasibility Checking

Each sampled waypoint selection is **independently evaluated** against the original coverage matrix:
$$\text{is\_feasible}(\mathbf{x}) = \left[\sum_i A_{ji} x_i \ge k \text{ for all } j\right]$$

**Infeasible samples are explicitly counted and reported.** They are never silently repaired or discarded — they contribute to the infeasible sample count.

---

## 11. Why QAOA May Fail to Sample the Optimum

At low depth $p$, QAOA may not reliably concentrate probability mass on optimal solutions:
1. **Limited expressibility**: $p=1$ circuits have limited ability to distinguish near-optimal from optimal states.
2. **Unconstrained search space**: The standard mixer does not preserve coverage feasibility, so many samples may be infeasible.
3. **Local minima in parameter landscape**: The classical optimizer may converge to a suboptimal angle configuration.
4. **Statistical noise**: Even at optimal parameters, the optimal solution may not be sampled in every finite-shot experiment.

---

## 12. Why This Does Not Prove Quantum Advantage

- The simulation runs on a **classical computer** (Qiskit Aer statevector simulator).
- For 16 qubits, this is a small problem tractable by classical exact methods in milliseconds.
- QAOA at $p=1$ is a heuristic with no theoretical worst-case approximation guarantees for this problem class.
- Demonstrating quantum advantage requires a problem size and circuit depth beyond classical simulation capability — not achievable on this instance.

