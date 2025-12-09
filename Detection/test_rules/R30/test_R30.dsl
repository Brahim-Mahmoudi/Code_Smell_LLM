rule R30 "No Structured Output in Pipeline":
    condition:
        exists node in AST: (
            isReasoningModelCall(node) and hasNoReasoningEffort(node)
        )
    action: report "Reasoning model call without explicit reasoning effort parameter at line {lineno}"
