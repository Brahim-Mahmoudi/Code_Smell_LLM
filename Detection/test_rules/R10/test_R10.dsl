rule R10 "Memory Not Freed":
    condition:
        (
            exists usage in AST: (
                isPytorchTensorUsage(usage) 
                or isModelCreation(usage)
            )
        )
        and not (
            exists freecall in AST: (
                isMemoryFreeCall(freecall)
            )
        )
    action: report "Memory clearing API not used. Consider calling .detach() for PyTorch or tf.keras.backend.clear_session() for TensorFlow at line"
