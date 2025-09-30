import ast
import unittest
import generated_rules_R7  # Module généré contenant la règle R7

class TestMissingMaskR7(unittest.TestCase):
    def setUp(self):
        self.messages = []
        # Redéfinir report pour capturer les messages d'alerte
        generated_rules_R7.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        # Parser le code source et exécuter la règle R7 sur l'AST
        ast_node = ast.parse(code)
        generated_rules_R7.rule_R7(ast_node)

    def test_detect_missing_mask(self):
        """Test du cas où tf.log est utilisé sans clip_by_value"""
        code = """
import tensorflow as tf
x = 0.0
result = tf.log(x)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0,
                           "Une alerte devrait être générée lorsque tf.log est utilisé sans clip_by_value")

    def test_detect_with_mask(self):
        """Test du cas où tf.log est utilisé avec clip_by_value"""
        code = """
import tensorflow as tf
x = 0.0
result = tf.log(tf.clip_by_value(x, 1e-10, 1.0))
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne devrait être générée lorsque tf.log utilise clip_by_value")

if __name__ == '__main__':
    unittest.main()
