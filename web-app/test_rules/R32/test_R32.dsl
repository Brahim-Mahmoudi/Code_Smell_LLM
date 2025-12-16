rule R32 "Overspecified Sampling Controls":
    condition:
        exists node in AST: (
            hasOverspecifiedSampling(node) )
    action:
        report "Overspecified sampling at line {lineno}"