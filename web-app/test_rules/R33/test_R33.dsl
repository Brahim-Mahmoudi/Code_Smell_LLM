rule R33 "Anonymous Inference Call":
    condition:
        exists node in AST: (
            isTextGeneratingCall(node) and hasMultiUserContext(node) and not hasUserAttribution(node) )
    action:
        report "Anonymous Inference Call at line {lineno}"