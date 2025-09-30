## Available Rules

SpecDetect4AI supports detection of 24 AI-specific code smells, grouped by ML concern:

| Rule ID | Name | Detection Category | Detection Explanation |
|---------|------|---------------------|----------------------|
| R1 | Broadcasting Feature Not Used | 1 (Easily detectable statically) | [Detection Explanation](Rules/R1.md) |
| R2 | Random Seed Not Set | 2 (Implicit config) | [Detection Explanation](Rules/R2.md) |
| R3 | TensorArray Not Used | 1(Easily detectable statically) | [Detection Explanation](Rules/R3.md) |
| R4 | Training / Evaluation Mode Improper Toggling | 2 (Dynamic behavior) | [Detection Explanation](Rules/R4.md) |
| R5 | Hyperparameter Not Explicitly Set | 2 (Implicit config) | [Detection Explanation](Rules/R5.md) |
| R6 | Deterministic Algorithm Option Not Used | 2 (Implicit config) | [Detection Explanation](Rules/R6.md) |
| R7 | Missing the Mask of Invalid Value (e.g., in `tf.log`) | 3 (Static detection insufficient) | [Detection Explanation](Rules/R7.md) |
| R8 | PyTorch Call Method Misused | 1(Easily detectable statically) | [Detection Explanation](Rules/R8.md) |
| R9 | Gradients Not Cleared before Backward Propagation | 1(Easily detectable statically) | [Detection Explanation](Rules/R9.md) |
| R10 | Memory Not Freed | 1(Easily detectable statically) | [Detection Explanation](Rules/R10.md) |
| R11 | Data Leakage (fit_transform before split) | 3 (Static detection insufficient) | [Detection Explanation](Rules/R11.md) |
| R11bis | Data Leakage (no pipeline in presence of model.fit) | 3 (Static detection insufficient) | [Detection Explanation](Rules/R11.md) |
| R12 | Matrix Multiplication API Misused (np.dot vs np.matmul) | 1(Easily detectable statically) | [Detection Explanation](Rules/R12.md) |
| R13 | Empty Column Misinitialization | 1(Easily detectable statically) | [Detection Explanation](Rules/R13.md) |
| R14 | Dataframe Conversion API Misused (e.g., `.values`) | 1(Easily detectable statically) | [Detection Explanation](Rules/R14.md) |
| R15 | Merge API Parameter Not Explicitly Set | 1(Easily detectable statically) | [Detection Explanation](Rules/R15.md) |
| R16 | API Misuse (e.g., missing inplace or reassignment) | 1(Easily detectable statically) | [Detection Explanation](Rules/R16.md) |
| R17 | Unnecessary Iteration | 1(Easily detectable statically) | [Detection Explanation](Rules/R17.md) |
| R18 | NaN Comparison (`== np.nan`) | 1(Easily detectable statically) | [Detection Explanation](Rules/R18.md) |
| R19 | Threshold Validation Metrics Count | 3 (Easily detectable statically) | [Detection Explanation](Rules/R19.md) |
| R20 | Chain Indexing on DataFrames | 1(Easily detectable statically) | [Detection Explanation](Rules/R20.md) |
| R21 | Columns and DataType Not Explicitly Set in pd.read | 1(Easily detectable statically) | [Detection Explanation](Rules/R21.md) |
| R22 | No Scaling Before Scale-Sensitive Operations | 3 (Static detection insufficient) | [Detection Explanation](Rules/R22.md) |
| R23 | EarlyStopping Not Used in Model.fit | 2 (Implicit config) | [Detection Explanation](Rules/R23.md) |
| R24 | Index Column Not Explicitly Set in DataFrame Read | 1(Easily detectable statically) | [Detection Explanation](Rules/R24.md) |
| R25 | LLM Temperature Not Explicitly Set | 1(Easily detectable statically) | [Detection Explanation](Rules/R25.md) |
| R26 | LLM Version Pinning Not Explicitly Set Read | 2 (Implicit config) | [Detection Explanation](Rules/R26.md) |
| R27 | LLM With No System Message | 2 (Implicit config) | [Detection Explanation](Rules/R27.md) |
| R28 | LLM Calls Without Bounded Metrics | 1(Easily detectable statically) | [Detection Explanation](Rules/R28.md) |
| R29 | No Structured Output in Pipeline | 2 (Implicit config) | [Detection Explanation](Rules/R29.md) |

---

### Detection Categories

- **1 Easily detectable statically**: Detectable through static patterns (e.g., AST traversal, syntactic rules). Includes API misuses, explicit constructs, and default values.
- **2 Implicit configuration or dynamic behavior**: Involves logic spread across functions or configuration not directly visible. Requires interprocedural analysis or contextual understanding.
- **3 Static detection insufficient**: Requires dynamic or hybrid analysis. Often relies on runtime behavior, data flow, or execution context.

---

In practice, static detection offers **a sound approximation** of these smells, though **dynamic or hybrid analysis** would improve precision.

Overall, SpecDetect4AI demonstrates that a wide range of AI-specific code smells — including those traditionally seen as dynamic — can be **effectively approximated via static analysis**, thanks to designed detection rules and interprocedural reasoning.
