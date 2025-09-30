import ast
import unittest
import generated_rules_R15

class TestGeneratedRules15(unittest.TestCase):
    def setUp(self):
        # Réinitialise la liste des messages pour chaque test
        self.messages = []
        # On "monkey-patche" la fonction report du module généré
        def report(message):
            self.messages.append(message)
        generated_rules_R15.report = report
        # Pour être sûr que dataframe_vars est réinitialisé à chaque test, vous pouvez le vider :
        if hasattr(generated_rules_R15, "dataframe_vars"):
            generated_rules_R15.dataframe_vars.clear()

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R15.rule_R15(ast_node)

    def test_merge_without_parameters(self):
        # Cas : appel merge avec un seul paramètre (doit être détecté)
        code = """
import pandas as pd

df1 = pd.DataFrame({'key': ['foo', 'bar', 'baz', 'foo'],
                    'value': [1, 2, 3, 5]})
df2 = pd.DataFrame({'key': ['foo', 'bar', 'baz', 'foo'],
                    'value': [5, 6, 7, 8]})
df3 = df1.merge(df2)
        """
        self.run_rule(code)
        # Vérifier qu'au moins un message a été généré
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour un merge sans paramètres explicites.")
        print("Test merge_without_parameters - Messages générés:", self.messages)

    def test_merge_with_parameters(self):
        # Cas : appel merge avec paramètres explicites (ne doit pas être détecté)
        code = """
import pandas as pd

df1 = pd.DataFrame({'key': ['foo', 'bar', 'baz', 'foo'],
                    'value': [1, 2, 3, 5]})
df2 = pd.DataFrame({'key': ['foo', 'bar', 'baz', 'foo'],
                    'value': [5, 6, 7, 8]})
df3 = df1.merge(
    df2,
    how='inner',
    on='key',
    validate='m:m'
)
        """
        self.run_rule(code)
        # Vérifier qu'aucun message n'a été généré
        self.assertEqual(len(self.messages), 0,
                         "Un message a été généré alors que merge est correctement paramétré.")
        print("Test merge_with_parameters - Aucun message généré.")

    def test_mixed_merge(self):
        # Cas mixte : un appel sur DataFrame (à détecter) et un appel sur autre objet (à ignorer)
        code = """
import pandas as pd

# Bon cas - DataFrame
df = pd.DataFrame({'A': [1, 2]})
df2 = pd.DataFrame({'B': [3, 4]})
result = df.merge(df2)  # Devrait être détecté

# Mauvais cas - non DataFrame
session.merge(SqlRegisteredModelTag(name=name, key=tag.key, value=tag.value))  # Ne devrait pas être détecté
        """
        self.run_rule(code)
        # On s'attend à ce qu'au moins un message ait été généré pour le merge sur DataFrame
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour l'appel merge sur DataFrame.")
        print("Test mixed_merge - Messages générés:", self.messages)

if __name__ == '__main__':
    unittest.main()
