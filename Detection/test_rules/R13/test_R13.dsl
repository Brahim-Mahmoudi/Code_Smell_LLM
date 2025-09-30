rule R13 "Empty Column Misinitialization":
    condition:
        exists_assign sub in AST: (
            isDataFrameColumnAssignment(sub)
            and (
                isAssignedLiteral(sub, 0)
                or isAssignedLiteral(sub, "")
            )
        )
    action:
        report "Detected a new column initialized with a filler (0 or ''). Use np.nan or an empty Series instead at line {lineno}"
