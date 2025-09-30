import ast
import unittest
import generated_rules_R12  # Assurez-vous que ce module contient la règle R12

class TestGeneratedRules12(unittest.TestCase):
    def setUp(self):
        # On réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # On "monkey-patche" la fonction report du module généré
        generated_rules_R12.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R12.rule_R12(ast_node)

    def test_detect_matrix_multiplication_misuse(self):
        # Test d'un usage incorrect de np.dot() pour la multiplication de matrices 2D
        code = """
import numpy as np
a = [[1, 0], [0, 1]]
b = [[4, 1], [2, 2]]
result = np.dot(a, b)
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Un usage incorrect de np.dot() pour la multiplication de matrices 2D aurait dû être détecté"
        )
        if len(self.messages) > 0:
            print("Message généré (basic):", self.messages[0])

    

    def test_no_misuse_when_using_matmul(self):
        # Test d'un usage correct avec np.matmul()
        code = """
import numpy as np
a = [[1, 0], [0, 1]]
b = [[4, 1], [2, 2]]
result = np.matmul(a, b)
"""
        self.run_rule(code)
        # Ici aussi, on n'attend aucun message car df n'est pas un DataFrame
        self.assertEqual(len(self.messages), 0, "Aucun usage incorrect de np.dot() pour la multiplication de matrices 2D n'aurait dû être détecté")
        if len(self.messages) > 0:
            print("Message généré (basic):", self.messages[0])


if __name__ == '__main__':
    unittest.main()
