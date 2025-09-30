import ast
import unittest
import generated_rules_R19  # Assurez-vous que le module généré pour la règle R19 s'appelle bien generated_rules_19

class TestGeneratedRules19(unittest.TestCase):
    def setUp(self):
        # Réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # On "monkey-patche" la fonction report du module généré
        generated_rules_R19.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R19.rule_R19(ast_node)

    def test_threshold_validation_metrics_count(self):
        """
        Ce test vérifie qu'une alerte est générée lorsque le nombre de métriques dépendantes
        (par exemple f1_score, precision_score, recall_score) est supérieur ou égal au nombre de métriques
        indépendantes (par exemple mean_absolute_error, mean_squared_error).
        """
        code = """
import sklearn.metrics as metrics
# Simuler plusieurs appels aux métriques dépendantes
#a = metrics.f1_score([1,0,1], [1,1,0])
#b = metrics.precision_score([1,0,1], [1,1,0])
#c = metrics.recall_score([1,0,1], [1,1,0])
# Simuler un appel à une métrique indépendante
d = metrics.mean_absolute_error([1,2,3], [1,2,3])
recall_score2_data2 = sklmetrics.recall_score(eval2_y, pred2_y, average="micro")
scorer1 = sklmetrics.make_scorer(sklmetrics.recall_score, average="micro")
"""
        self.run_rule(code)
        # Vérifier qu'une alerte est générée
        self.assertTrue(len(self.messages) > 0,
                        "Une alerte doit être générée lorsque les métriques dépendantes sont trop nombreuses.")
        # Vérifier que le message contient le texte attendu
        self.assertIn("Too many threshold-dependent metrics", self.messages[0])

    def test_no_alert_when_independent_higher(self):
        """
        Ce test vérifie qu'aucune alerte n'est générée lorsque le nombre de métriques indépendantes
        est supérieur au nombre de métriques dépendantes.
        """
        code = """
import sklearn.metrics as metrics
# Simuler un appel à une métrique dépendante
a = metrics.f1_score([1,0,1], [1,1,0])
# Simuler plusieurs appels aux métriques indépendantes
b = metrics.mean_absolute_error([1,2,3], [1,2,3])
c = metrics.mean_squared_error([1,2,3], [1,2,3])
d = metrics.r2_score([1,2,3], [1,2,3])
"""
        self.run_rule(code)
        # Aucune alerte ne doit être générée
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée lorsque les métriques indépendantes dominent.")

if __name__ == '__main__':
    unittest.main()
