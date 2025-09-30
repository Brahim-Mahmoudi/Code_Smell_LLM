import ast
import unittest
import generated_rules_R8  # Le module généré contenant la règle R8

class TestPyTorchCallMethodMisuse(unittest.TestCase):
    def setUp(self):
        # On redéfinit la fonction report pour capturer les messages d'alerte
        self.messages = []
        generated_rules_R8.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        # Parser le code source et exécuter la règle R8 sur l'AST
        ast_node = ast.parse(code)
        generated_rules_R8.rule_R8(ast_node)

    def test_true_positive_direct_forward(self):
        """Vrai positif : usage explicite de .forward() sur self"""
        code = """
import torch
import torch.nn as nn

class Net(nn.Module):
    def forward(self, x):
        return self.conv.forward(x)  # Doit être signalé
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Le smell devrait être signalé (true positive)")

    def test_true_positive_variable_model(self):
        """Vrai positif : usage explicite de .forward() sur variable modèle"""
        code = """
import torch
import torch.nn as nn

model = nn.Linear(10, 5)
y = model.forward(x)  # Doit être signalé
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Le smell devrait être signalé (true positive variable)")

    def test_false_positive_non_pytorch(self):
        """Faux positif : .forward() hors contexte PyTorch (ne doit PAS être signalé)"""
        code = """
class Custom:
    def forward(self, x):
        return x * 2

obj = Custom()
y = obj.forward(3)  # Ne doit pas être signalé
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Pas d'alerte hors PyTorch (false positive)")

    def test_true_negative_correct_usage(self):
        """Vrai négatif : appel correct du module comme fonction"""
        code = """
import torch
import torch.nn as nn

class Net(nn.Module):
    def forward(self, x):
        return x + 1

model = Net()
y = model(x)  # Bonne pratique, ne doit pas être signalé
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Bonne pratique : pas d'alerte attendue (true negative)")

    def test_false_negative_missed_smell(self):
        """Faux négatif : cas que la règle devrait signaler mais ne le fait pas"""
        code = """
import torch
import torch.nn as nn

class Net(nn.Module):
    def forward(self, x):
        return self.linear.forward(x)  # Devrait être signalé

def some_function():
    model = Net()
    z = model.linear.forward(y)  # Devrait aussi être signalé
"""
        self.run_rule(code)
        # Si la règle rate ces cas, le test doit échouer
        self.assertGreaterEqual(len(self.messages), 2, "Au moins deux alerts attendues (false negative si non détecté)")

    def test_true_positive_nested_attribute(self):
        """Vrai positif : .forward() sur attribut imbriqué (self.block.layer.forward(x))"""
        code = """
import torch
import torch.nn as nn

class Block(nn.Module):
    def forward(self, x):
        return x

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.block = Block()
    def forward(self, x):
        return self.block.forward(x)  # Doit être signalé
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Le smell imbriqué doit être détecté (true positive)")

    def test_false_positive_function_named_forward(self):
        """Faux positif : une fonction nommée 'forward' hors classe PyTorch (ne doit pas être signalé)"""
        code = """
def forward(x):
    return x*2

y = forward(42)  # Ne doit pas être signalé
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Pas d'alerte pour simple fonction nommée forward")

if __name__ == '__main__':
    unittest.main()
