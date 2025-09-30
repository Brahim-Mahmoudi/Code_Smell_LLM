rule R21 "Columns and DataType Not Explicitly Set":
    condition:
        exists sub in AST: (
            isPandasReadCall(sub)
            and not hasKeyword(sub, "dtype")
            and not hasKeyword(sub, "names")
        )
    action: report "Call to a pd.read function without the 'dtype' parameter; consider specifying dtype to ensure explicit column type handling at line {lineno}"
