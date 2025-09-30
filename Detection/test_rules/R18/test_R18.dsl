rule R18 "NaN Comparison":
    condition:
        exists cmp in AST: ( isCompare(cmp) and hasNpNanComparator(cmp) )
    action: report "Do not compare with np.nan. Use df.isna() instead at line {lineno}"
