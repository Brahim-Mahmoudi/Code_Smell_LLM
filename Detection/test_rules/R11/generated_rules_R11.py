import ast
import sys
import re
from typing import Optional

torch_imported = False
torch_used = False
deterministic_used = False
def reset_torch_flags():
    global torch_imported, torch_used, deterministic_used
    torch_imported = False
    torch_used = False
    deterministic_used = False

def track_torch_import(node):
    global torch_imported
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name == 'torch':
                torch_imported = True
    elif isinstance(node, ast.ImportFrom):
        if node.module and node.module.startswith('torch'):
            torch_imported = True

def useDeterministic(node):
    global deterministic_used
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute) and node.func.attr == 'use_deterministic_algorithms':
        if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value is True:
            deterministic_used = True
            return True
    return False

def isRelevantTorchCall(node):
    global torch_used
    if not isinstance(node, ast.Call):
        return False
    full_path = get_full_attr_path(node.func)
    if full_path and full_path.startswith("torch."):
        torch_used = True
        return True
    return False

def get_full_attr_path(expr):
    parts = []
    while isinstance(expr, ast.Attribute):
        parts.insert(0, expr.attr)
        expr = expr.value
    if isinstance(expr, ast.Name):
        parts.insert(0, expr.id)
    return '.'.join(parts)

def customCheckTorchDeterminism(ast_node):
    reset_torch_flags()
    for node in ast.walk(ast_node):
        track_torch_import(node)
        isRelevantTorchCall(node)
        useDeterministic(node)
    #log(f"torch_imported={torch_imported}, torch_used={torch_used}, deterministic_used={deterministic_used}")
    return torch_imported and torch_used and not deterministic_used

def report(message):
    print('REPORT:', message, flush=True)

def log(message):
    print('LOG:', message, flush=True)

def report_with_line(message, node):
    line = getattr(node, 'lineno', '?')
    report(message.format(lineno=line))

def add_parent_info(node, parent=None):
    node.parent = parent
    for child in ast.iter_child_nodes(node):
        add_parent_info(child, node)
    if parent is None:
       init_train_lines(node)

def gather_scale_sensitive_ops(ast_node):
    scale_sensitive_ops = {
        'PCA', 'SVC', 'SGDClassifier', 'SGDRegressor', 'MLPClassifier',
        'ElasticNet', 'Lasso', 'Ridge', 'KMeans', 'KNeighborsClassifier',
        'LogisticRegression'
    }
    ops = {}
    for stmt in ast.walk(ast_node):
        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                var_name = stmt.targets[0].id
                value = stmt.value
                if isinstance(value, ast.Call):
                    func = value.func
                    if isinstance(func, ast.Name) and func.id in scale_sensitive_ops:
                        ops[var_name] = func.id
                    elif isinstance(func, ast.Attribute) and func.attr in scale_sensitive_ops:
                        ops[var_name] = func.attr
    return ops

def isScaleSensitiveFit(call, variable_ops):
    if not isinstance(call, ast.Call):
        return False
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == 'fit'):
        return False
    callee = call.func.value
    if isinstance(callee, ast.Name):
        return callee.id in variable_ops
    return False

def isChainedIndexingBase(node):
    """
    Détecte les patterns chain indexing :
      - df[...][...]
      - df[...][...].method()
    Exclut .values[...] et .to_numpy()[...], .str[...] et .apply[...]
    """
    if not isinstance(node, ast.Subscript):
        return False

    value = node.value

    # Exclure accès .values, .to_numpy, .str, .apply, .dt, .map, etc.
    skip_attrs = {'values', 'to_numpy', 'str', 'dt', 'apply', 'map', 'squeeze'}

    # Traverse la chaîne d'attributs/méthodes entre le Subscript actuel et le précédent Subscript
    while isinstance(value, (ast.Attribute, ast.Call)):
        # Si on rencontre .str, .apply, etc. => on NE FLAG PAS
        if isinstance(value, ast.Attribute) and value.attr in skip_attrs:
            return False
        # Si c'est un appel de méthode, on check la fonction puis continue sur .value
        if hasattr(value, "value"):
            value = value.value
        elif hasattr(value, "func"):
            value = value.func
        else:
            break

    # Si on atteint un Subscript (df[...][...])
    if isinstance(value, ast.Subscript):
        return True

    return False
def get_scope_dataframe_vars(node):
    current = node
    while current is not None and not isinstance(current, (ast.FunctionDef, ast.Module)):
        current = getattr(current, 'parent', None)

    local_vars = set()
    series_vars = set()

    dataframe_creators = {
        'DataFrame', 'from_dict', 'from_records',
        'read_csv', 'read_json', 'read_excel',
        'read_sql', 'read_parquet', 'read_feather',
        'read_table', 'concat', 'merge'
    }
    series_creators = {'Series'}

    # 1. Détection explicite des DataFrames et Series Pandas
    for stmt in ast.walk(current):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id
            val = stmt.value

            if isinstance(val, ast.Call):
                func = val.func
                if isinstance(func, ast.Attribute):
                    # Ex: pd.read_csv(...) ou pd.Series(...)
                    if isinstance(func.value, ast.Name) and func.value.id == 'pd':
                        if func.attr in dataframe_creators:
                            local_vars.add(var_name)
                        elif func.attr in series_creators:
                            series_vars.add(var_name)
                    # Ex: pd.DataFrame.from_dict(...) ou pd.Series.from_array(...)
                    elif isinstance(func.value, ast.Attribute):
                        if func.value.attr == 'DataFrame' and getattr(func.value.value, 'id', '') == 'pd':
                            if func.attr in dataframe_creators:
                                local_vars.add(var_name)
                        if func.value.attr == 'Series' and getattr(func.value.value, 'id', '') == 'pd':
                            if func.attr in series_creators:
                                series_vars.add(var_name)
                elif isinstance(func, ast.Name):
                    if func.id == 'DataFrame':
                        local_vars.add(var_name)
                    elif func.id == 'Series':
                        series_vars.add(var_name)

    # 2. Propagation du statut DataFrame/Series via alias, accès colonne ou méthode pandas
    for stmt in ast.walk(current):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id
            val = stmt.value

            # df2 = df.method(...) ou df2 = df[...]
            if isinstance(val, (ast.Call, ast.Subscript)):
                base = get_base_name(val)
                # Cas DataFrame
                if base in local_vars:
                    local_vars.add(var_name)
                # Cas Series : accès à une colonne d'un DataFrame connu
                if base in local_vars and isinstance(val, ast.Subscript):
                    series_vars.add(var_name)
                # Cas alias de Series
                if base in series_vars:
                    series_vars.add(var_name)

    # 3. On EXCLUT explicitement les dict, defaultdict, list, set...
    for stmt in ast.walk(current):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id
            val = stmt.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name):
                if val.func.id in {'dict', 'defaultdict', 'list', 'set'}:
                    if var_name in local_vars:
                        local_vars.remove(var_name)
                    if var_name in series_vars:
                        series_vars.remove(var_name)

    # 4. Propagation simple des alias (alias = df ou alias = series)
    for stmt in ast.walk(current):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id
            val = stmt.value
            if isinstance(val, ast.Name):
                if val.id in local_vars:
                    local_vars.add(var_name)
                if val.id in series_vars:
                    series_vars.add(var_name)

    # Retourne l'union
    return local_vars | series_vars
def get_base_name(expr):
    while isinstance(expr, (ast.Subscript, ast.Attribute, ast.Call)):
        if hasattr(expr, "value"):
            expr = expr.value
        elif hasattr(expr, "func"):
            expr = expr.func
        else:
            break
    if isinstance(expr, ast.Name):
        return expr.id
    return None
def isDataFrameVariable(var, node):
    if isinstance(var, str):
        base = var
    else:
        base = get_base_name(var)
    if base is None:
        return False
    scope_vars = get_scope_dataframe_vars(node)
    return base in scope_vars

def gather_scaled_vars(ast_node):
    scaled_vars = set()
    known_scalers = {
        'StandardScaler','MinMaxScaler','RobustScaler','Normalizer',
        'MaxAbsScaler','PowerTransformer','QuantileTransformer'
    }

    scaler_map = {}
    for stmt in ast.walk(ast_node):
        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                var_name = stmt.targets[0].id
                value = stmt.value
                if isinstance(value, ast.Call):
                    func = value.func
                    # ex: scaler = StandardScaler()
                    if isinstance(func, ast.Name) and func.id in known_scalers:
                        scaler_map[var_name] = func.id
                    elif isinstance(func, ast.Attribute) and func.attr in known_scalers:
                        scaler_map[var_name] = func.attr

    for stmt in ast.walk(ast_node):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name):
                if isinstance(stmt.value, ast.Call):
                    if isinstance(stmt.value.func, ast.Attribute):
                        # ex: scaler.fit_transform(X) ou StandardScaler().fit_transform(X)
                        if stmt.value.func.attr == 'fit_transform':
                            base = stmt.value.func.value  # ex. ast.Name(id='scaler') ou ast.Call(...)
                            if isinstance(base, ast.Name):
                                # case: scaler.fit_transform(X)
                                if base.id in scaler_map:
                                    scaled_vars.add(target.id)
                                else:
                                    base_func = get_base_name(base)
                                    if base_func in known_scalers:
                                        scaled_vars.add(target.id)
                            else:
                                # case: StandardScaler().fit_transform(X)
                                base_func = get_base_name(base)
                                if base_func in known_scalers:
                                    scaled_vars.add(target.id)
    return scaled_vars

