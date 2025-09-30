import ast
import unittest
import generated_rules_R20

class TestGeneratedRules20(unittest.TestCase):
    def setUp(self):
        # On réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # On "monkey-patche" la fonction report du module généré
        generated_rules_R20.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R20.rule_R20(ast_node)

    

    def test_loc_usage(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
result = df.loc[:, 'A']
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée pour l'utilisation de loc.")

    def test_chained_indexing(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
result = df['A']['B']
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Une alerte doit être générée pour le chained indexing.")
    
    def test_non_dataframe(self):
        code = """
arr = [[1, 2, 3], [4, 5, 6]]
result = arr[0][1]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée pour un tableau non DataFrame.")

    def test_chained_indexing_with_condition(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3], 'B': [3, 4, 5]})
result = df[df['A'] > 1]['B']
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Alerte attendue pour chained indexing avec condition.")

    def test_chained_indexing_with_method(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
result = df[df['A'] > 1]['B'].mean()
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Alerte attendue pour chained indexing suivi d'une méthode.")

    def test_iloc_usage(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
result = df.iloc[0, 1]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée pour l'utilisation de iloc.")

    def test_indexing_on_series(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
col = df['A']
val = col[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée pour l'indexation d'une série.")

    def test_double_indexing_on_dict(self):
        code = """
d = {'a': [1, 2, 3], 'b': [4, 5, 6]}
val = d['a'][1]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée pour double indexation sur un dict.")

    def test_chained_indexing_after_assignment(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
tmp = df['A']
result = tmp[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée si l'objet n'est plus un DataFrame.")

    def test_chained_indexing_indirect(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
foo = df
result = foo['A']['B']
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0,
                        "Alerte attendue pour chained indexing indirect.")

    def test_series_of_dataframe(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
s = df['A']
val = s.iloc[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                         "Aucune alerte ne doit être générée pour iloc sur une série.")

    def test_values_indexing(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3]})
val = df['A'].values[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte ne doit être générée pour .values[0]")

    def test_to_numpy_indexing(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3]})
val = df['A'].to_numpy()[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte ne doit être générée pour .to_numpy()[0]")

    def test_values_method(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3]})
val = df['A'].values.sum()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte ne doit être générée pour .values.sum()")

    def test_to_numpy_method(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3]})
val = df['A'].to_numpy().mean()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte ne doit être générée pour .to_numpy().mean()")

    def test_chained_indexing_multilevel(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[{'B': [1,2]}, {'B':[3,4]}]})
result = df['A'][0]['B'][1]
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Alerte attendue pour chain indexing multilevel (df['A'][0]['B'][1])")

    def test_chained_indexing_multiple_on_dataframe(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3], 'B':[4,5,6]})
result = df['A'][1:][0]
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Alerte attendue pour chained indexing multiple sur DataFrame")

    def test_not_dataframe_object(self):
        code = """
class Dummy:
    def __getitem__(self, x):
        return [1,2,3]
dummy = Dummy()
result = dummy[0][1]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte pour double indexation sur un objet custom")

    def test_method_on_dataframe_direct(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3]})
result = df.mean()
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte pour méthode directe sur DataFrame")

    def test_chained_indexing_multiple_on_dataframe(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3], 'B':[4,5,6]})
result = df['A'][1:][0]
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Alerte attendue pour chained indexing multiple sur DataFrame")

    def test_chained_indexing_with_str_accessor(self):
        code = """
import pandas as pd
df = pd.DataFrame({'label(s)': ['cat,dog','mouse']})
df['top_label'] = df["label(s)"].str.split(",").str[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte attendue pour .str split puis .str[0] (pas du chained indexing)")

    def test_chained_indexing_with_values(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1,2,3]})
x = df['A'].values[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte attendue pour .values[0] (pas du chained indexing)")

    def test_chained_indexing_with_apply(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3]})
result = df['A'].apply(lambda x: x+1)[0]
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte attendue pour .apply suivi d'un index")

    def test_chained_indexing_on_dataframe_direct(self):
        code = """
import pandas as pd
df = pd.DataFrame({'A':[1,2,3], 'B':[4,5,6]})
x = df['A']['B']
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Alerte attendue pour chained indexing direct df['A']['B']")



if __name__ == '__main__':
    unittest.main()
