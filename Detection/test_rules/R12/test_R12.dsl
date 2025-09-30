rule R12 "Matrix Multiplication API Misused":
    condition:
        exists sub in AST: (
            isDotCall(sub)
            and isMatrix2D(sub)
        )
    action: report "Use np.matmul() instead of np.dot() for matrices at line {lineno}" 