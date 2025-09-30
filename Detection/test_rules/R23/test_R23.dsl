rule R23 "EarlyStopping Not Used in Model.fit":
    condition:
        exists call in AST: (
            isFitCall(call)
            and not hasEarlyStoppingCallback(call)
        )
    action:
        report "Model.fit() called without EarlyStopping callback at line {lineno}"
