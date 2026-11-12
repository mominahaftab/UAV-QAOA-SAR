# Academic & Technical References

## 1. Quantum Optimization & QAOA
1. **Lee, S., et al. (2026).**
   *Quantum-Based k-Coverage Optimization for UAV-Aided Search and Rescue Missions.*
   arXiv:2609.01930 (preprint).
   - Foundational formulation of $k$-coverage multi-UAV waypoint selection mapped to quantum optimization algorithms.

2. **Farhi, E., Goldstone, J., & Gutmann, S. (2014).**
   *A Quantum Approximate Optimization Algorithm.*
   arXiv:1411.4028.
   - Defines the standard QAOA framework using alternating phase separation ($e^{-i \gamma H_C}$) and mixer ($e^{-i \beta H_M}$) Hamiltonians.

3. **Lucas, A. (2014).**
   *Ising formulations of many NP problems.*
   *Frontiers in Physics*, 2, 5. doi:10.3389/fphy.2014.00005.
   - Outlines quadratic unconstrained binary optimization (QUBO) and Ising Hamiltonian mappings for fundamental NP-hard combinatorial optimization problems, including exact cover and set cover with penalty functions.

4. **Glover, F., Kochenberger, G., & Hennig, R. (2019).**
   *A Tutorial on Formulating and Solving Problems with QUBO.*
   arXiv:1811.11538.
   - Practical techniques for converting inequality constraints into quadratic penalties via slack variables and penalty multiplier selection.

5. **Hadfield, S., Wang, Z., O'Gorman, B., Rieffel, E. G., Venturelli, D., & Biswas, R. (2019).**
   *From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz.*
   *Algorithms*, 12(2), 34.
   - Explores domain-preserving mixer Hamiltonians and constrained quantum optimization.

## 2. UAV Search-and-Rescue (SAR) & Multi-Coverage
1. **Erdos, D., Erdos, A., & Watkins, S. E. (2013).**
   *An Experimental UAV System for Search and Rescue Applications.*
   *IEEE Transactions on Aerospace and Electronic Systems*.
   - Practical sensing geometry, footprint calculation, and waypoint distribution requirements in aerial SAR scenarios.

2. **Vakhitov, A., et al. (2019).**
   *Probabilistic Multi-Coverage Trajectory Optimization for Aerial Surveying.*
   - Models sensor footprint overlap, multi-angle view redundancy ($k$-fold coverage), and minimum waypoint selection under false-alarm / detection uncertainty.

3. **Cardei, M., & Du, D. Z. (2005).**
   *Improving wireless sensor network lifetime through power aware organization.*
   *ACM Wireless Networks*.
   - Foundational concepts of $k$-coverage formulations in spatial sensor networks and discrete geometry cover matrices.

## 3. Mathematical Programming & Optimization Toolkits
1. **SciPy Optimization (`scipy.optimize.milp`):**
   - Exact Mixed-Integer Linear Programming solver using HiGHS branch-and-cut for binary integer linear programs (BILP).
   - Official URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html

2. **Qiskit Documentation (Qiskit 1.x / 2.x):**
   - Core Circuit Architecture: `qiskit.circuit.QuantumCircuit`, `qiskit.quantum_info.SparsePauliOp`
   - Primitives: `qiskit.primitives.StatevectorSampler` and `qiskit_aer.AerSimulator`
   - Ansätze: `qiskit.circuit.library.QAOAAnsatz`
   - Official URL: https://docs.quantum.ibm.com/
