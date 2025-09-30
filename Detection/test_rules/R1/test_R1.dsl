rule R1 "Broadcasting Feature Not Used":
    condition:
        exists sub in AST: (
            isTfTile(sub)
        )
    action: report "Call to tf.tile detected; consider using broadcasting instead for improved memory efficiency at line {lineno}"
