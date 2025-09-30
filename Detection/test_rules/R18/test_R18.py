import ast
import unittest
import generated_rules_R18  

class TestGeneratedRules18(unittest.TestCase):
    def setUp(self):
        # Réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # On "monkey-patche" la fonction report du module généré
        generated_rules_R18.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R18.rule_R18(ast_node)

    def test_nanComparison(self):
        code = """
if value == np.nan: pass
if other == np.nan: pass
"""
        self.run_rule(code)
        # Vérifier qu'au moins un message a été généré
        self.assertTrue(len(self.messages) > 0,
                        "Une alerte doit être générée pour le chained indexing.")
        
        # Extraire le numéro de ligne de chaque message
        line_numbers = [msg.split("at line ")[-1].strip() for msg in self.messages]
        # Conserver uniquement les messages dont le numéro de ligne n'est pas "?"
        valid_messages = {msg for msg, line in zip(self.messages, line_numbers) if line != "?"}
        
        # Afficher les messages uniques
        print("Messages uniques générés:")
        for i, msg in enumerate(valid_messages, 1):
            print(f"Message {i}: {msg}")



   

if __name__ == '__main__':
    unittest.main()
