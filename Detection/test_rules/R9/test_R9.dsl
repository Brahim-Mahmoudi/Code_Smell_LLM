rule R9 "Gradients Not Cleared before Backward Propagation":
    condition:
        exists call in AST: (
            isLossBackward(call)
            and not hasPrecedingZeroGrad(call)
        )
    action: report "optimizer.zero_grad() not called before loss_fn.backward() at line {lineno}"

