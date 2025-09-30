import ast
import unittest
import generated_rules_R11  

class TestRuleR11(unittest.TestCase):
    def setUp(self):
        self.messages = []
        generated_rules_R11.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        tree = ast.parse(code)
        generated_rules_R11.rule_R11(tree)

    def test_no_transformations(self):
        code = """
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0)

    def test_transformation_before_split(self):
        code = """
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0)

    def test_feature_selection_before_split(self):
        code = """
from sklearn.feature_selection import SelectKBest
from sklearn.model_selection import train_test_split
selector = SelectKBest(k=10)
X_selected = selector.fit_transform(X, y)
X_train, X_test, y_train, y_test = train_test_split(X_selected, y)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0)
