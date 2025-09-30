rule R22 "No Scaling Before Scale Sensitive Operations":
    condition:
        exists sub in AST: (
            isScaleSensitiveFit(sub, variable_ops)
            and not hasPrecedingScaler(sub, scaled_vars)
            and not isPartOfValidatedPipeline(sub)
        )
    action: report "Call to a sensitive function detected without prior scaling; consider applying a scaler (e.g., StandardScaler) before executing scale-sensitive operations at line {lineno}"
