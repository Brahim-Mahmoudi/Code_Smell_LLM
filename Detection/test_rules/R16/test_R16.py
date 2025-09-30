import ast
import unittest
import generated_rules_R16  # module contenant rule_R16 et les fonctions utilitaires associées

class TestGeneratedRules16(unittest.TestCase):
    def setUp(self):
        self.messages = []
        def report(message):
            self.messages.append(message)
        generated_rules_R16.report = report

    def run_rule(self, code):
        tree = ast.parse(code)
        generated_rules_R16.add_parent_info(tree)
        generated_rules_R16.rule_R16(tree)

    def test_detect_api_misuse_assignment(self):
        code = """
import pandas as pd
df = pd.DataFrame({'col': [1,2,3]})
df.drop(columns=['col'], inplace=False)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 
            1, 
            "Un usage incorrect de l'API aurait dû être détecté (réassignation manquante)"
        )
        self.assertIn(
            "API call might be missing reassignment or inplace=True", 
            self.messages[0]
        )

    def test_detect_api_misuse_inplace(self):
        code = """
import pandas as pd
df = pd.DataFrame({'col': [1,2,3]})
df.dropna()
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 
            1, 
            "Un usage incorrect de l'API aurait dû être détecté (inplace=True manquant)"
        )
        self.assertIn(
            "API call might be missing reassignment or inplace=True", 
            self.messages[0]
        )

    def test_detect_api_misuse_correct(self):
        code = """
import pandas as pd
df = pd.DataFrame({'col': [1,2,3]})
df = df.drop(columns=['col'])
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 
            0, 
            "Aucun usage incorrect de l'API n'aurait dû être détecté"
        )

    def test_detect_multiple_api_misuses(self):
        code = """
import pandas as pd
import numpy as np
df = pd.DataFrame({'col': [1,2,3]})
df.drop(columns=['col'], inplace=False)
df.sort_values(by='col', inplace=False)
import numpy as np
zhats = [2, 3, 1, 0]
np.clip(zhats, -1, 1)
zhats = np.clip(zhats, -1, 1)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 
            3, 
            "Trois mauvais usages des API auraient dû être détectés"
        )

    def test_no_misuse_when_no_reassignment(self):
        code = """
import pandas as pd
df = pd.DataFrame({'old': ['x','y']})
df = df.replace('old', 'new')
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Aucun mauvais usage des API n'aurait dû être détecté"
        )

    def test_no_misuse_when_inplace_true(self):
        code = """
import pandas as pd
df = pd.DataFrame({'col': [1,None,3]})
df.dropna(inplace=True)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Aucun mauvais usage des API n'aurait dû être détecté (inplace=True)"
        )

    def test_no_misuse_when_method_is_not_in_list(self):
        code = """
import pandas as pd
df = pd.DataFrame({'col': [1,2,3]})
df.some_other_method()
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Aucun mauvais usage des API n'aurait dû être détecté (méthode non listée)"
        )

    def test_no_misuse_with_different_variable_assignment(self):
        code = """
import pandas as pd
df = pd.DataFrame({'target': [1,2,3]})
inputs = df.drop(columns=['target'])
unique_id = text.replace("/", "-")
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Aucun mauvais usage ne devrait être détecté quand le résultat est assigné à une nouvelle variable"
        )

    def test_no_misuse_in_function_arguments(self):
        code = """
import pandas as pd
df = pd.DataFrame({'timestamp': [1,2,3]})
transformer = ColumnTransformer([
    ("selector", "passthrough", df.drop(columns=["timestamp"]))
])
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Aucun mauvais usage ne devrait être détecté quand utilisé comme argument de fonction"
        )

    def test_no_misuse_in_return_statement(self):
        code = """
import pandas as pd
df = pd.DataFrame({'unused': [1,2,3]})
def process_data():
    return df.drop(columns=['unused'])
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Aucun mauvais usage ne devrait être détecté quand utilisé dans un return"
        )

if __name__ == '__main__':
    unittest.main()
