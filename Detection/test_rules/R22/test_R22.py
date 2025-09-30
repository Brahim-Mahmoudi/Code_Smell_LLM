import ast
import unittest
import generated_rules_R22  # Le fichier généré contenant la règle R22

class TestGeneratedRules22(unittest.TestCase):
    def setUp(self):
        self.messages = []
        def report(message):
            self.messages.append(message)
        generated_rules_R22.report = report  # Remplace report() par une version qui stocke les messages

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R22.rule_R22(ast_node)  # Exécute la règle R22

    def test_no_scaling_before_pca(self):
        """Test détection absence de scaling avant PCA"""
        code = """
from sklearn.decomposition import PCA
clf = PCA(n_components=2)
clf.fit(X)
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Should report missing scaling before PCA.")
        self.assertIn("Call to a sensitive function detected without prior scaling", self.messages[0], "Message should indicate missing scaling.")

    def test_pipeline_with_scaling_correct(self):
        """Test pipeline avec scaling correct"""
        code = """
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
clf = make_pipeline(StandardScaler(), PCA(n_components=2))
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when scaling is applied in the pipeline.")

    def test_no_scaling_before_svc(self):
        """Test détection absence de scaling avant SVC"""
        code = """
from sklearn.svm import SVC
clf = SVC()
clf.fit(X, y)
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, "Should report missing scaling before SVC.")
        self.assertIn("Call to a sensitive function detected without prior scaling", self.messages[0], "Message should indicate missing scaling.")

    def test_pipeline_with_scaling_svc(self):
        """Test absence de détection quand SVC est dans un pipeline avec scaling"""
        code = """
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
clf = make_pipeline(StandardScaler(), SVC(gamma="auto"))
clf.fit(X, y)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when scaling is applied in the pipeline.")

    def test_scaler_assigned_to_variable(self):
        """Test scaler assigné à une variable avant l'utilisation d'une opération sensible"""
        code = """
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
clf = PCA(n_components=2)
clf.fit(X_scaled)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when scaling is explicitly applied before PCA.")

    def test_pipeline_with_custom_steps(self):
        """Test pipeline contenant un scaler et une opération sensible"""
        code = """
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC
pipeline = Pipeline([
    ("scaler", MinMaxScaler()),
    ("classifier", SVC())
])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when pipeline properly applies scaling.")

    def test_multiple_sensitive_operations_some_without_scaling(self):
        """Test plusieurs opérations sensibles, certaines sans scaling"""
        code = """
from sklearn.decomposition import PCA
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
X_scaled = StandardScaler().fit_transform(X)
clf1 = PCA(n_components=2)
clf1.fit(X)  # Pas de scaling ici !
clf2 = SVC()
clf2.fit(X_scaled, y)  # Scaling OK ici
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1, "Should report only for PCA, since SVC has scaling.")

if __name__ == '__main__':
    unittest.main()
