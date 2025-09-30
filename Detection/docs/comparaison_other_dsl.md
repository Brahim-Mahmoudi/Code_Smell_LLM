## Comparative Specification of Rule R5 — *Hyperparameter Not Explicitly Set* with several DSL

To illustrate the benefits of our DSL, we present a comparative specification of the same rule — **R5: _Hyperparameter Not Explicitly Set_** — using three tools: **SpecDetect4AI DSL**, **CodeQL**, and **Semgrep**.

This rule aims to detect machine learning model instantiations (e.g., `SVC`) where important hyperparameters (such as `random_state`) are not explicitly set.

---

###  SpecDetect4AI DSL

```dsl
rule R5 "Hyperparameter Not Explicitly Set":
    condition:
        exists call in AST: (
            isMLMethodCall(call)
            and not hasExplicitHyperparameters(call)
        )
    action:
        report "Hyperparameters not explicitly set"
```

This DSL rule uses reusable semantic predicates (e.g., isMLMethodCall, hasExplicitHyperparameters) that encapsulate ML domain knowledge. It abstracts away low-level AST traversal and enables declarative, modular, and scalable rule definitions tailored to AI workflows.


###  CodeQL DSL

```
import python

from CallExpr call, Function func
where
  func.getName() = "SVC" and
  call.getCallee() instanceof RefExpr and
  call.getCallee().(RefExpr).getId().getName() = "SVC" and
  not exists(Argument arg |
    arg = call.getArg("random_state")
  )
select call, "SVC called without setting random_state"
```

Although CodeQL is expressive, expressing this rule requires detailed knowledge of the AST and Python semantics. Crucially, extending the rule to cover other models (e.g., RandomForestClassifier, GradientBoostingClassifier) requires manually listing each constructor and duplicating logic — making the rule hard to maintain as APIs evolve.


###  Semgrep DSL

```
rules:
  - id: svc-missing-random-state
    languages: [python]
    message: "Possible missing random_state in SVC call"
    severity: WARNING
    pattern: |
      SVC(...)

```

Semgrep supports shallow syntactic matching but lacks the ability to reason semantically or detect the absence of keyword arguments like random_state. This pattern would match all calls to SVC(...), even when hyperparameters are provided, making it unreliable for precise ML analysis.