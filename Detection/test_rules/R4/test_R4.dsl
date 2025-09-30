rule R4 "Training / Evaluation Mode Improper Toggling":
    condition:
        exists sub in AST: (
            isEvalCall(sub)
            and not hasLaterTrainCall(sub)
        )
    action: report "Training / Evaluation Mode Improper Toggling: .eval() call without subsequent .train() call at line {lineno}"
