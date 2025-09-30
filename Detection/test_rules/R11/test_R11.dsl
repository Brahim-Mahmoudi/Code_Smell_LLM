rule R11 "Data Leakage (fit_transform before split)":
    condition:
        exists call in AST: (
            isFitTransform(call)
            and not pipelineUsed(call)
            and usedBeforeTrainTestSplit(call)
        )
    action: report "Potential data leakage: fit_transform called before train/test split at line {lineno}"
