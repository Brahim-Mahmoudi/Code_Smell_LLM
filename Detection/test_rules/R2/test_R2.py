import ast
import unittest
import generated_rules_R2  # Ton module contenant la règle R2

class TestRandomSeedRuleR2(unittest.TestCase):
    def setUp(self):
        self.messages = []
        def report(msg):
            self.messages.append(msg)
        generated_rules_R2.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R2.rule_R2(ast_node)

    def test_correct_seed_usage(self):
        """Test pour vérifier que les seeds correctement définis ne génèrent pas d'erreur"""
        code = """
import numpy as np
import torch
import tensorflow as tf
from sklearn.ensemble import RandomForestClassifier

# Seeds définis correctement
np.random.seed(42)
torch.manual_seed(42)
tf.random.set_seed(42)

# Utilisation d'opérations aléatoires
X = np.random.randn(100, 10)
noise = torch.rand(100)
features = tf.random.normal([100, 10])
model = RandomForestClassifier(random_state=42)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte ne devrait être générée")

    def test_random_operations_without_seed(self):
        """Test pour détecter les opérations aléatoires sans seed"""
        code = """
import numpy as np
import torch
import tensorflow as tf

# Opérations aléatoires sans seed
X = np.random.randn(100, 10)
noise = torch.rand(100)
features = tf.random.normal([100, 10])
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Des alertes devraient être générées pour absence de seed")

    def test_additional_random_operations(self):
        """Test pour détecter les opérations aléatoires supplémentaires"""
        code = """
import random
import string
import numpy as np
from torch.utils.data import DataLoader

# Python random operations
x = random.randint(0, 10)
y = random.choice(string.ascii_lowercase)
z = random.uniform(0, 1)
data = [1, 2, 3]
random.shuffle(data)

# Numpy additional operations
a = np.random.random(shape)
b = np.random.rand(100)
c = np.random.sample((100, 2))

# DataLoader with shuffle
loader = DataLoader(dataset, batch_size=32, shuffle=True)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Des opérations aléatoires sans seed devraient être détectées")

    def test_mixed_deterministic_and_random(self):
        """Test pour vérifier la détection correcte dans un code mixte"""
        code = """
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier

# Partie déterministe
X_det = np.array([[1, 2], [3, 4]])
model_det = LinearRegression()

# Partie aléatoire
X_rand = np.random.rand(100, 10)
model_rand = RandomForestClassifier()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Les parties aléatoires devraient être détectées")

    def test_sklearn_random_algorithms_without_seed(self):
        """Test pour détecter les algorithmes sklearn aléatoires sans random_state"""
        code = """
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split

# Algorithmes sans random_state
X_train, X_test, y_train, y_test = train_test_split(X, y)
rf = RandomForestClassifier()
kmeans = KMeans()
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Des algorithmes sklearn sans random_state devraient être détectés")

    def test_complex_nested_random_calls(self):
        """Test pour détecter les appels aléatoires profondément imbriqués"""
        code = """
import numpy as np
import array_module
import mx

def test_function(gluon_random_data_run):
    model = mlflow.gluon.load_model("runs:/123/model", ctx)
    # Appel complexe imbriqué
    result = model(array_module.array(np.random.rand(1000, 1, 32)))
    other_result = complex_function(
        first_arg=process_data(np.random.random(100)),
        second_arg=array_module.process(np.random.randn(50, 3))
    )
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Des appels aléatoires imbriqués devraient être détectés")

    def test_random_assignment(self):
        """Test pour détecter les appels à random dans les assignations"""
        code = """
import random

def _generate_string(sep, integer_scale):
    predicate = random.choice(["a", "b"]).lower()
    noun = random.choice(["x", "y"]).lower()
    num = random.randint(0, 10**integer_scale)
    return f"{predicate}{sep}{noun}{sep}{num}"
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Les appels à random devraient être détectés même dans les fonctions")

    def test_DataLoader(self):
        """Test pour détecter l'absence de seed lors de l'utilisation d'un DataLoader avec shuffle=True"""
        code = """
import torch
from torch.utils.data import DataLoader
dataset = list(range(100))
batch_size = 32
num_workers = 4
# DataLoader avec shuffle=True
dataloader = DataLoader(dataset, batch_size=batch_size, num_workers=num_workers, shuffle=True, drop_last=False)
"""
        self.run_rule(code)
        self.assertGreater(len(self.messages), 0, "Une alerte devrait être générée pour DataLoader avec shuffle=True sans seed")

    def test_DataLoader_shuffle_false(self):
        """Test pour vérifier qu'un DataLoader avec shuffle=False ne génère pas d'alerte de seed manquante"""
        code = """
import torch
from torch.utils.data import DataLoader
dataset = list(range(100))
batch_size = 32
num_workers = 4
# DataLoader avec shuffle=False
dataloader = DataLoader(dataset, batch_size=batch_size, num_workers=num_workers, shuffle=False, drop_last=False)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Aucune alerte ne devrait être générée pour DataLoader avec shuffle=False")

if __name__ == '__main__':
    unittest.main()
