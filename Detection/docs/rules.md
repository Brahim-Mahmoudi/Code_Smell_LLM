## Available Rules

SpecDetect4LLM supports detection of 5 LLM Integration code smells:

| Rule ID | Name | ID | Detection Category | Detection Explanation |
|---------|------|------|---------------------|----------------------|
| R25 | LLM Temperature Not Explicitly Set | TNES | 1(Easily detectable statically) | [Detection Explanation](Rules/R25.md) |
| R26 | LLM Version Pinning Not Explicitly Set Read |NMVP| 2 (Implicit config) | [Detection Explanation](Rules/R26.md) |
| R27 | LLM With No System Message | NSM | 2 (Implicit config) |  [Detection Explanation](Rules/R27.md) |
| R28 | LLM Calls Without Bounded Metrics | UMM | 1(Easily detectable statically) | [Detection Explanation](Rules/R28.md) |
| R29 | No Structured Output in Pipeline | NSO | 2 (Implicit config) | [Detection Explanation](Rules/R29.md) |
| R30 | Reasoning Effort Not Explicitly Set | RENES | 1(Easily detectable statically) | [Detection Explanation](Rules/R30.md) |
| R31 | Raw Vision Payload |  RVP |2 (Implicit config)  | [Detection Explanation](Rules/R31.md) |
| R32 | Overspecified Sampling Parameters | OSP | 1(Easily detectable statically) | [Detection Explanation](Rules/R32.md) |
| R33 | Anonymous Inference Cal |  AIC |2 (Implicit config) | [Detection Explanation](Rules/R33.md) |


---

### Detection Categories

- **1 Easily detectable statically**: Detectable through static patterns (e.g., AST traversal, syntactic rules). Includes API misuses, explicit constructs, and default values.
- **2 Implicit configuration or dynamic behavior**: Involves logic spread across functions or configuration not directly visible. Requires interprocedural analysis or contextual understanding.
- **3 Static detection insufficient**: Requires dynamic or hybrid analysis. Often relies on runtime behavior, data flow, or execution context.

---

In practice, static detection offers **a sound approximation** of these smells, though **dynamic or hybrid analysis** would improve precision.

Overall, SpecDetect4LLM demonstrates that a wide range of LLM Integration code smells — including those traditionally seen as dynamic — can be **effectively approximated via static analysis**, thanks to designed detection rules and interprocedural reasoning.
