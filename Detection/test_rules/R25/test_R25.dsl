rule R25 "LLM Temperature Not Explicitly Set":
    condition:
        exists node in AST: (
            isLLMCall(node) and hasNoTemperatureParameter(node)
        )
    action:
        report "LLM call without explicit temperature parameter at line {lineno}"