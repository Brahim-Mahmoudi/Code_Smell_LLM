rule R6 "Deterministic Algorithm Option Not Used":
    condition:
        customCheckTorchDeterminism(ast_node)
    action: report "Deterministic Algorithm Option Not Used"
