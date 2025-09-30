import ast
import unittest
import generated_rules_R10  # Le module généré contenant la règle R10

class TestRuleR10(unittest.TestCase):
    def setUp(self):
        # Capture les messages générés par la fonction report
        self.messages = []
        generated_rules_R10.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        # Parse le code source et exécute la règle R10 sur l'AST
        ast_node = ast.parse(code)
        generated_rules_R10.rule_R10(ast_node)

    def test_detect_memory_not_freed_tensorflow(self):
        """
        Test d'un usage de TensorFlow sans clear_session() dans une boucle
        => On s'attend à au moins 1 message (car aucune API de libération mémoire n'est appelée)
        """
        code = """
import tensorflow as tf
for _ in range(100):
    model = tf.keras.Sequential([tf.keras.layers.Dense(10) for _ in range(10)])
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un avertissement devrait être généré car aucune API de libération mémoire n'est appelée en TensorFlow"
        )

    def test_detect_memory_not_freed_pytorch(self):
        """
        Test d'un usage de PyTorch sans .detach() 
        => On s'attend à au moins 1 message (car .detach() n'est jamais appelé)
        """
        code = """
import torch

# Création explicite d'un tenseur via torch
tensor1 = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
tensor2 = torch.tensor([[5.0, 6.0], [7.0, 8.0]])

# Appel de matmul sur un tenseur défini par torch.
output = tensor1.matmul(tensor2)

# Appel de add sans utiliser .detach(), ce qui devrait être détecté comme problème par la règle R10.
result = output.add(torch.tensor([[1.0, 1.0], [1.0, 1.0]]))

print(result)
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un avertissement devrait être généré car .detach() n'est jamais appelé pour libérer la mémoire en PyTorch"
        )

    def test_detect_memory_not_freed_tensorflow_correct(self):
        """
        Test d'un usage correct de TensorFlow avec clear_session() dans une boucle
        => On ne devrait pas avoir de message
        """
        code = """
import tensorflow as tf
for _ in range(100):
    tf.keras.backend.clear_session()
    model = tf.keras.Sequential([tf.keras.layers.Dense(10) for _ in range(10)])
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré, car clear_session() est appelé"
        )

    def test_detect_memory_not_freed_pytorch_correct(self):
        """
        Test d'un usage correct de PyTorch avec .detach() 
        => On ne devrait pas avoir de message
        """
        code = """
import torch
for _ in range(100):
    output = tensor1.matmul(tensor2)
    result = output.detach()
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré, car .detach() est appelé"
        )

    # Tests pour éviter les faux positifs

    def test_false_positive_git(self):
        """
        Test qu'un appel provenant de git (ex: repo.git.add) ne déclenche pas la règle.
        """
        code = """
import git
repo = git.Repo.init("dummy_repo")
repo.git.add(A=True)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré pour un appel git.add"
        )

    def test_false_positive_os(self):
        """
        Test qu'un appel à une fonction os ne déclenche pas la règle.
        """
        code = """
import os
os.path.join("a", "b")
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré pour os.path.join"
        )

    def test_false_positive_numpy(self):
        """
        Test qu'un appel à numpy.add ne déclenche pas la règle (numpy n'est pas PyTorch).
        """
        code = """
import numpy as np
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
c = np.add(a, b)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré pour np.add"
        )

    def test_fp_tensorflow_clear_session_outside_loop(self):
        """
        Test FP : clear_session appelé hors boucle (doit être détecté comme MEMORY NOT FREED !)
        """
        code = """
import tensorflow as tf
tf.keras.backend.clear_session()
for _ in range(100):
    model = tf.keras.Sequential([tf.keras.layers.Dense(10) for _ in range(10)])
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
        "Un avertissement doit être généré si clear_session() est appelé hors de la boucle."
    )

    def test_fn_pytorch_explicit_del(self):
        """
        Test FN : PyTorch avec suppression explicite via del (doit être reconnu comme libération mémoire)
        """
        code = """
import torch
tensor1 = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
output = tensor1.add(torch.tensor([[1.0, 1.0], [1.0, 1.0]]))
del output
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré si l'objet est supprimé explicitement via del."
    )

    def test_fn_pytorch_assign_none(self):
        """
        Test FN : PyTorch variable assignée à None (considéré comme libérée)
        """
        code = """
import torch
output = torch.tensor([1, 2, 3])
output = None
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré si la variable tensor est assignée à None."
    )

    def test_fp_numpy_array_reshape(self):
        """
        Test FP : np.array reshape (ne doit PAS déclencher la règle)
        """
        code = """
import numpy as np
a = np.array([1, 2, 3])
b = a.reshape((3, 1))
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré pour reshape sur un array NumPy."
    )


    def test_fp_dataframe_to_numpy(self):
        """
        Test FP : DataFrame to_numpy (usage recommandé, ne doit PAS déclencher la règle)
        """
        code = """
