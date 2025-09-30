# Evaluation Metrics Compared to Other Tools

This folder contains the evaluation files used to compute precision, recall, and F1-score for multiple tools detecting AI-specific code smells, including:

-  `mlpylint`
-  `CodeSmile`
-  `LLaMA 3 (8B)`
-  `LLaMA 3 (70B)`
-  `gpt-4.1-nano`
-  `gpt-4.1-mini`
-  `deepseek-r1`
-  `SpecDetect4AI` (our proposed approach)

The evaluation is performed against a manually labeled ground truth (`Evaluation/Comparison_Other_Tools/GroundTruth_Manual_Eval.xlsx`), described in (`docs/docs/Ground_Truth_Construction.md`)

---

## LLM Prompting Strategy for Code Smell Detection

To evaluate the performance of large language models (LLMs) on AI-specific code smell detection, we implemented structured prompt-based methods.

The full implementation are available in:

(`Evaluation/Comparison_Other_Tools/LLM_powered_ML_code_smell_static_detection_3_versions`)

---

## Objective

This evaluation aims to assess how well each tool detects AI-specific code smells compared to the ground truth, using standard classification metrics:

- **Precision (P)** = TP / (TP + FP)
- **Recall (R)** = TP / (TP + FN)
- **F1-Score** = 2 × (P × R) / (P + R)

All metrics are computed through using the script(`Evaluation/Comparison_Other_Tools/Evaluation_Precision_recall.py`)

---
