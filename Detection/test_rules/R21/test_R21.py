import ast
import unittest
import generated_rules_R21

class TestGeneratedRules21(unittest.TestCase):
    def setUp(self):
        self.messages = []
        def report(message):
            self.messages.append(message)
        generated_rules_R21.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R21.rule_R21(ast_node)

    def test_read_csv_no_dtype(self):
        code = """
import pandas as pd
df = pd.read_csv('data.csv')
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Should report missing dtype.")

    def test_read_csv_with_dtype(self):
        code = """
import pandas as pd
df = pd.read_csv('data.csv', dtype={'col1': 'int64', 'col2': 'float64'})
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when dtype is provided.")

    def test_read_json_no_dtype(self):
        code = """
import pandas as pd
df = pd.read_json('data.json')
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Should report missing dtype in read_json.")

    def test_read_sql_no_dtype(self):
        code = """
import pandas as pd
df = pd.read_sql('SELECT * FROM table', connection)
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Should report missing dtype in read_sql.")

    def test_read_csv_inside_function(self):
        code = """
import pandas as pd
def load_data():
    return pd.read_csv('data.csv')
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Should report missing dtype inside function.")

    def test_read_csv_attribute_assignment(self):
        code = """
import pandas as pd
self._content = pd.read_csv(local_artifact_path)
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Should report missing dtype for attribute assignment.")

    def test_multiple_read_calls_no_dtype(self):
        code = """
import pandas as pd
df1 = pd.read_csv('data1.csv')
df2 = pd.read_json('data2.json')
df3 = pd.read_sql('SELECT * FROM table', conn)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 3, "Should report missing dtype for all three read calls.")

    def test_mixed_dtype_provided(self):
        code = """
import pandas as pd
df1 = pd.read_csv('data1.csv', dtype={'col1': 'int64'})
df2 = pd.read_json('data2.json')
df3 = pd.read_csv('data3.csv', dtype={'col2': 'float64'})
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1, "Should report missing dtype only for read_json.")

if __name__ == '__main__':
    unittest.main()
