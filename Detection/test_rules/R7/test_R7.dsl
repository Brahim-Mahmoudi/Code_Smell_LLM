rule R7 "Missing the Mask of Invalid Value":
    condition:
        exists call in AST: (
            isLog(call)
            and not hasMask(call)
        )
    action: report "Missing mask for tf.log at line {lineno}"