def call_uses_scaled_data(call_node, scaled_vars):
    if not isinstance(call_node, ast.Call):
        return False
    for arg in call_node.args:
        if isinstance(arg, ast.Name) and arg.id in scaled_vars:
            return True
    for kw in call_node.keywords:
        if isinstance(kw.value, ast.Name) and kw.value.id in scaled_vars:
            return True
    return False

def hasPrecedingScaler(call, scaled_vars=None):
    if scaled_vars:
        if call_uses_scaled_data(call, scaled_vars):
            return True
    scalers = {
        'StandardScaler', 'MinMaxScaler', 'RobustScaler', 'Normalizer',
        'MaxAbsScaler', 'PowerTransformer', 'QuantileTransformer'
    }
    current = call
    while current:
        current = getattr(current, 'parent', None)
        if isinstance(current, ast.Assign):
            value = current.value
            if isinstance(value, ast.Call):
                if isinstance(value.func, ast.Name) and value.func.id in scalers:
                    return True
                elif isinstance(value.func, ast.Attribute) and value.func.attr in scalers:
                    return True
    return False

def parse_pipeline_steps(node):
    funcs = []
    if isinstance(node, ast.Call):
        base_name = None
        if isinstance(node.func, ast.Name):
            base_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            base_name = node.func.attr
        if base_name:
            funcs.append(base_name)
        for arg in node.args:
            funcs.extend(parse_pipeline_steps(arg))
        for kw in node.keywords:
            funcs.extend(parse_pipeline_steps(kw.value))
    elif isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            funcs.extend(parse_pipeline_steps(elt))
    elif isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            funcs.extend(parse_pipeline_steps(value))
    elif isinstance(node, ast.keyword):
        funcs.extend(parse_pipeline_steps(node.value))
    return funcs

def isPartOfValidatedPipeline(call):
    scalers = {
        'StandardScaler', 'MinMaxScaler', 'RobustScaler', 'Normalizer',
        'MaxAbsScaler', 'PowerTransformer', 'QuantileTransformer'
    }
    sensitive_ops = {
        'PCA', 'SVC', 'SGDClassifier', 'SGDRegressor', 'MLPClassifier',
        'ElasticNet', 'Lasso', 'Ridge', 'KMeans', 'KNeighborsClassifier',
        'LogisticRegression'
    }
    parent = call
    while parent:
        if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name):
            if parent.func.id in {'Pipeline', 'make_pipeline'}:
                all_funcs = []
                for arg in parent.args:
                    all_funcs.extend(parse_pipeline_steps(arg))
                for kw in parent.keywords:
                    all_funcs.extend(parse_pipeline_steps(kw.value))
                has_scaler = any(func in scalers for func in all_funcs)
                has_sensitive_op = any(func in sensitive_ops for func in all_funcs)
                return (has_scaler and has_sensitive_op)
        parent = getattr(parent, 'parent', None)
    return False

def isDataFrameColumnAssignment(node):
    if not isinstance(node, ast.Assign):
        return False
    if len(node.targets) != 1:
        return False
    target = node.targets[0]
    if not isinstance(target, ast.Subscript):
        return False
    base_name = get_base_name(target.value)
    if not isDataFrameVariable(base_name, target.value):
        return False
    return True

def isAssignedLiteral(node, val):
    if not isinstance(node, ast.Assign):
        return False
    assigned_value = node.value
    if not isinstance(assigned_value, ast.Constant):
        return False
    return assigned_value.value == val

# Fonctions ajoutées (absentes du premier header initial)
def isDataFrameMerge(node):
    return (isinstance(node, ast.Call) and
            hasattr(node, 'func') and
            getattr(node.func, 'attr', '') == 'merge' and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id in get_scope_dataframe_vars(node))

def singleParam(node):
    return (len(node.args) + len(node.keywords)) == 1

def isApiMethod(node):
    """
    Détecte les appels d’API qui doivent :
      • soit être exécutés avec « inplace=True » (DataFrame Pandas),
      • soit ré‑affecter leur résultat (NumPy ou Pandas).

    Renvoie True si l’appel entre dans l’un de ces deux cas.
    """
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return False

    attr = node.func.attr
    base = get_base_name(node.func.value)

    # ----------  NumPy -------------------------------------------------
    numpy_methods_requiring_assignment = {'clip', 'sort', 'argsort'}
    if base == 'np' and attr in numpy_methods_requiring_assignment:
        return True

    # ----------  DataFrame Pandas -------------------------------------
    api_methods = {
        'drop', 'dropna', 'sort_values', 'replace',
        'clip', 'sort', 'argsort',
        'detach', 'cpu', 'clone', 'numpy',
        'transform', 'fit_transform',
        'traverse', 'strip', 'rstrip', 'lstrip', 'lower', 'upper'
    }
    if attr in api_methods and base in get_scope_dataframe_vars(node):
        return True

    return False


def hasInplaceTrue(node):
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg == 'inplace' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False

def isResultUsed(node):
    parent = getattr(node, 'parent', None)
    if isinstance(parent, ast.Expr):
        return False
    if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return True
    if isinstance(parent, ast.Return):
        return True
    if isinstance(parent, ast.Call):
        return True
    if isinstance(parent, (ast.Attribute, ast.Subscript)):
        return isResultUsed(parent)
    if isinstance(parent, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
        return True
    return False

def isBinOp(node):
    return isinstance(node, ast.BinOp)

def isTfTile(node):
    return (
    hasattr(node, 'func') and
    getattr(node.func, 'attr', '') == 'tile' and
    isinstance(node.func.value, ast.Name) and
    node.func.value.id == 'tf')

def isSubscript(node):
    return isinstance(node, ast.Subscript)

def extract_metric_name(node):
    if isinstance(node, ast.Call):
        if hasattr(node.func, 'attr') and node.func.attr == 'make_scorer':
            for arg in node.args:
                candidate = extract_metric_name(arg)
                if candidate is not None:
                    return candidate
            return None
        else:
            return extract_metric_name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None

def isMetricCall(node):
    return isinstance(node, ast.Call) and hasattr(node, 'func') and hasattr(node.func, 'attr')

def isThresholdDependent(node):
    metric_name = extract_metric_name(node)
    return metric_name in {
        'f1_score', 'precision_score', 'recall_score', 'accuracy_score',
        'specificity', 'balanced_accuracy', 'jaccard_score',
        'confusion_matrix', 'brier_score_loss'
    }

def isThresholdIndependent(node):
    metric_name = extract_metric_name(node)
    return metric_name in {
        'mean_absolute_error', 'mean_squared_error', 'root_mean_squared_error',
        'r2_score', 'max_error', 'mean_absolute_percentage_error',
        'roc_auc_score', 'roc_curve', 'pr_auc_score',
        'precision_recall_curve', 'log_loss', 'hinge_loss', 'auc'
    }

def isCompare(node):
    return isinstance(node, ast.Compare)

def hasNpNanComparator(node):
    if not isinstance(node, ast.Compare):
        return False
    for comparator in node.comparators:
        if isinstance(comparator, ast.Attribute):
            if (isinstance(comparator.value, ast.Name) and
                comparator.value.id == 'np' and
                comparator.attr == 'nan'):
                return True
    return False

def isNumpyVariable(node):
    return isinstance(node, ast.Name) and node.id == 'np'

def isValuesAccess(node):
    """
    Retourne True si le nœud est un accès d'attribut sur '.values'
    """
    return isinstance(node, ast.Attribute) and node.attr == 'values'

def isPandasReadCall(node):
    pandas_read_methods = {'read_csv', 'read_json', 'read_sql', 'read_table', 'read_excel', 'read_parquet'}
    if isinstance(node, ast.Call):
        # Cas pd.read_csv(...) ou pandas.read_csv(...)
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name)
                and node.func.value.id in {'pd', 'pandas'}
                and node.func.attr in pandas_read_methods):
                return True
        # Cas import direct : read_csv(...)
        if isinstance(node.func, ast.Name):
            if node.func.id in pandas_read_methods:
                return True
    return False
def hasKeyword(node, keyword_name):
   if isinstance(node, ast.Call):
       return any(kw.arg == keyword_name for kw in node.keywords)
   return False
def isDotCall(node):
   if not isinstance(node, ast.Call):
       return False
   if not isinstance(node.func, ast.Attribute):
       return False
   if node.func.attr != "dot":
       return False
   if not (isinstance(node.func.value, ast.Name) and node.func.value.id == "np"):
       return False
   return True
