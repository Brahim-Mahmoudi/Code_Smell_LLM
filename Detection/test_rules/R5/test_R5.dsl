rule R5 "Hyperparameter not Explicitly Set":
    condition:
        exists call in AST: (
            isMLMethodCall(call)
            and not hasExplicitHyperparameters(call)
        )
    action: report "Hyperparameter not explicitly set at line {lineno}"
