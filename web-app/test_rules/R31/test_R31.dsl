rule R31 "Raw Vision Payload (RVP)":
    condition:
        exists node in AST: (
            isVisionModelCall(node) and hasImageContent(node) and not hasImagePreprocessing(node) and not hasExplicitDetailLevel(node)
        )
    action: report "Unbounded vision payloads at line {lineno}"
