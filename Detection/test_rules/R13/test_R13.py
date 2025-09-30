import ast
import unittest
import generated_rules_R13  # Assurez-vous que ce module contient la règle R13

class TestGeneratedRules13(unittest.TestCase):
    def setUp(self):
        # On réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # On "monkey-patche" la fonction report du module généré
        generated_rules_R13.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R13.rule_R13(ast_node)

    def test_detect_empty_column_with_zeros(self):
        """
        Vérifie qu'on détecte la mauvaise initialisation d'une colonne avec 0
        """
        code = """
import pandas as pd

df = pd.DataFrame([])
df['new_col'] = 0
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Une mauvaise initialisation de colonne (valeur 0) aurait dû être détectée"
        )
        if len(self.messages) > 0:
            print("Message généré (basic):", self.messages[0])

    def test_detect_empty_column_with_empty_string(self):
        """
        Vérifie qu'on détecte la mauvaise initialisation d'une colonne avec ""
        """
        code = """
import pandas as pd

x = pd.DataFrame([])
x['new_col'] = ''
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Une mauvaise initialisation de colonne (chaîne vide) aurait dû être détectée"
        )
        if len(self.messages) > 0:
            print("Message généré (basic):", self.messages[0])

    def test_no_issue_with_nan_initialization(self):
        """
        Vérifie qu'on ne signale pas l'initialisation correcte avec np.nan
        """
        code = """
import pandas as pd
import numpy as np

df = pd.DataFrame([])
df['new_col'] = np.nan
"""
        self.run_rule(code)
        # On n'attend aucun message
        self.assertEqual(len(self.messages), 0, "Pas de message attendu avec np.nan")
        if len(self.messages) > 0:
            print("Message généré (basic):", self.messages[0])

    def test_no_false_positive(self):
        """
        Vérifie qu'on ne signale pas quand 'df' n'est pas un DataFrame
        """
        code = """
import pandas as pd

df = []
df['new_col'] = 0
"""
        self.run_rule(code)
        # Ici aussi, on n'attend aucun message car df n'est pas un DataFrame
        self.assertEqual(len(self.messages), 0, "Pas de message attendu (df n'est pas un DataFrame)")
        if len(self.messages) > 0:
            print("Message généré (basic):", self.messages[0])


if __name__ == '__main__':
    unittest.main()
