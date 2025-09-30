rule R24 "Index Column Not Explicitly Set in DataFrame Read":
    condition:
        exists call in AST: (
            isPandasReadCall(call)
            and not hasKeyword(call, "index_col")
        )
    action:
        report "pd.read_… called without ‘index_col’; consider specifying index_col to avoid implicit integer indexing at line {lineno}"