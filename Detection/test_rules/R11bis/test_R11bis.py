
import ast
import unittest
import generated_rules_R11bis  

class TestRuleR11bis(unittest.TestCase):
    def setUp(self):
        self.messages = []
        generated_rules_R11bis.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        tree = ast.parse(code)
        generated_rules_R11bis.rule_R11bis(tree)

    def test_correct_pipeline_usage(self):
        code = """
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y)
pipeline = Pipeline([
    ('scaler', StandardScaler())
])
pipeline.fit(X_train, y_train)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0)

    def test_multiple_transformations_without_pipeline(self):
        code = """
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA

scaler1 = StandardScaler()
X_scaled = scaler1.fit_transform(X)

scaler2 = MinMaxScaler()
X_scaled = scaler2.fit_transform(X_scaled)

pca = PCA(n_components=2)
X_final = pca.fit_transform(X_scaled)

model.fit(X_final, y)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0)