def isMatrix2D(node):
   if not isinstance(node, ast.Call):
       return False
   if len(node.args) != 2:
       return False
   return True
def isForLoop(node):
   return isinstance(node, ast.For)

def isFunctionDef(node):
   return isinstance(node, ast.FunctionDef)
def usesIterrows(node):
   return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'iterrows')
def usesItertuples(node):
   return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'itertuples')
def usesPythonLoopOnTensorFlow(loop_node):
    if not isinstance(loop_node, ast.For):
        return False
    
    # 1. Collecter toutes les variables assignées à un tenseur TensorFlow
    tf_vars = set()
    root = loop_node
    while hasattr(root, 'parent') and root.parent:
        root = root.parent

    for stmt in ast.walk(root):
        if isinstance(stmt, ast.Assign):
            if isinstance(stmt.value, ast.Call):
                func = stmt.value.func
                if isinstance(func, ast.Attribute):
                    base_name = get_base_name(func.value)
                    if base_name == 'tf':
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                tf_vars.add(target.id)

    # 2. Vérifier si la boucle fait des opérations sur ces variables TensorFlow
    for stmt in ast.walk(loop_node):
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
            if isinstance(stmt.value, ast.Subscript):
                var_name = get_base_name(stmt.value)
                if var_name in tf_vars:
                    return True
    return False
def isTensorFlowTensor(node):
   if isinstance(node, ast.Name):
       var_name = node.id.lower()
       return 'tf' in var_name or 'tensor' in var_name
   return False
def isRandomCall(call):
    if not isinstance(call, ast.Call):
        return False
    if isinstance(call.func, ast.Name) and call.func.id == 'DataLoader':
        for kw in call.keywords:
           if kw.arg == 'shuffle' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
               return True
    if not isinstance(call.func, ast.Attribute):
        return False

    rand_funcs = [
        ('np', 'random', {'random', 'rand', 'randn', 'randint', 'normal',
                          'uniform', 'sample', 'choice', 'shuffle', 'permutation'}),
        ('torch', None, {'rand', 'randn', 'randint', 'random'}),
        ('tf', 'random', {'normal', 'uniform', 'shuffle'}),
        ('random', None, {'randint', 'choice', 'shuffle', 'random', 'uniform'}),
        ('sklearn', 'utils', {'shuffle'}),
        ('sklearn', 'model_selection', {'train_test_split'}),
        ('sklearn', 'metrics', {'make_scorer'}),
        ('df', None, {'randomSplit'}),
    ]

    for lib, submodule, funcs in rand_funcs:
        if submodule:
            if (isinstance(call.func.value, ast.Attribute) and
                isinstance(call.func.value.value, ast.Name) and
                call.func.value.value.id == lib and
                call.func.value.attr == submodule and
                call.func.attr in funcs):
                return True
        else:
            if (isinstance(call.func.value, ast.Name) and
                call.func.value.id == lib and
                call.func.attr in funcs):
                return True

    return False

def seedSet(call):
    if not isinstance(call, ast.Call):
        return False
    if not isinstance(call.func, ast.Attribute):
        return False

    # np.random.seed(...)
    if (isinstance(call.func.value, ast.Attribute) and
        isinstance(call.func.value.value, ast.Name) and
        call.func.value.value.id == 'np' and
        call.func.value.attr == 'random' and
        call.func.attr == 'seed'):
        return True

    # tf.random.set_seed(...)
    if (isinstance(call.func.value, ast.Attribute) and
        isinstance(call.func.value.value, ast.Name) and
        call.func.value.value.id == 'tf' and
        call.func.value.attr == 'random' and
        call.func.attr == 'set_seed'):
        return True

    # torch.manual_seed(...)
    if (isinstance(call.func.value, ast.Name) and
        call.func.value.id == 'torch' and
        call.func.attr == 'manual_seed'):
        return True

    # random.seed(...)
    if (isinstance(call.func.value, ast.Name) and
        call.func.value.id == 'random' and
        call.func.attr == 'seed'):
        return True

    return False
    # np.random.seed(...)
    if (isinstance(call.func.value, ast.Attribute) and
        isinstance(call.func.value.value, ast.Name) and
        call.func.value.value.id == 'np' and
        call.func.value.attr == 'random' and
        call.func.attr == 'seed'):
        return True

    # tf.random.set_seed(...)
    if (isinstance(call.func.value, ast.Attribute) and
        isinstance(call.func.value.value, ast.Name) and
        call.func.value.value.id == 'tf' and
        call.func.value.attr == 'random' and
        call.func.attr == 'set_seed'):
        return True

    # torch.manual_seed(...)
    if (isinstance(call.func.value, ast.Name) and
        call.func.value.id == 'torch' and
        call.func.attr == 'manual_seed'):
        return True

    # random.seed(...)
    if (isinstance(call.func.value, ast.Name) and
        call.func.value.id == 'random' and
        call.func.attr == 'seed'):
        return True

    return False
def hasRandomState(call):
    if not isinstance(call, ast.Call):
        return False
    for kw in call.keywords:
        if kw.arg == 'random_state':
            if isinstance(kw.value, ast.Constant):
                return kw.value.value is not None
            return True  
    return False
def global_seed_set(ast_node, lib):
    seeds = set()
    for stmt in ast.walk(ast_node):
        if isinstance(stmt, ast.Call):
            if isinstance(stmt.func, ast.Attribute):
                # np.random.seed(...)
                if (isinstance(stmt.func.value, ast.Attribute) and
                    isinstance(stmt.func.value.value, ast.Name) and
                    stmt.func.value.value.id == 'np' and
                    stmt.func.value.attr == 'random' and
                    stmt.func.attr == 'seed'):
                    seeds.add('numpy')
                # torch.manual_seed(...)
                elif (isinstance(stmt.func.value, ast.Name) and
                      stmt.func.value.id == 'torch' and
                      stmt.func.attr == 'manual_seed'):
                    seeds.add('torch')
                # tf.random.set_seed(...)
                elif (isinstance(stmt.func.value, ast.Attribute) and
                      isinstance(stmt.func.value.value, ast.Name) and
                      stmt.func.value.value.id == 'tf' and
                      stmt.func.value.attr == 'random' and
                      stmt.func.attr == 'set_seed'):
                    seeds.add('tensorflow')
                # random.seed(...)
                elif (isinstance(stmt.func.value, ast.Name) and
                      stmt.func.value.id == 'random' and
                      stmt.func.attr == 'seed'):
                    seeds.add('random')
    return lib in seeds

def get_random_lib(call):
    if is_random_numpy_call(call):
        return 'numpy'
    if is_random_torch_call(call):
        return 'torch'
    if is_dataloader_with_shuffle(call):
        return 'torch'
    if is_random_tf_call(call):
        return 'tensorflow'
    if is_random_python_call(call):
        return 'random'
    return None

def is_random_numpy_call(stmt):
    if not isinstance(stmt, ast.Call):
        return False
    if not isinstance(stmt.func, ast.Attribute):
        return False
    return (isinstance(stmt.func.value, ast.Attribute) and
            isinstance(stmt.func.value.value, ast.Name) and
            stmt.func.value.value.id == 'np' and
            stmt.func.value.attr == 'random' and
            stmt.func.attr in {
                'random', 'rand', 'randn', 'randint', 'normal',
                'uniform', 'sample', 'choice', 'shuffle', 'permutation'
            })
def is_random_python_call(stmt):
    if not isinstance(stmt, ast.Call):
        return False
    if not isinstance(stmt.func, ast.Attribute):
        return False
    return (isinstance(stmt.func.value, ast.Name) and
            stmt.func.value.id == 'random' and
            stmt.func.attr in {'randint', 'choice', 'shuffle', 'random', 'uniform'})
def is_random_torch_call(stmt):
    if is_dataloader_with_shuffle(stmt):
       return True
    if not isinstance(stmt, ast.Call):
        return False
    if not isinstance(stmt.func, ast.Attribute):
        return False
    return (isinstance(stmt.func.value, ast.Name) and
            stmt.func.value.id == 'torch' and
            stmt.func.attr in {'rand', 'randn', 'randint', 'random'})
def is_random_tf_call(stmt):
    if not isinstance(stmt, ast.Call):
        return False
    if not isinstance(stmt.func, ast.Attribute):
        return False
    return (isinstance(stmt.func.value, ast.Attribute) and
            isinstance(stmt.func.value.value, ast.Name) and
            stmt.func.value.value.id == 'tf' and
            stmt.func.value.attr == 'random')
def isSklearnRandomAlgo(call):
    if not isinstance(call, ast.Call):
        return False
    if isinstance(call.func, ast.Name):
        return call.func.id in {
            'RandomForestClassifier', 'RandomForestRegressor',
            'KMeans', 'train_test_split', 'RandomizedSearchCV',
            'StratifiedKFold', 'ShuffleSplit', 'GridSearchCV','CatBoostregressor','SGD','Linear'
        }
    return False
