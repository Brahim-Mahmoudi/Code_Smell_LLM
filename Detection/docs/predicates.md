##  Predicate Library

The DSL uses semantic predicates over AST nodes. Below is a list of predicates used across the rules:

### General AST Analysis
- `exists ... in AST: (...)`
- `count(...)`
- `not (...)`
- `and`, `or`, etc.

# Predicate Descriptions

## Model & Fit

- `isModelFitPresent(node)`  
  Returns True if the AST contains a `.fit()` call.

- `isFitCall(node)`  
  Returns True if the given node is a `.fit()` method call.

- `isMLMethodCall(node)`  
  Detects if the call is to a known ML model constructor (e.g., `RandomForestClassifier`).

- `hasEarlyStoppingCallback(node)`  
  Returns True if the `callbacks` argument of `.fit()` includes `EarlyStopping`.

- `hasExplicitHyperparameters(node)`  
  Returns True if the call explicitly sets at least one hyperparameter (via keyword arguments).

## Data Pipelines

- `pipelineUsed(node)`  
  Returns True if the given node is part of a pipeline call (e.g., `make_pipeline`, `Pipeline`).

- `pipelineUsedGlobally(node)`  
  Returns True if the entire AST contains a pipeline definition.

- `usedBeforeTrainTestSplit(node)`  
  Returns True if the given transformation is called before a `train_test_split`.

## Randomness / Determinism

- `isRandomCall(node)`  
  Detects usage of random functions across `random`, `numpy`, `torch`, or `tensorflow`.

- `seedSet(node)`  
  Returns True if the call sets a random seed (e.g., `np.random.seed`, `torch.manual_seed`).

- `isSklearnRandomAlgo(node)`  
  Detects usage of scikit-learn algorithms that rely on randomness.

- `hasRandomState(node)`  
  Checks if a call to a sklearn model includes the `random_state` parameter.

- `customCheckTorchDeterminism(ast_node)`  
  Returns True if torch is used and deterministic algorithms are not enabled.

## PyTorch / TensorFlow

- `isEvalCall(node)`  
  Returns True if the node calls `.eval()` on a model.

- `hasLaterTrainCall(node)`  
  Checks if there is a subsequent call to `.train()` or `optimizer.step()` after `.eval()`.

- `isForwardCall(node)`  
  Detects calls to `self.module.forward()` in PyTorch modules.

- `isLossBackward(node)`  
  Returns True if the node is a `.backward()` call.

- `hasPrecedingZeroGrad(node)`  
  Checks if `.zero_grad()` (or `clear_grad()` in Paddle) occurs before `.backward()`.

- `isPytorchTensorUsage(node)`  
  Detects operations on known PyTorch tensor variables (e.g., `.matmul()`).

- `isModelCreation(node)`  
  Detects creation of a known model object (e.g., `torch.nn.Linear(...)`).

- `isMemoryFreeCall(node)`  
  Returns True if memory release APIs like `.detach()` or `clear_session()` are used.

- `isLog(node)`  
  Returns True if the call is `tf.log(...)`.

- `hasMask(node)`  
  Returns True if the input to `tf.log` is wrapped in `tf.clip_by_value`, i.e., masked.

## DataFrame / Pandas

- `isDataFrameMerge(node)`  
  Returns True if the node is a call to `.merge()` on a pandas DataFrame.

- `singleParam(node)`  
  Returns True if the function call has only one argument or keyword.

- `isApiMethod(node)`  
  Detects calls to APIs that require reassignment or `inplace=True`.

- `hasInplaceTrue(node)`  
  Returns True if `inplace=True` is set.

- `isResultUsed(node)`  
  Returns True if the result of the call is used (assigned, returned, passed).

- `isPandasReadCall(node)`  
  Returns True if the node is a call to a pandas data loading function.

- `hasKeyword(node, kw)`  
  Checks whether a keyword argument with name `kw` is present.

- `isDataFrameVariable(var, node)`  
  Determines whether a variable is a pandas DataFrame within the node’s scope.

- `isSubscript(node)`  
  Returns True if the node is a subscript (e.g., `df[...]`).

- `get_base_name(node)`  
  Recursively extracts the base variable name of an expression.

- `usesIterrows(node)`  
  Detects use of the inefficient `.iterrows()` method.

- `usesItertuples(node)`  
  Detects use of `.itertuples()` (more efficient than `.iterrows()`).

- `isValuesAccess(node)`  
  Returns True if accessing `.values` of a DataFrame.

- `isDataFrameColumnAssignment(node)`  
  Detects assignments like `df["col"] = ...`.

- `isAssignedLiteral(node, value)`  
  Returns True if a literal value is assigned (e.g., `x = 0`).

## Numpy / Math

- `isCompare(node)`  
  Returns True if the node is a comparison (e.g., `a == b`).

- `hasNpNanComparator(node)`  
  Detects comparisons against `np.nan`.

- `isDotCall(node)`  
  Returns True if the node is a call to `np.dot()`.

- `isMatrix2D(node)`  
  Returns True if the function call takes two arguments (typically a 2D matrix op).

## Scaling / Metrics

- `isScaleSensitiveFit(node, vars)`  
  Returns True if `.fit()` is called on a model sensitive to data scaling.

- `hasPrecedingScaler(node, vars)`  
  Returns True if the data used in a `.fit()` call has been scaled.

- `isPartOfValidatedPipeline(node)`  
  Returns True if the operation is inside a pipeline with scaling + sensitive model.

- `isMetricCall(node)`  
  Returns True if the node is a metric function call.

- `isThresholdDependent(node)`  
  Returns True if the metric is threshold-dependent (e.g., precision, recall).

- `isThresholdIndependent(node)`  
  Returns True for metrics like `mean_squared_error` or `roc_auc_score`.

## Looping

- `isForLoop(node)`  
  Returns True if the node is a `for` loop.

- `isFunctionDef(node)`  
  Returns True if the node defines a function.

- `hasConstantAndConcatIntersection(node)`  
  Returns True if the block mixes `tf.constant()` and `tf.concat()`.

- `usesPythonLoopOnTensorFlow(node)`  
  Returns True if a native Python loop is used on a TensorFlow tensor.

