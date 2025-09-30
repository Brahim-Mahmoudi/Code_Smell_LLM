rule R3 "TensorArray Not Used":
    condition: 
        exists block in AST: (
            (isForLoop(block) or isFunctionDef(block))
            and hasConstantAndConcatIntersection(block)
        )
    action: report "TensorArray Not Used at line {lineno}"