def is_dataloader_with_shuffle(stmt):
    if not isinstance(stmt, ast.Call):
        return False
    if isinstance(stmt.func, ast.Name) and stmt.func.id == 'DataLoader':
        for kw in stmt.keywords:
            if kw.arg == 'shuffle' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    if isinstance(stmt.func, ast.Attribute) and stmt.func.attr == 'DataLoader':
        for kw in stmt.keywords:
            if kw.arg == 'shuffle' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False

def hasConstantAndConcatIntersection(block):
    import ast

    TF_INIT_FUNCS = {'Variable', 'ones', 'zeros', 'random_normal', 'random_uniform', 'fill'}
    MODIFICATION_FUNCS = {'concat', 'stack'}

    tf_constant_vars = set()
    ignore_vars = set()
    tensorarray_write_vars = set()

    # Vérifie si le block est dans une boucle (nécessaire pour ce smell)
    def is_inside_loop(node):
        while node:
            if isinstance(node, (ast.For, ast.While)):
                return True
            node = getattr(node, 'parent', None)
        return False

    # 1. Collecte les tf.constant assignés
    for node in ast.walk(block):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # assurer la référence vers parent
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute)
                and hasattr(call.func.value, 'id')
                and call.func.value.id == 'tf'):
                if call.func.attr == 'constant':
                    if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                        tf_constant_vars.add(node.targets[0].id)
                elif call.func.attr in TF_INIT_FUNCS:
                    if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                        ignore_vars.add(node.targets[0].id)

    # 2. Ignore si uniquement utilisé dans TensorArray.write
    for node in ast.walk(block):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "write" and isinstance(node.func.value, ast.Name):
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id in tf_constant_vars:
                        tensorarray_write_vars.add(arg.id)

    # 3. Détecte les modifications suspectes dans le bloc, UNIQUEMENT DANS UNE BOUCLE
    for node in ast.walk(block):
        # Assurer parent
        for child in ast.iter_child_nodes(node):
            child.parent = node

        # tf.concat / tf.stack
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute)
                and hasattr(call.func.value, 'id')
                and call.func.value.id == 'tf'
                and call.func.attr in MODIFICATION_FUNCS
                and is_inside_loop(node)):  # Seulement dans boucle
                involved_vars = set()
                for arg in call.args:
                    if isinstance(arg, ast.List):
                        involved_vars |= set(elt.id for elt in arg.elts if isinstance(elt, ast.Name))
                    elif isinstance(arg, ast.Name):
                        involved_vars.add(arg.id)
                smell_vars = (involved_vars & tf_constant_vars) - ignore_vars - tensorarray_write_vars
                if smell_vars:
                    return True

        # Opération arithmétique (+, *, etc.) sur tf.constant dans une boucle seulement
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and is_inside_loop(node):
            for side in [node.value.left, node.value.right]:
                if isinstance(side, ast.Name):
                    if side.id in tf_constant_vars and side.id not in ignore_vars and side.id not in tensorarray_write_vars:
                        return True

    # Aucune intersection détectée
    return False
def isMLMethodCall(call):
    if not isinstance(call, ast.Call):
        return False
    if isinstance(call.func, ast.Name):
        func_name = call.func.id
    elif isinstance(call.func, ast.Attribute):
        func_name = call.func.attr
    else:
        return False
    hyperparameter_functions = {
        # Scikit-Learn
        'KMeans', 'DBSCAN', 'AgglomerativeClustering',
        'RandomForestClassifier','RandomForestRegressor', 'GradientBoostingClassifier', 'AdaBoostClassifier',
        'LogisticRegression', 'LinearRegression', 'Lasso', 'Ridge',
        'SVC', 'SVR', 'DecisionTreeClassifier', 'DecisionTreeRegressor',
        'MLPClassifier', 'MLPRegressor',
        # PyTorch Optimizers
        'SGD', 'Adagrad', 'Adadelta', 'Adamax', 'RMSprop', 'Net',
        # TensorFlow Optimizers (et éventuellement des layers si pertinent)
        'Adam', 'Ftrl', 'Nadam', 'Adamax', 'Dense', 'Conv2D', 'LSTM',
        # XGBoost
        'XGBClassifier', 'XGBRegressor',
        # LightGBM
        'LGBMClassifier', 'LGBMRegressor'
        # LightGBM
        'Sequential'
    }
    return func_name in hyperparameter_functions
def hasExplicitHyperparameters(call):
    return len(call.keywords) > 0

def isLog(call):
    if not isinstance(call, ast.Call):
        return False
    if not isinstance(call.func, ast.Attribute):
        return False
    if hasattr(call.func.value, 'id') and call.func.value.id == 'tf' and call.func.attr == 'log':
        return True
    return False

def hasMask(call):
    if not isinstance(call, ast.Call):
        return False
    if not isLog(call):
        return False
    if len(call.args) == 0:
        return False
    arg = call.args[0]
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):
        if hasattr(arg.func.value, 'id') and arg.func.value.id == 'tf' and arg.func.attr == 'clip_by_value':
            return True
    return False

def isForwardCall(call):
    if not isinstance(call, ast.Call):
        return False
    if not isinstance(call.func, ast.Attribute):
        return False
    if call.func.attr != 'forward':
        return False

    # (NOUVEAU) Vérifie si on est dans la méthode __call__ d'une classe : autorisé => pas de smell
    node = call
    while hasattr(node, 'parent') and node.parent is not None:
        node = node.parent
        if isinstance(node, ast.FunctionDef) and node.name == '__call__':
            return False  # Autorisé dans __call__, donc pas un smell

    # Base de l'appel (self, self.block, model, etc)
    base = call.func.value
    while isinstance(base, ast.Attribute):
        base = base.value

    if isinstance(base, ast.Name):
        base_id = base.id
        # Accepte self
        if base_id == 'self':
            return True
        # Accepte toute variable qui ressemble à un modèle dans le code
        root = call
        while hasattr(root, 'parent') and root.parent is not None:
            root = root.parent
        for node in ast.walk(root):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == base_id:
                    val = node.value
                    if isinstance(val, ast.Call):
                        func = val.func
                        if isinstance(func, ast.Attribute):
                            if (
                                (isinstance(func.value, ast.Name) and func.value.id in {'torch', 'nn'})
                                or (isinstance(func.value, ast.Attribute) and func.value.attr == 'nn')
                            ):
                                return True
    # Optionnel : flag toute utilisation de .forward dans un fichier PyTorch
    root = call
    while hasattr(root, 'parent') and root.parent is not None:
        root = root.parent
    torch_present = False
    for node in ast.walk(root):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'torch':
                    torch_present = True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith('torch'):
                torch_present = True
    if torch_present:
        return True
    return False

def isRelevantLibraryCall(node):
    if not isinstance(node, ast.Call):
       return False
    base = get_base_name(node.func)
    return base in ['torch', 'numpy', 'random', 'transformers']

def hasManualSeed(node):
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute) and node.func.attr in {'manual_seed', 'set_seed', 'seed'}:
        return bool(node.args and isinstance(node.args[0], ast.Constant))
    return False

def isEvalCall(node):
    return (isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'eval')

def isTrainCall(node):
    return (isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'train')

def isOptimizerStep(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and getattr(node.func.value, 'id', None) == 'optimizer'
        and node.func.attr == 'step'
    )

train_lines = []

def init_train_lines(ast_node):
    global train_lines
    train_lines = []
    for stmt in ast.walk(ast_node):
        if (isTrainCall(stmt) or isOptimizerStep(stmt)) and hasattr(stmt, 'lineno'):
            train_lines.append(stmt.lineno)
    train_lines.sort()

def hasLaterTrainCall(node):
    if not hasattr(node, 'lineno'):
        return False

    node_line = node.lineno
    for tline in train_lines:
        if tline > node_line:
            return True
    return False

def isLossBackward(node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute):
        return False
    return node.func.attr == 'backward'

def isZeroGradCall(node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute):
        return False
    return node.func.attr == 'zero_grad'

def isClearGradCall(node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute):
        return False
    return node.func.attr == 'clear_grad'

def isPaddleEnvironment(root_node):
    """
    Détecte si l'AST contient un import de paddle,
    donc si l'on est dans un environnement Paddle.
    """
    import ast
    for stmt in ast.walk(root_node):
        # Case: import paddle
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name == 'paddle':
                    return True
        # Case: from paddle import <X>
        if isinstance(stmt, ast.ImportFrom):
            if stmt.module and 'paddle' in stmt.module:
                return True
    return False

def isInsideNoGrad(node):
    """
    Retourne True si le noeud se trouve dans un bloc `with torch.no_grad():`
    """
    current = node
    while getattr(current, 'parent', None) is not None:
        current = current.parent
        if isinstance(current, ast.With):
            for item in current.items:
                if isinstance(item.context_expr, ast.Call):
                    called = item.context_expr.func
                    if (isinstance(called, ast.Attribute)
                        and isinstance(called.value, ast.Name)
                        and called.value.id == 'torch'
                        and called.attr == 'no_grad'):
                        return True
    return False

