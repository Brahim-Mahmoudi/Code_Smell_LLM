import ast
import unittest
import generated_rules_R14  # Assurez-vous que ce module contient la règle R14

class TestGeneratedRules14(unittest.TestCase):
    def setUp(self):
        # On réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # On "monkey-patche" la fonction report du module généré
        generated_rules_R14.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R14.rule_R14(ast_node)

    def test_conversion_misuse_basic(self):
        # Test 1 : Utilisation basique de df.values (doit être détectée)
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
arr = df.values
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour l'utilisation basique de df.values.")
        print("Message généré (basic):", self.messages[0])

    def test_conversion_misuse_indexing(self):
        # Test 2 : Utilisation de df.values avec indexation (doit être détectée)
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
elem = df.values[0]
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour l'utilisation de df.values avec indexation.")
        print("Message généré (indexing):", self.messages[0])

    def test_complex_indexing_values_misuse(self):
        # Test 3 : Indexation complexe après .values (doit être détectée)
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
result = df.values[:, 0]
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour l'indexation complexe sur df.values.")

    def test_transformation_values_misuse(self):
        # Test 4 : Transformation après .values (doit être détectée)
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
result = df.values.transpose()
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour l'utilisation de .transpose() sur df.values.")

    def test_numpy_function_values_misuse(self):
        # Test 5 : Utilisation de df.values dans une fonction numpy (doit être détectée)
        code = """
import pandas as pd
import numpy as np
df = pd.DataFrame({'A': [1, 2, 3]})
np.testing.assert_array_almost_equal(df.values, np.array([1, 2, 3]))
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour l'utilisation de df.values dans une fonction numpy.")

    def test_multiple_operations_values_misuse(self):
        # Test 6 : Plusieurs opérations chaînées sur df.values (doit être détectée)
        code = """
import pandas as pd
result_df = pd.DataFrame({'A': [1, 2, 3]})
result = result_df.values.transpose()[0]
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Aucun message n'a été généré pour les opérations chaînées sur df.values.")

    def test_false_positives(self):
        # Test 7 : Utilisation de .values sur un dictionnaire (ne doit pas être détectée)
        code = """
import pandas as pd
dict_data = {'A': 1}
values = dict_data.values()
for value in dict_data.values():
    print(value)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Un message a été généré alors que l'utilisation de .values sur un dictionnaire ne doit pas être signalée.")

    def test_dict_values_usage(self):
        # Test 8 : Utilisations légitimes de .values() sur des dictionnaires (ne doivent pas être détectées)
        code = """
import pandas as pd
dict_data = {'A': 1, 'B': 2}
if all(_is_scalar(x) for x in dict_data.values()):
    df = pd.DataFrame([dict_data])
for value in dict_data.values():
    print(value)
if all(isinstance(x, (str, list)) for x in dict_data.values()):
    pass
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Un message a été généré alors que l'utilisation légitime de .values() sur des dictionnaires ne doit pas être signalée.")

    def test_correct_usage_with_to_numpy(self):
        # Test 9 : Utilisation correcte avec to_numpy() (ne doit pas être détectée)
        code = """
import pandas as pd
import numpy as np
df = pd.DataFrame({'A': [1, 2, 3]})
arr1 = df.to_numpy()
arr2 = df.to_numpy()[:, 0]
arr3 = df.to_numpy().transpose()
np.testing.assert_array_almost_equal(df.to_numpy(), np.array([1, 2, 3]))
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Un message a été généré alors que l'utilisation de df.to_numpy() est correcte.")

    def test_mixed_conversion(self):
        # Test 10 : Cas mixte : un appel sur df.values (à détecter) et un appel sur df.to_numpy() (à ignorer)
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
arr1 = df.values
arr2 = df.to_numpy()
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) == 1,
                        "Le nombre de messages générés ne correspond pas : seul df.values doit être signalé.")
        print("Message généré (mixed):", self.messages[0])


    def test_series_values_detected(self):
        # Test 11 : Utilisation de .values sur une Series pandas (doit être détectée)
        code = """
import pandas as pd
s = pd.Series([1, 2, 3])
a = s.values
b = s.values[1]
c = s.values.reshape(-1, 1)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 3,
                         "Chaque utilisation de .values sur une Series doit être signalée (3 cas attendus).")
        print("Messages générés (Series):", self.messages)

    def test_series_from_dataframe_column(self):
        # Test 12 : Series issue d'une colonne de DataFrame (doit être détectée)
        code = '''
import pandas as pd
df = pd.DataFrame({"x": [1, 2, 3]})
s = df["x"]
arr = s.values
'''
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1,
                         "L'utilisation de .values sur une Series issue d'une colonne DataFrame doit être signalée.")

    def test_series_alias_and_propagation(self):
        # Test 13 : Alias de Series (propagation)
        code = '''
import pandas as pd
df = pd.DataFrame({"x": [1, 2, 3]})
s1 = df["x"]
s2 = s1
s3 = s2
a = s3.values
'''
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1,
                         "L'utilisation de .values sur une Series propagée par alias doit être détectée.")

    def test_values_on_list_should_not_detect(self):
        # Test 14 : .values sur une liste (ne doit pas être détecté)
        code = '''
l = [1, 2, 3]
try:
    v = l.values
except AttributeError:
    v = None
'''
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucun message ne doit être généré pour .values sur une liste.")

    def test_values_on_non_pandas_object(self):
        # Test 15 : .values sur un objet non pandas (ne doit pas être détecté)
        code = '''
class Dummy:
    def __init__(self):
        self.values = [1, 2, 3]
obj = Dummy()
print(obj.values)
'''
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucun message ne doit être généré pour .values sur un objet arbitraire.")

if __name__ == '__main__':
    unittest.main()
