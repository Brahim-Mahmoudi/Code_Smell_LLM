rule R16 "API Misuse":
    condition: exists call in AST: (
        isApiMethod(call)
        and not hasInplaceTrue(call)
        and not isResultUsed(call)
    )
    action: report "API call might be missing reassignment or inplace=True at line {lineno}"
