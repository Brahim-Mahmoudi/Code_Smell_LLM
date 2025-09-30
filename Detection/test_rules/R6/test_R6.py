import ast
import unittest
import generated_rules_R6  # Le module contenant rule_R6 générée depuis la DSL

class TestGeneratedRulesR6(unittest.TestCase):
    def setUp(self):
        self.messages = []
        def report(message):
            self.messages.append(message)
        generated_rules_R6.report = report  # Monkey-patch de report()

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R6.rule_R6(ast_node)

    def test_no_warning_if_use_deterministic(self):
        """Aucun message si torch.use_deterministic_algorithms(True) est utilisé"""
        code = """
import torch
torch.use_deterministic_algorithms(True)
model = torch.nn.Linear(10, 2)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucun message attendu avec use_deterministic_algorithms(True)")

    def test_warning_if_no_deterministic(self):
        """Message attendu si aucun réglage de déterminisme"""
        code = """
import torch
model = torch.nn.Linear(10, 2)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Un message attendu si aucun appel à use_deterministic_algorithms")

    def test_ignore_random_library(self):
        """Pas de message attendu si on utilise random (non concerné)"""
        code = """
import random
x = random.choice([1, 2, 3])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucun message attendu pour random")

    def test_ignore_numpy_seed(self):
        """Pas de message attendu si on utilise np.random.seed (non PyTorch)"""
        code = """
import numpy as np
np.random.seed(42)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucun message attendu pour numpy")

    def test_ignore_transformers_seed(self):
        """Pas de message attendu pour transformers.set_seed (non PyTorch)"""
        code = """
import transformers
transformers.set_seed(42)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucun message attendu pour transformers")

    def test_combined_with_manual_seed(self):
        """torch.manual_seed ne suffit pas, use_deterministic doit être présent"""
        code = """
import torch
torch.manual_seed(42)
model = torch.nn.Linear(10, 2)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Un message attendu sans use_deterministic_algorithms")

if __name__ == '__main__':
    unittest.main()
