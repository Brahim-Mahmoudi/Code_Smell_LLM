rule R19 "Threshold Validation Metrics Count":
    condition:
        (count_dep = count(m in AST: isMetricCall(m) and isThresholdDependent(m)))
        and (count_indep = count(m in AST: isMetricCall(m) and isThresholdIndependent(m)))
        and (count_indep <= count_dep)
    action: report "Too many threshold-dependent metrics"
