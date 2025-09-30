import ast
import unittest
import generated_rules_R3  # module généré contenant la règle R3

class TestTensorArrayNotUsedR3(unittest.TestCase):
    def setUp(self):
        # Réinitialise les messages pour chaque test
        self.messages = []
        # Remplace la fonction report pour capturer les messages d'alerte
        generated_rules_R3.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        # Parse le code source et exécute la règle R3
        ast_node = ast.parse(code)
        generated_rules_R3.rule_R3(ast_node)

    def test_detect_constant_concat_in_tf_function(self):
        # Cas de test avec tf.constant() et tf.concat() dans une fonction tf.function problématique
        code = """
import tensorflow as tf

@tf.function
def problematic_function():
    a = tf.constant([1, 2])
    for i in range(3):
        a = tf.concat([a, [i]], 0)
    return a
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Should detect missing TensorArray usage in problematic_function")

    def test_correct_tensorarray_usage(self):
        # Cas de test avec une utilisation correcte de TensorArray
        code = """
import tensorflow as tf

@tf.function
def correct_function():
    a = tf.TensorArray(tf.int32, size=5)
    a = a.write(0, 1)
    a = a.write(1, 2)
    return a.stack()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not detect issue in correct_function")

    def test_detect_multiple_constant_concat(self):
        # Cas de test avec plusieurs variables utilisant constant et concat
        code = """
import tensorflow as tf

@tf.function
def multiple_variables_function():
    x = tf.constant([1, 2])
    y = tf.constant([3, 4])
    for i in range(3):
        x = tf.concat([x, [i]], 0)
        y = tf.concat([y, [i+10]], 0)
    return x, y
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Should detect issues in multiple_variables_function")

    def test_nested_function_detection(self):
        # Cas de test dans une fonction imbriquée avec @tf.function
        code = """
import tensorflow as tf

@tf.function
def outer_function():
    def inner_function():
        a = tf.constant([1, 2])
        for i in range(3):
            a = tf.concat([a, [i]], 0)
        return a
    return inner_function()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Should detect issue in inner_function nested within outer_function")


    def test_constant_only_assignment(self):
        # tf.constant assigné mais jamais utilisé dans une op => ne doit PAS détecter
        code = """
import tensorflow as tf

def only_constant():
    a = tf.constant([1, 2, 3])
    return a
    """
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Ne doit pas détecter si tf.constant n'est pas utilisé dans une opération")

    def test_constant_binop_inside_loop(self):
    # Correctement identifié comme smell uniquement car DANS une boucle
        code = """
import tensorflow as tf

def constant_binop_loop():
    x = tf.constant([1., 2., 3.])
    for i in range(3):
        x = x + tf.constant([i, i, i])
    return x
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "DOIT détecter tf.constant modifié dynamiquement dans une boucle")

    def test_constant_used_in_function_arg(self):
        # tf.constant utilisé comme argument d'une fonction TensorFlow => doit détecter
        code = """
import tensorflow as tf

def func_arg_constant():
    a = tf.reduce_sum(tf.constant([1, 2, 3]))
    return a
    """
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Ne doit PAS détecter tf.constant utilisé comme argument de fonction")

    def test_constant_used_in_compare(self):
        # tf.constant utilisé dans une comparaison => doit détecter
        code = """
import tensorflow as tf

def compare_constant():
    a = tf.constant([1])
    b = tf.constant([2])
    return a == b
    """
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Ne doit PAS détecter tf.constant utilisé dans une comparaison")

    def test_constant_and_tensorarray(self):
        # Utilisation de tf.constant mais aussi TensorArray => ne doit pas détecter (cas 'OK')
        code = """
import tensorflow as tf

def array_and_constant():
    ta = tf.TensorArray(tf.float32, size=2)
    a = tf.constant([1., 2.])
    ta = ta.write(0, a)
    return ta.stack()
    """
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Ne doit pas détecter si TensorArray est utilisé correctement")

    def test_constant_in_tf_function_no_op(self):
        # tf.constant dans une fonction tf.function mais jamais utilisé dans une opération => ne doit pas détecter
        code = """
import tensorflow as tf

@tf.function
def no_op_constant():
    c = tf.constant([42])
    return c
    """
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Ne doit pas détecter pour tf.constant inutilisé dans une op")

    def test_constant_binop_outside_loop(self):
    # Pas un smell : hors boucle, pas dynamique
        code = """
import tensorflow as tf

def constant_binop_no_loop():
    x = tf.constant([1., 2., 3.])
    y = x + tf.constant([4., 5., 6.])
    return y
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "NE DOIT PAS détecter usage ponctuel de tf.constant hors boucle")

    def test_constant_used_as_function_default(self):
        # tf.constant utilisé dans une valeur par défaut de fonction, mais pas dans une op => ne doit pas détecter
        code = """
import tensorflow as tf

def foo(x=tf.constant([1,2,3])):
    return x
    """
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Ne doit pas détecter si tf.constant n'est pas utilisé dans une opération")

if __name__ == '__main__':
    unittest.main()
