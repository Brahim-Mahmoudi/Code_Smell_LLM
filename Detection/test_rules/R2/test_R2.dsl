rule R2 "Random Seed Not Set":
  condition: 
    (
      exists call in AST: (
        isRandomCall(call)
        and not seedSet(call)
      )
    )
    or
    (
      exists algo in AST: (
        isSklearnRandomAlgo(algo)
        and not hasRandomState(algo)
      )
    )
  action: report "Random Seed Not Set at line {lineno}"
