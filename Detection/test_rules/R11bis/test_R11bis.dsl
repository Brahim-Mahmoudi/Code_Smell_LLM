rule R11bis "Data Leakage (no pipeline in presence of model.fit)":
    condition:
        (
            isModelFitPresent(ast_node)
            and not pipelineUsedGlobally(ast_node)
            and isFitCall(sub)
            
        )
    action: report "Potential data leakage: model.fit() used without a pipeline at line {lineno}"
