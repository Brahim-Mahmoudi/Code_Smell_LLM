import ast
import unittest
import sys
import os

# Ensure the generated_rules_R24 module in the same directory is importable
sys.path.insert(0, os.path.dirname(__file__))
import generated_rules_R24  # The file generated for rule R24

class TestGeneratedRules24(unittest.TestCase):
    def setUp(self):
        # Capture reported messages
        self.messages = []
        def report(message):
            self.messages.append(message)
        # Monkey-patch the report function in the generated module
        generated_rules_R24.report = report

    def run_rule(self, code: str):
        """Parse code and run the R24 rule on its AST."""
        self.messages.clear()
        tree = ast.parse(code)
        # Add parent links if needed by predicates
        from generated_rules_R24 import add_parent_info
        add_parent_info(tree)
        # Execute the rule function
        generated_rules_R24.rule_R24(tree)

    def test_read_csv_without_index_col(self):
        """Should report when pd.read_csv is called without index_col."""
        code = """
import pandas as pd
df = pd.read_csv("data.csv")
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for missing index_col")
        self.assertIn("pd.read_", self.messages[0])
        self.assertIn("index_col", self.messages[0])

    def test_read_csv_with_index_col(self):
        """Should not report when index_col is explicitly set."""
        code = """
import pandas as pd
df = pd.read_csv("data.csv", index_col='id')
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report when index_col is provided")

    def test_read_json_without_index_col(self):
        """Should report for other pandas read_* calls without index_col."""
        code = """
import pandas as pd
data = pd.read_json("data.json")
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for missing index_col on read_json")

    def test_read_excel_with_index_col(self):
        """Should not report when index_col is provided to read_excel."""
        code = """
import pandas as pd
sheet = pd.read_excel("file.xlsx", index_col=0)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report when index_col is provided to read_excel")

if __name__ == '__main__':
    unittest.main()

