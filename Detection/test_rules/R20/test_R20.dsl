rule R20 "Chain Indexing":
    condition:
        exists sub in AST: (
            isSubscript(sub)
            and isChainedIndexingBase(sub)
            and isDataFrameVariable(get_base_name(sub.value), sub)
        )
    action: report "Avoid chained indexing in DataFrames at line {lineno}; use df.loc[]"
