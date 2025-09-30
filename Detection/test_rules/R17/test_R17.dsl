rule R17 "Unnecessary Iteration":
    condition:
        exists sub in AST: (
            isForLoop(sub)
            and (
                (usesIterrows(sub.iter) and isDataFrameVariable(get_base_name(sub.iter), sub.iter))
                or (usesItertuples(sub.iter) and isDataFrameVariable(get_base_name(sub.iter), sub.iter))
                or usesPythonLoopOnTensorFlow(sub)
            )
        )
    action: report "Unnecessary iteration detected; consider using vectorized operations (e.g., DataFrame.add, tf.reduce_sum) for efficiency at line {lineno}"