import pandas as pd
df = pd.DataFrame({'a':[1,2,3]})
arr = df.to_numpy().reshape(-1, 1)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne devrait être généré pour df.to_numpy().reshape()."
    )

    def test_fn_keras_multiple_models(self):
        """
        Test FN : Création de plusieurs modèles Keras sans clear_session à chaque boucle (should trigger!)
        """
        code = """
import tensorflow as tf
for _ in range(10):
    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Dense(10))
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un avertissement doit être généré pour création répétée de modèles sans clear_session dans la boucle."
    )

    def test_fp_sklearn_model(self):
        """
        Test FP : Utilisation d'un modèle scikit-learn (pas concerné par le code smell mémoire)
        """
        code = """
from sklearn.linear_model import LogisticRegression
import numpy as np
X = np.random.randn(100, 2)
y = np.random.randint(0, 2, size=100)
model = LogisticRegression().fit(X, y)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne doit être généré pour un modèle sklearn."
    )

    def test_fp_pytorch_tensor_cpu(self):
        """
        Test FP : .cpu() (transfert sur CPU, pas libération mémoire GPU réelle, ne doit PAS être confondu)
        """
        code = """
import torch
t = torch.tensor([1,2,3])
t = t.cpu()
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne doit être généré pour t.cpu() seul."
    )


    def test_fn_keras_sequential_in_loop_without_clear_session(self):
        """
        Test FN : Création répétée de modèles Sequential dans une boucle sans clear_session.
        On doit détecter un problème de mémoire non libérée.
        """
        code = """
from tensorflow.keras import Sequential, layers

for i in range(10):
    model = Sequential([
        layers.Dense(64, activation='relu'),
        layers.Dense(10, activation='softmax')
    ])
    """
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un avertissement doit être généré pour la création répétée de modèles Sequential sans clear_session dans la boucle."
        )

    def test_fn_keras_layers_list_in_loop_without_clear_session(self):
        """
        Test FN : Création répétée de couches (Dense, Conv2D) dans une liste dans une boucle sans clear_session.
        On doit détecter un problème de mémoire non libérée.
        """
        code = """
from tensorflow.keras import Sequential, layers

for i in range(5):
    hidden_layers = []
    for c in [32, 64, 128]:
        hidden_layers.append(layers.Dense(c, activation='relu'))
    model = Sequential(hidden_layers)
    """
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un avertissement doit être généré pour la création répétée de couches Dense sans clear_session dans la boucle."
        )

    def test_fp_keras_sequential_in_loop_with_clear_session(self):
        """
        Test FP : Création répétée de modèles Sequential dans une boucle AVEC clear_session.
        Aucun avertissement ne doit être généré.
        """
        code = """
from tensorflow.keras import Sequential, layers
from tensorflow.keras.backend import clear_session

for i in range(10):
    clear_session()
    model = Sequential([
        layers.Dense(64, activation='relu'),
        layers.Dense(10, activation='softmax')
    ])
    """
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne doit être généré car clear_session est bien appelé dans la boucle."
        )

    def test_fn_tf_sequential_in_loop_without_clear_session(self):
        """
        Test FN : Création répétée de tf.keras.Sequential dans une boucle sans clear_session.
        On doit détecter un problème de mémoire non libérée.
        """
        code = """
import tensorflow as tf

for i in range(10):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax')
    ])
    """
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un avertissement doit être généré pour la création répétée de tf.keras.Sequential sans clear_session dans la boucle."
        )

    def test_fp_tf_sequential_in_loop_with_clear_session(self):
        """
        Test FP : Création répétée de tf.keras.Sequential dans une boucle AVEC clear_session.
        Aucun avertissement ne doit être généré.
        """
        code = """
import tensorflow as tf

for i in range(10):
    tf.keras.backend.clear_session()
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax')
    ])
    """
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne doit être généré car clear_session est bien appelé dans la boucle."
        )

    def test_fn_pytorch_model_in_loop_without_detach(self):
        """
        Test FN : Création répétée de tensors PyTorch dans une boucle sans detach().
        On doit détecter un problème de mémoire non libérée.
        """
        code = """
import torch

for i in range(5):
    tensor1 = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    tensor2 = torch.tensor([[5.0, 6.0], [7.0, 8.0]])
    output = tensor1.matmul(tensor2)
    result = output.add(torch.tensor([[1.0, 1.0], [1.0, 1.0]]))
    """
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un avertissement doit être généré pour la création répétée de tensors sans detach() dans la boucle."
        )

    def test_fp_pytorch_model_in_loop_with_detach(self):
        """
        Test FP : Création répétée de tensors PyTorch dans une boucle AVEC detach().
        Aucun avertissement ne doit être généré.
        """
        code = """
import torch

for i in range(5):
    tensor1 = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    tensor2 = torch.tensor([[5.0, 6.0], [7.0, 8.0]])
    output = tensor1.matmul(tensor2)
    result = output.detach()
    """
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucun avertissement ne doit être généré car detach() est bien appelé dans la boucle."
        )


if __name__ == '__main__':
    unittest.main()
