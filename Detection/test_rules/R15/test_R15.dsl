rule R15 "Merge API Parameter Not Explicitly Set":
    condition: exists call in AST: (
        isDataFrameMerge(call)
        and singleParam(call)
    )
    action: report "Specify 'on' or 'left_on/right_on' when using merge() at line {lineno}"
