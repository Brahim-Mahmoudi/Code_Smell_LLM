rule R14 "Dataframe Conversion API Misused":
    condition:
        exists sub in AST: (
            isValuesAccess(sub)
            and isDataFrameVariable(get_base_name(sub), sub)
        )
    action: report "Avoid using .values on DataFrames. Use .to_numpy() instead at line {lineno}"
