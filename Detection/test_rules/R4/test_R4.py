import ast
import unittest
import generated_rules_R4  # module généré contenant la règle R4

class TestTrainingEvalTogglingR4(unittest.TestCase):
    def setUp(self):
        # Réinitialise la liste des messages pour chaque test
        self.messages = []
        # Redéfinition de report et report_with_line pour capturer les messages d'alerte
        generated_rules_R4.report = lambda msg: self.messages.append(msg)
        generated_rules_R4.report_with_line = lambda msg, node: self.messages.append(msg.format(lineno=getattr(node, 'lineno', '?')))

    def run_rule(self, code):
        # Parse le code source et exécute la règle R4
        ast_node = ast.parse(code)
        generated_rules_R4.rule_R4(ast_node)

    def test_eval_without_train(self):
        """Test eval() sans train() suivant"""
        code = """
for epoch in range(10):
    model.eval()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Should detect eval() without subsequent train()")

    def test_eval_during_training(self):
        """Test eval() pendant l'entraînement"""
        code = """
for epoch in range(10):
    model.eval()
    optimizer.step()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not detect issue when no train() is required during training loop")

    def test_proper_eval_train(self):
        """Test séquence correcte eval()->train()"""
        code = """
for epoch in range(10):
    model.eval()
    model.train()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not detect issue if eval() is followed by train()")

    def test_eval_in_validation(self):
        """Test eval() dans bloc validation"""
        code = """
for epoch in range(10):
    if True:
        model.eval()
        model.train()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not detect issue if eval() and train() occur in a conditional block")

    def test_eval_without_train_in_function(self):
        """Test eval() sans train() dans une fonction"""
        code = """
def validate():
    model.eval()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Should detect eval() without train() inside a function")

    def test_eval_in_nested_loop(self):
        """Test eval() dans une boucle imbriquée"""
        code = """
for epoch in range(10):
    for batch in range(100):
        model.eval()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Should detect eval() without train() in a nested loop")

    def test_eval_with_train_in_nested_loop(self):
        """Test eval() dans une boucle imbriquée avec train()"""
        code = """
for epoch in range(10):
    for batch in range(100):
        model.eval()
        model.train()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not detect issue if eval() and train() are both present in a nested loop")

if __name__ == '__main__':
    unittest.main()