def hasPrecedingZeroGrad(call):
    """
    Vérifie si backward() est précédé d'un appel zero_grad(), ou si on est
    dans un bloc no_grad(), ou si on est en environnement Paddle et qu'un
    clear_grad() (paddle) est présent *après* la ligne du backward.
    """
    import ast
    if isInsideNoGrad(call):
        return True

    if not hasattr(call, 'lineno'):
        return False
    node_line = call.lineno

    root_node = call
    while getattr(root_node, 'parent', None) is not None:
        root_node = root_node.parent

    if not isPaddleEnvironment(root_node):
        for stmt in ast.walk(root_node):
            if isZeroGradCall(stmt) and hasattr(stmt, 'lineno'):
                if stmt.lineno < node_line:
                    return True
        return False
    else:

        for stmt in ast.walk(root_node):
            if isZeroGradCall(stmt) and hasattr(stmt, 'lineno'):
                if stmt.lineno < node_line:
                    return True

        for stmt in ast.walk(root_node):
            if isClearGradCall(stmt) and hasattr(stmt, 'lineno'):
                if stmt.lineno > node_line:
                    return True

        return False

tracked_tensors = set()

pytorch_tensors = set()

def isPytorchTensorDefinition(node):
    """Register variables created via torch tensor creation functions."""
    global pytorch_tensors
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
        call = node.value
        if isinstance(call.func, ast.Attribute):
            # Catch torch.tensor(...) and torch.Tensor(...)
            if isinstance(call.func.value, ast.Name) and call.func.value.id == 'torch':
                if call.func.attr in {'tensor', 'Tensor'}:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            pytorch_tensors.add(target.id)
                            return True
    return False

def isPytorchTensorUsage(node):
    # Limite la détection aux variables connues comme tenseurs torch
    if not isinstance(node, ast.Call): return False
    if not isinstance(node.func, ast.Attribute): return False
    ops = {'matmul', 'add', 'mul', 'sub', 'div', 'mm'}
    if node.func.attr not in ops: return False
    if isinstance(node.func.value, ast.Name):
        var_name = node.func.value.id
        return var_name in pytorch_tensors
    return False



def isModelCreation(node):
    """
    Détecte la création d'un modèle ou d'une couche (Keras/PyTorch) même sans assignation explicite,
    y compris passé comme argument à une fonction/méthode (ex: append(Model(...))).
    """
    if not isinstance(node, ast.Call):
        return False
    # Liste élargie : tous les objets potentiellement coûteux en mémoire
    model_layer_names = {
        "Sequential", "Model",
        "Conv1D", "Conv2D", "Conv3D", "Dense", "LSTM", "GRU", "RNN",
        "LeakyReLU", "ReLU", "MaxPooling2D", "Flatten", "Dropout"
    }
    # Cas appel direct (ex: Sequential(...), Model(...))
    if isinstance(node.func, ast.Name) and node.func.id in model_layer_names:
        return True
    # Cas appel qualifié (ex: tf.keras.Sequential(...), tf.keras.Model(...))
    if isinstance(node.func, ast.Attribute) and node.func.attr in model_layer_names:
        return True
    return False


def isMemoryFreeCall(node):
    """Return True if the node represents a memory-freeing API call."""
    if isinstance(node, ast.Call):
        # Handle method calls like tensor.detach() or backend.clear_session()
        if isinstance(node.func, ast.Attribute):
            # PyTorch: tensor.detach()
            if node.func.attr == 'detach':
                return True
            # TensorFlow/Keras: clear_session() called as an attribute
            if node.func.attr == 'clear_session':
                # Check if this call is inside a loop (for memory freeing in loops)
                current = node
                in_loop = False
                while hasattr(current, "parent") and current.parent is not None:
                    if isinstance(current.parent, ast.For):
                        in_loop = True
                        break
                    current = current.parent
                return in_loop  # True if in a loop, False otherwise
        # Handle function calls like clear_session() imported directly
        elif isinstance(node.func, ast.Name):
            if node.func.id == 'clear_session':
                # Similar loop check for standalone clear_session()
                current = node
                in_loop = False
                while hasattr(current, "parent") and current.parent is not None:
                    if isinstance(current.parent, ast.For):
                        in_loop = True
                        break
                    current = current.parent
                return in_loop
    # Handle explicit deletions: `del var`
    if isinstance(node, ast.Delete):
        return True
    # Handle assigning a variable to None as a form of manual cleanup
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if (isinstance(target, ast.Name) 
                and isinstance(node.value, ast.Constant) 
                and node.value.value is None):
            return True
    return False


def isFitTransform(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'fit_transform'
    )

def pipelineUsed(node):
    current = node
    while current:
        if isinstance(current, ast.Call):
            if isinstance(current.func, ast.Name) and current.func.id in {'make_pipeline', 'Pipeline'}:
                return True
            if isinstance(current.func, ast.Attribute) and current.func.attr in {'fit', 'predict'}:
                base = get_base_name(current.func.value)
                if base in {'pipeline', 'clf'}:
                    return True
        current = getattr(current, 'parent', None)
    return False

def usedBeforeTrainTestSplit(node):
    if not hasattr(node, 'lineno'):
        return False
    fit_line = node.lineno
    root = node
    while getattr(root, 'parent', None):
        root = root.parent
    for sub in ast.walk(root):
        if isinstance(sub, ast.Call):
            if isinstance(sub.func, ast.Name) and sub.func.id == 'train_test_split':
                if hasattr(sub, 'lineno') and sub.lineno > fit_line:
                    return True
    return False

