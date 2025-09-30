rule R8 "PyTorch Call Method Misused":
    condition:
        exists call in AST: (
            isForwardCall(call)
        )
    action: report "Use module() instead of forward() at line {lineno}"
