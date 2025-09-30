import ast
import unittest
import generated_rules_R1  # Ce module doit contenir la fonction rule_R1

class TestGeneratedRulesR1(unittest.TestCase):
    def setUp(self):
        # On réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # On monkey-patche la fonction report du module généré
        generated_rules_R1.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R1.rule_R1(ast_node)


    def test_no_tensorflow_import(self):
        """Test sans import de TensorFlow (donc pas d'utilisation de tf.tile)"""
        code = """
import numpy as np
a = np.array([[1., 2.], [3., 4.]])
b = np.array([[1.], [2.]])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, 
                         "Aucun message attendu si TensorFlow n'est pas importé")

    def test_no_tiling_used(self):
        """Test avec du code sans tf.tile"""
        code = """
import tensorflow as tf
a = tf.constant([[1., 2.], [3., 4.]])
b = tf.constant([[1.], [2.]])
c = a + b
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, 
                         "Aucun message attendu si tf.tile n'est pas utilisé")

    def test_detect_unnecessary_tiling(self):
        """Test la détection de tf.tile dans une opération binaire où le broadcasting serait possible"""
        code = """
import tensorflow as tf
a = tf.constant([[1., 2.], [3., 4.]])
b = tf.constant([[1.], [2.]])
c = a + tf.tile(b, [1, 2])
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, 
                        "Un appel à tf.tile dans une opération binaire aurait dû être détecté")
        if self.messages:
            print("Message généré (unnecessary tiling):", self.messages[0])

if __name__ == '__main__':
    unittest.main()