def pipelineUsedGlobally(ast_node):
    for node in ast.walk(ast_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {'Pipeline', 'make_pipeline'}:
                return True
    return False

def isModelFitPresent(ast_node):
    for node in ast.walk(ast_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "fit":
                return True
    return False

def isFitCall(node):
   return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fit"

def reportFitLine(msg, node):   report_with_line(msg, node)

def report_line(message, node):
   report_with_line(message, node)

def hasEarlyStoppingCallback(call):
   # return True if 'callbacks' exists and contains 'EarlyStopping'
   if not (isinstance(call, ast.Call) and hasKeyword(call, "callbacks")):
       return False
   for kw in call.keywords:
       if kw.arg == "callbacks" and "EarlyStopping" in ast.unparse(kw.value):
           return True
   return False

def isLLMCall(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False

    # Reconstitue le chemin de l'appel
    path = []
    f = node.func
    while isinstance(f, ast.Attribute):
        path.insert(0, f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        path.insert(0, f.id)
    call_tuple = tuple(path)
    # print("DBG_R25.isLLMCall:", call_tuple)

    # 1) Appels LLM explicites (OpenAI/Anthropic/…)
    EXACTS = {
        ("openai", "Completion", "create"),
        ("openai", "ChatCompletion", "create"),
        ("OpenAI", "completions", "create"),
        ("OpenAI", "chat", "completions", "create"),
        ("anthropic", "completions", "create"),
        ("anthropic", "messages", "create"),
        ("Anthropic", "completions", "create"),
        ("vertexai", "generative_models", "generate_content"),
        ("GenerativeModel", "generate_content"),
        ("cohere", "generate"),
        ("Client", "generate"),
    }
    if call_tuple in EXACTS:
        return True

    # 2) Suffixes client.*.create (inclut responses.create)
    SUFFIXES = {
        ("completions", "create"),
        ("messages", "create"),
        ("responses", "create"),
        ("chat", "completions", "create"),
    }
    for suf in SUFFIXES:
        if len(call_tuple) >= len(suf) and call_tuple[-len(suf):] == suf:
            return True

    # 3) LangChain : considérer les *constructeurs de modèles* comme LLM calls
    #    (ils portent temperature). On évite 'OpenAI()' non qualifié pour ne pas
    #    confondre avec le client OpenAI SDK.
    LANGCHAIN_LLM_CTORS = {
        "OpenAI",             # langchain.llms.OpenAI
        "ChatOpenAI",         # langchain_openai
        "ChatAnthropic",      # langchain_anthropic
        "ChatCohere",         # langchain_cohere
        "ChatVertexAI",       # langchain_google
        "HuggingFacePipeline" # langchain_huggingface
    }

    # a) Nom simple: ChatOpenAI(...)
    if isinstance(node.func, ast.Name) and node.func.id in LANGCHAIN_LLM_CTORS:
        return True

    # b) Chemin qualifié: langchain_openai.ChatOpenAI(...) ou x.y.ChatOpenAI(...)
    if isinstance(node.func, ast.Attribute) and node.func.attr in LANGCHAIN_LLM_CTORS:
        return True

    # 4) transformers.pipeline("text-generation", ...)
    if isinstance(f, ast.Name) and f.id == "pipeline":
        if node.args and isinstance(node.args[0], ast.Constant) and str(node.args[0].value) == "text-generation":
            return True

    # 5) variable = pipeline('text-generation'); variable(...)
    if isinstance(node.func, ast.Name):
        varname = node.func.id
        root = node
        while isinstance(getattr(root, "parent", None), ast.AST):
            root = root.parent
        if not isinstance(root, ast.AST):
            root = node
        call_line = getattr(node, "lineno", float("inf"))
        last_line = -1
        found_pipeline = False
        for n in ast.walk(root):
            if isinstance(n, ast.Assign) and getattr(n, "lineno", 0) < call_line:
                if any(isinstance(t, ast.Name) and t.id == varname for t in n.targets):
                    v = n.value
                    if isinstance(v, ast.Call):
                        vf = v.func
                        is_pipeline = (isinstance(vf, ast.Name) and vf.id == "pipeline") or \
                                      (isinstance(vf, ast.Attribute) and vf.attr == "pipeline")
                        if is_pipeline and v.args and isinstance(v.args[0], ast.Constant):
                            if str(v.args[0].value) == "text-generation" and getattr(n, "lineno", 0) > last_line:
                                last_line = getattr(n, "lineno", 0)
                                found_pipeline = True
        if found_pipeline:
            return True

    # 6) Gemini var-based
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"generate_content", "start_chat"}:
        return True

    return False


def hasNoTemperatureParameter(node: ast.AST) -> bool:
    """
    Retourne True IFF la température est ABSENTE (missing).
    """
    if not isinstance(node, ast.Call):
        return False  # pas un call

    # 1) Présence directe
    for kw in node.keywords:
        if kw.arg == "temperature":
            return False  # présente -> pas "missing"

    # 2) **kwargs
    for kw in node.keywords:
        if kw.arg is None:  # **kwargs
            val = kw.value

            # **{ ... }
            if isinstance(val, ast.Dict):
                has_temp = any(isinstance(k, ast.Constant) and k.value == "temperature" for k in val.keys)
                return not has_temp  # True si absent

            # **params (variable dict)
            if isinstance(val, ast.Name):
                varname = val.id

                # Racine sûre
                root = node
                while isinstance(getattr(root, "parent", None), ast.AST):
                    root = root.parent
                if not isinstance(root, ast.AST):
                    root = node

                call_line = getattr(node, "lineno", float("inf"))
                last_dict = None
                last_line = -1
                for n in ast.walk(root):
                    if isinstance(n, ast.Assign) and getattr(n, "lineno", 0) < call_line:
                        if any(isinstance(t, ast.Name) and t.id == varname for t in n.targets):
                            if isinstance(n.value, ast.Dict) and getattr(n, "lineno", 0) > last_line:
                                last_dict = n.value
                                last_line = getattr(n, "lineno", 0)

                if last_dict is not None:
                    has_temp = any(isinstance(k, ast.Constant) and k.value == "temperature" for k in last_dict.keys)
                    return not has_temp  # True si absent

                # On ne sait pas ce qu'il y a dans **params -> conservateur: missing
                return True

    # 3) Aucun indice de température -> missing
    return True

# --- Regex pour juger si un ID de modèle est "pinné" ---
_OPENAI_OK   = re.compile(r"-20\d{2}-\d{2}-\d{2}$")     # ...-YYYY-MM-DD (ex: gpt-4o-2024-11-20)
_ANTHROPIC_OK = re.compile(r"-20\d{6}$")                # ...-YYYYMMDD   (ex: claude-3-5-haiku-20241022)
_GEMINI_OK   = re.compile(r"-00\d$")                    # ...-001 / -002
_LATEST      = re.compile(r"(?:^|:)latest$")            # 'latest' ou ':latest'

def _is_str(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)

def _model_is_pinned(s: str) -> bool:
    s = s.strip()
    if _LATEST.search(s):
        return False
    if _OPENAI_OK.search(s) or _ANTHROPIC_OK.search(s) or _GEMINI_OK.search(s):
        return True
    return False

def _get_root(node: ast.AST) -> ast.AST:
    root = node
    while isinstance(getattr(root, "parent", None), ast.AST):
        root = root.parent
    return root if isinstance(root, ast.AST) else node

def _find_last_dict_assignment(root: ast.AST, varname: str, before_line: int) -> ast.Dict:
    last_dict, last_line = None, -1
    for n in ast.walk(root):
        if isinstance(n, ast.Assign) and getattr(n, "lineno", 0) < before_line:
            if any(isinstance(t, ast.Name) and t.id == varname for t in n.targets):
                if isinstance(n.value, ast.Dict) and getattr(n, "lineno", 0) > last_line:
                    last_dict, last_line = n.value, getattr(n, "lineno", 0)
    return last_dict

# --------------------------------------------------------------------
# R26 helpers (NOUVEAUX) — pas de recouvrement avec tes fonctions existantes
# --------------------------------------------------------------------

def isModelVersionedLLMCall(node: ast.AST) -> bool:
    """
    True si 'node' est un appel où le "model pinning" a un sens :
      - OpenAI/Anthropic: *.create(..., model=...)
      - Gemini: GenerativeModel("<model-id>")
      - HF Transformers: Auto*.from_pretrained(...)
      - Ollama: subprocess.run([... 'ollama','run','<model[:tag]>' ...]) ou shell string
    """
    if not isinstance(node, ast.Call):
        return False

    # Construire le chemin: openai.ChatCompletion.create -> ('openai','ChatCompletion','create')
    path = []
    f = node.func
    while isinstance(f, ast.Attribute):
        path.insert(0, f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        path.insert(0, f.id)
    call_tuple = tuple(path)

    # A) OpenAI / Anthropic
    exacts = {
        ("openai", "Completion", "create"),
        ("openai", "ChatCompletion", "create"),
        ("OpenAI", "completions", "create"),
        ("OpenAI", "chat", "completions", "create"),
        ("anthropic", "completions", "create"),
        ("anthropic", "messages", "create"),
        ("Anthropic", "completions", "create"),
    }
    if call_tuple in exacts:
        return True
    for suf in {("completions", "create"), ("messages", "create"), ("chat", "completions", "create")}:
        if len(call_tuple) >= len(suf) and call_tuple[-len(suf):] == suf:
            return True

    # B) Gemini — GenerativeModel("gemini-...")
    if call_tuple and call_tuple[-1] == "GenerativeModel":
        return True

    # C) HF Transformers — Auto*.from_pretrained(...)
    if isinstance(node.func, ast.Attribute) and node.func.attr == "from_pretrained":
        base = node.func.value
        if isinstance(base, ast.Name) and base.id in {
            "AutoModel", "AutoTokenizer", "AutoModelForCausalLM", "AutoModelForSeq2SeqLM",
            "AutoModelForTokenClassification", "AutoModelForMaskedLM"
        }:
            return True

    # D) Ollama via subprocess
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"run", "check_call"}:
        return True

    return False


def hasNoModelVersionPinning(node: ast.AST) -> bool:
    """
    True si l'appel n'est PAS pinné (alias, 'latest', pas de revision, etc.)
    """
    if not isinstance(node, ast.Call):
        return False

    # Reconstituer chemin
    path = []
    f = node.func
    while isinstance(f, ast.Attribute):
        path.insert(0, f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        path.insert(0, f.id)
    call_tuple = tuple(path)

    # 1) OpenAI / Anthropic — via model="..." ou **params
    # a) model="..."
    for kw in node.keywords:
        if kw.arg == "model" and _is_str(kw.value):
            return not _model_is_pinned(kw.value.value)

    # b) **params (dict litéral ou variable)
    for kw in node.keywords:
        if kw.arg is None:
            if isinstance(kw.value, ast.Dict):
                # **{...}
                for k, v in zip(kw.value.keys, kw.value.values):
                    if isinstance(k, ast.Constant) and k.value == "model" and _is_str(v):
                        return not _model_is_pinned(v.value)
            elif isinstance(kw.value, ast.Name):
                # **params (variable dict)
                root = _get_root(node)
                call_line = getattr(node, "lineno", float("inf"))
                d = _find_last_dict_assignment(root, kw.value.id, call_line)
                if isinstance(d, ast.Dict):
                    for k, v in zip(d.keys, d.values):
                        if isinstance(k, ast.Constant) and k.value == "model" and _is_str(v):
                            return not _model_is_pinned(v.value)

    # 2) Gemini — GenerativeModel("gemini-...")
    if call_tuple and call_tuple[-1] == "GenerativeModel":
        if node.args and _is_str(node.args[0]):
            return not _model_is_pinned(node.args[0].value)
        return True  # arg non-const → conservateur

    # 3) HF Transformers — from_pretrained(..., revision=?)
    if isinstance(node.func, ast.Attribute) and node.func.attr == "from_pretrained":
        base = node.func.value
        if isinstance(base, ast.Name) and base.id in {
            "AutoModel", "AutoTokenizer", "AutoModelForCausalLM", "AutoModelForSeq2SeqLM",
            "AutoModelForTokenClassification", "AutoModelForMaskedLM"
        }:
            for kw in node.keywords:
                if kw.arg == "revision":
                    if _is_str(kw.value):
                        v = kw.value.value.strip().lower()
                        return v in ("", "main", "latest")
                    return False  # revision présent mais non-const → ne pas signaler
            return True  # pas de revision → non pinné

    # 4) Ollama — subprocess.run([... "ollama","run","llama3[:tag]"])
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"run", "check_call"}:
        # a) Liste/tuple d'args
        for arg in node.args:
            if isinstance(arg, (ast.List, ast.Tuple)):
                items = [e.value for e in arg.elts if _is_str(e)]
                if len(items) >= 3 and items[0] == "ollama" and items[1] == "run":
                    model_tok = items[2]
                    if ":" not in model_tok:
                        return True
                    return _LATEST.search(model_tok) is not None
            # b) Chaîne shell
            if _is_str(arg):
                s = arg.value.strip()
                if s.startswith("ollama run "):
                    model_tok = s.split("ollama run ", 1)[1].split()[0]
                    if ":" not in model_tok:
                        return True
                    return _LATEST.search(model_tok) is not None

    return False

def _kw_value(node: ast.AST, name: str):
    """Retourne la valeur du mot-clé `name` si présent dans l'appel AST."""
    if not isinstance(node, ast.Call):
        return None
    for kw in node.keywords:
        # Cas normal : kw.arg est une string
        if kw.arg == name:
            return kw.value
        # Cas **kwargs : kw.arg est None → on ne sait pas encore
    return None

def _dict_has_key_str(d: ast.Dict, wanted: str) -> bool:
    """True si le dict AST a une clé constante == wanted."""
    if not isinstance(d, ast.Dict):
        return False
    for k in d.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value == wanted:
            return True
    return False

def _list_has_system_message(lst: ast.List) -> bool:
    """
    Retourne True si la liste AST contient un dict ou tuple dont le rôle est 'system'.
    """
    if not isinstance(lst, ast.List):
        return False

    for elt in lst.elts:
        # Cas {"role": "system", "content": "..."}
        if isinstance(elt, ast.Dict):
            for k, v in zip(elt.keys, elt.values):
                if isinstance(k, ast.Constant) and k.value == "role":
                    if isinstance(v, ast.Constant) and v.value == "system":
                        return True

        # Cas ("system", ...)
        if isinstance(elt, (ast.Tuple, ast.List)) and elt.elts:
            first = elt.elts[0]
            if isinstance(first, ast.Constant) and first.value == "system":
                return True

    return False



def isRoleBasedLLMChat(node: ast.AST) -> bool:
    """
    True si l'appel est un "chat" role-based (où un 'system' est attendu) :
      - OpenAI Chat Completions: openai.ChatCompletion.create / client.chat.completions.create
      - Anthropic Messages: anthropic.messages.create / client.messages.create
      - OpenAI Responses: client.responses.create (quand input est de type chat)
      - Gemini / Vertex: model.generate_content(...) / model.start_chat(...) où model provient d'un GenerativeModel(...)
    """
    if not isinstance(node, ast.Call):
        return False

    # Reconstruit le chemin ('openai','ChatCompletion','create'), ('client','responses','create'), etc.
    path = []
    f = node.func
    while isinstance(f, ast.Attribute):
        path.insert(0, f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        path.insert(0, f.id)
    call_tuple = tuple(path)

    # --- OpenAI Chat ---
    if call_tuple in {("openai", "ChatCompletion", "create"), ("OpenAI", "chat", "completions", "create")}:
        return True
    if len(call_tuple) >= 3 and call_tuple[-3:] == ("chat", "completions", "create"):
        return True

    # --- Anthropic Messages ---
    if call_tuple in {("anthropic", "messages", "create"), ("Anthropic", "messages", "create")}:
        return True
    if len(call_tuple) >= 2 and call_tuple[-2:] == ("messages", "create"):
        return True

    # --- OpenAI Responses ---
    if len(call_tuple) >= 2 and call_tuple[-2:] == ("responses", "create"):
        return True  # on vérifiera "instructions" côté hasNoSystemMessage

    # --- Gemini / Vertex generate_content / start_chat ---
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"generate_content", "start_chat"}:
        # On ne vérifie pas ici le constructeur; hasNoSystemMessage s'en charge (recherche GenerativeModel)
        return True

    return False


def hasNoSystemMessage(node: ast.AST) -> bool:
    """
    True si, avec suffisamment d'évidence statique, aucun "system message/instructions" n'est fourni.
    Couvre :
      - OpenAI Chat: 'messages' ne contient pas {'role':'system',...}
      - Anthropic Messages: kw 'system' absent (même via **kwargs)
      - OpenAI Responses: 'instructions' absent ET input est de type chat (liste de dicts avec 'role')
      - Gemini / Vertex: GenerativeModel(...) sans system_instruction (ou ""), puis generate_content/start_chat
    Conservative: si indéterminé, NE PAS signaler.
    """
    if not isinstance(node, ast.Call) or not isRoleBasedLLMChat(node):
        return False

    # Recrée call_tuple pour distinguer les familles
    path = []
    f = node.func
    while isinstance(f, ast.Attribute):
        path.insert(0, f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        path.insert(0, f.id)
    call_tuple = tuple(path)

    # -------------------- OpenAI Chat --------------------
    # Inspecte messages=[...] / **kwargs{"messages": ...}
    if (call_tuple in {("openai", "ChatCompletion", "create"), ("OpenAI", "chat", "completions", "create")}) or \
       (len(call_tuple) >= 3 and call_tuple[-3:] == ("chat", "completions", "create")):
        msgs_kw = _kw_value(node, "messages")

        def _messages_has_system_from_value(val: ast.AST):
            # True/False si déterminé, None sinon
            if isinstance(val, ast.List):
                return _list_has_system_message(val)
            if isinstance(val, ast.Name):
                root = _get_root(node)
                call_line = getattr(node, "lineno", 10**9)
                lst = _find_last_list_assignment(root, val.id, call_line)
                if isinstance(lst, ast.List):
                    return _list_has_system_message(lst)
                return None
            return None

        if msgs_kw is not None:
            has = _messages_has_system_from_value(msgs_kw)
            if has is True:
                return False
            if has is False:
                return True
            return False  # indéterminé

        # Cherche via **kwargs
        for kw in node.keywords:
            if kw.arg is None:
                val = kw.value
                # **{...}
                if isinstance(val, ast.Dict):
                    # Anthropic-style 'system' n'est pas pertinent ici; on cherche 'messages'
                    for k, v in zip(val.keys, val.values):
                        if isinstance(k, ast.Constant) and k.value == "messages":
                            if isinstance(v, ast.List):
                                return not _list_has_system_message(v)
                            if isinstance(v, ast.Name):
                                root = _get_root(node)
                                call_line = getattr(node, "lineno", 10**9)
                                lst = _find_last_list_assignment(root, v.id, call_line)
                                if isinstance(lst, ast.List):
                                    return not _list_has_system_message(lst)
                            return False  # indéterminé
                    return False
                # **params (variable dict)
                if isinstance(val, ast.Name):
                    root = _get_root(node)
                    call_line = getattr(node, "lineno", 10**9)
                    d = _find_last_dict_assignment(root, val.id, call_line)
                    if isinstance(d, ast.Dict):
                        for k, v in zip(d.keys, d.values):
                            if isinstance(k, ast.Constant) and k.value == "messages":
                                if isinstance(v, ast.List):
                                    return not _list_has_system_message(v)
                                if isinstance(v, ast.Name):
                                    lst = _find_last_list_assignment(root, v.id, call_line)
                                    if isinstance(lst, ast.List):
                                        return not _list_has_system_message(lst)
                        return False
                    return False
        return False  # rien de concluant → ne pas signaler

    # -------------------- Anthropic Messages --------------------
    if (call_tuple in {("anthropic", "messages", "create"), ("Anthropic", "messages", "create")}) or \
       (len(call_tuple) >= 2 and call_tuple[-2:] == ("messages", "create")):
        # kw 'system' direct ?
        if _kw_value(node, "system") is not None:
            return False
        # via **kwargs
        for kw in node.keywords:
            if kw.arg is None:
                v = kw.value
                if isinstance(v, ast.Dict):
                    if _dict_has_key_str(v, "system"):
                        return False
                    return True  # dict présent mais sans 'system' → missing
                if isinstance(v, ast.Name):
                    root = _get_root(node)
                    call_line = getattr(node, "lineno", 10**9)
                    d = _find_last_dict_assignment(root, v.id, call_line)
                    if isinstance(d, ast.Dict):
                        if _dict_has_key_str(d, "system"):
                            return False
                        return True
                    return False  # indéterminé
        # Aucun 'system' visible → signaler
        return True

    # -------------------- OpenAI Responses --------------------
    if len(call_tuple) >= 2 and call_tuple[-2:] == ("responses", "create"):
        # Si 'instructions' est présent (même via **kwargs) → OK
        if _kw_value(node, "instructions") is not None:
            return False
        for kw in node.keywords:
            if kw.arg is None:
                v = kw.value
                if isinstance(v, ast.Dict):
                    if _dict_has_key_str(v, "instructions"):
                        return False
                    inp = None
                    for k, val in zip(v.keys, v.values):
                        if isinstance(k, ast.Constant) and k.value == "input":
                            inp = val
                            break
                    # input chat-like ?
                    chat_like = False
                    if isinstance(inp, ast.List):
                        chat_like = any(isinstance(e, ast.Dict) and _dict_has_key_str(e, "role") for e in inp.elts)
                    elif isinstance(inp, ast.Name):
                        root = _get_root(node)
                        call_line = getattr(node, "lineno", 10**9)
                        lst = _find_last_list_assignment(root, inp.id, call_line)
                        if isinstance(lst, ast.List):
                            chat_like = any(isinstance(e, ast.Dict) and _dict_has_key_str(e, "role") for e in lst.elts)
                    return chat_like  # report seulement si clairement chat-like
                if isinstance(v, ast.Name):
                    root = _get_root(node)
                    call_line = getattr(node, "lineno", 10**9)
                    d = _find_last_dict_assignment(root, v.id, call_line)
                    if isinstance(d, ast.Dict):
                        if _dict_has_key_str(d, "instructions"):
                            return False
                        # inspect input
                        inp = None
                        for k, val in zip(d.keys, d.values):
                            if isinstance(k, ast.Constant) and k.value == "input":
                                inp = val
                                break
                        chat_like = False
                        if isinstance(inp, ast.List):
                            chat_like = any(isinstance(e, ast.Dict) and _dict_has_key_str(e, "role") for e in inp.elts)
                        elif isinstance(inp, ast.Name):
                            lst = _find_last_list_assignment(root, inp.id, call_line)
                            if isinstance(lst, ast.List):
                                chat_like = any(isinstance(e, ast.Dict) and _dict_has_key_str(e, "role") for e in lst.elts)
                        return chat_like
                    return False  # indéterminé
        # input=... direct ?
        inp = _kw_value(node, "input")
        chat_like = False
        if isinstance(inp, ast.List):
            chat_like = any(isinstance(e, ast.Dict) and _dict_has_key_str(e, "role") for e in inp.elts)
        elif isinstance(inp, ast.Name):
            root = _get_root(node)
            call_line = getattr(node, "lineno", 10**9)
            lst = _find_last_list_assignment(root, inp.id, call_line)
            if isinstance(lst, ast.List):
                chat_like = any(isinstance(e, ast.Dict) and _dict_has_key_str(e, "role") for e in lst.elts)
        return chat_like  # True ⇒ report (instructions manquantes)

    # -------------------- Gemini / Vertex generate_content / start_chat --------------------
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"generate_content", "start_chat"}:
        root = _get_root(node)
        call_line = getattr(node, "lineno", 10**9)

        # Helper inline: vérifie si un Call est un constructeur GenerativeModel(...)
        def _is_gm_ctor(call_obj: ast.AST) -> bool:
            if not isinstance(call_obj, ast.Call):
                return False
            ff = call_obj.func
            return (isinstance(ff, ast.Name) and ff.id == "GenerativeModel") or \
                   (isinstance(ff, ast.Attribute) and ff.attr == "GenerativeModel")

        # Helper inline: teste si system_instruction est manquant ou vide ("") dans un ctor
        def _gm_ctor_missing_sysinstr(ctor: ast.Call) -> bool:
            si = _kw_value(ctor, "system_instruction")
            if si is not None:
                # vide => report
                if isinstance(si, ast.Constant) and isinstance(si.value, str) and si.value == "":
                    return True
                return False
            # **kwargs
            for kw in ctor.keywords:
                if kw.arg is None:
                    v = kw.value
                    if isinstance(v, ast.Dict):
                        val = None
                        for k, dv in zip(v.keys, v.values):
                            if isinstance(k, ast.Constant) and k.value == "system_instruction":
                                val = dv
                                break
                        if val is None:
                            return True
                        if isinstance(val, ast.Constant) and isinstance(val.value, str) and val.value == "":
                            return True
                        return False
                    if isinstance(v, ast.Name):
                        d = _find_last_dict_assignment(root, v.id, getattr(ctor, "lineno", 10**9))
                        if isinstance(d, ast.Dict):
                            val = None
                            for k, dv in zip(d.keys, d.values):
                                if isinstance(k, ast.Constant) and k.value == "system_instruction":
                                    val = dv
                                    break
                            if val is None:
                                return True
                            if isinstance(val, ast.Constant) and isinstance(val.value, str) and val.value == "":
                                return True
                            return False
                        return False
            # aucun kw pertinent → manquant
            return True

        # Cas A: appel chaîné GenerativeModel(...).generate_content(...)
        base_expr = node.func.value
        if isinstance(base_expr, ast.Call) and _is_gm_ctor(base_expr):
            return _gm_ctor_missing_sysinstr(base_expr)

        # Cas B: var.generate_content(...), retrouver dernière affectation var = GenerativeModel(...)
        # Trouver le dernier Assign à cette variable avant l'appel
        base_name = None
        b = node.func.value
        while isinstance(b, ast.Attribute):
            b = b.value
        if isinstance(b, ast.Name):
            base_name = b.id

        if base_name:
            last_ctor = None
            last_line = -1
            for n in ast.walk(root):
                if isinstance(n, ast.Assign) and getattr(n, "lineno", 0) < call_line:
                    if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == base_name:
                        if isinstance(n.value, ast.Call) and _is_gm_ctor(n.value):
                            if getattr(n, "lineno", 0) > last_line:
                                last_ctor, last_line = n.value, getattr(n, "lineno", 0)
            if isinstance(last_ctor, ast.Call):
                return _gm_ctor_missing_sysinstr(last_ctor)

        return False  # indéterminé

    return False

def hasNoBoundedMetrics(node: ast.AST) -> bool:
    #print("DBG_R28.hasNoBoundedMetrics: enter node:", type(node).__name__)
    if not isinstance(node, ast.Call) or not isLLMCall(node):
        #print("DBG_R28.hasNoBoundedMetrics: not a Call or not LLM -> False")
        return False

    # bornes directes (sécurisé : parcours explicite des keywords)
    for kw in node.keywords:
        if kw.arg in {"max_tokens", "max_output_tokens", "timeout"}:
            #print(f"DBG_R28.hasNoBoundedMetrics: direct bound {kw.arg} -> False")
            return False

    # Gemini: generate_content / start_chat
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"generate_content", "start_chat"}:
        gen_cfg = _kw_value(node, "generation_config")
        if gen_cfg is None:
            return True
        if isinstance(gen_cfg, ast.Dict):
            if not _dict_has_key_str(gen_cfg, "max_output_tokens"):
                return True
            return False
        elif isinstance(gen_cfg, ast.Name):
            root = _get_root(node)
            call_line = getattr(node, "lineno", 10**9)
            d = _find_last_dict_assignment(root, gen_cfg.id, call_line)
            if isinstance(d, ast.Dict):
                if not _dict_has_key_str(d, "max_output_tokens"):
                    return True
                return False
            else:
                return True  # indéterminable ⇒ conservateur : unbounded

    # **kwargs: dicts qui contiennent des bornes
    for kw in node.keywords:
        if kw.arg is None:
            v = kw.value
            if isinstance(v, ast.Dict):
                if any(_dict_has_key_str(v, k) for k in ["max_tokens", "max_output_tokens", "timeout"]):
                    return False
            elif isinstance(v, ast.Name):
                root = _get_root(node)
                call_line = getattr(node, "lineno", 10**9)
                d = _find_last_dict_assignment(root, v.id, call_line)
                if isinstance(d, ast.Dict):
                    if any(_dict_has_key_str(d, k) for k in ["max_tokens", "max_output_tokens", "timeout"]):
                        return False

    # Timeout dans n'importe quel 'with client.with_options(timeout=...)' englobant
    parent = getattr(node, "parent", None)
    while parent:
        if isinstance(parent, ast.With):
            for item in parent.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Attribute) and ctx.func.attr == "with_options":
                    if _kw_value(ctx, "timeout") is not None:
                        return False
        parent = getattr(parent, "parent", None)

    # aucune borne trouvée -> unbounded
    return True

def rule_R11(ast_node):
    import ast
    add_parent_info(ast_node)
    #set_deterministic_flag(ast_node)
    # "Data Leakage (fit_transform before split)"
    variable_ops = gather_scale_sensitive_ops(ast_node)
    scaled_vars = gather_scaled_vars(ast_node)
    problems = {}
    for sub in ast.walk(ast_node):
        if (((isFitTransform(sub) and (not pipelineUsed(sub))) and usedBeforeTrainTestSplit(sub))):
            line = getattr(sub, 'lineno', '?')
            if line != '?':
                problems[line] = sub
    for line, node in problems.items():
        report_with_line("Potential data leakage: fit_transform called before train/test split at line {lineno}", node)
