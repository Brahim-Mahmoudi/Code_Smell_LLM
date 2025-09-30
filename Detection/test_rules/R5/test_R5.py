import ast
import unittest
import generated_rules_R5  # Ce module doit contenir la règle R5

class TestHyperparameterNotExplicitlySetR5(unittest.TestCase):
    def setUp(self):
        # Réinitialiser les messages en redéfinissant report
        self.messages = []
        generated_rules_R5.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        # Parser le code et exécuter la règle R5 sur l'AST
        ast_node = ast.parse(code)
        generated_rules_R5.rule_R5(ast_node)

    def test_sklearn_no_params(self):
        """Test pour sklearn sans paramètres"""
        code = """
from sklearn.cluster import KMeans
kmeans = KMeans()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0,
                           "Une alerte devrait être générée pour KMeans sans paramètres")

    def test_pytorch_no_params(self):
        """Test pour PyTorch sans paramètres"""
        code = """
from torch.optim import Adam
optimizer = Adam()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0,
                           "Une alerte devrait être générée pour Adam sans paramètres")

    def test_with_params(self):
        """Test avec paramètres définis (cas valide)"""
        code = """
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=5, random_state=42)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne devrait être générée lorsque les hyperparamètres sont définis")

    def test_multiple_models(self):
        """Test avec plusieurs modèles sans paramètres"""
        code = """
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
rf = RandomForestClassifier()
xgb = XGBClassifier()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0,
                           "Une alerte devrait être générée pour plusieurs modèles sans paramètres")

if __name__ == '__main__':
    unittest.main()
