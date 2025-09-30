import ast
import unittest
import generated_rules_R23  # Le fichier généré contenant la règle R23

class TestGeneratedRules23(unittest.TestCase):
    def setUp(self):
        self.messages = []
        def report(message):
            self.messages.append(message)
        generated_rules_R23.report = report  # Remplace report() par une version qui stocke les messages

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R23.rule_R23(ast_node)  # Exécute la règle R23
    def test_fit_without_callbacks(self):
        """Doit signaler absence de callbacks"""
        code = """
from keras.models import Sequential
model = Sequential()
model.fit(X, y)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Should report missing callbacks when none provided.")
        self.assertIn("Model.fit() called without EarlyStopping callback", self.messages[0])

    def test_fit_with_other_callbacks(self):
        """Doit signaler si callbacks ne contient pas EarlyStopping"""
        code = """
from keras.models import Sequential
from keras.callbacks import ModelCheckpoint
model = Sequential()
model.fit(X, y, callbacks=[ModelCheckpoint('cp.ckpt')])
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Should report when callbacks provided but no EarlyStopping.")
        self.assertIn("Model.fit() called without EarlyStopping callback", self.messages[0])

    def test_fit_with_earlystopping(self):
        """Ne doit pas signaler quand EarlyStopping est présent"""
        code = """
from keras.models import Sequential
from keras.callbacks import EarlyStopping
model = Sequential()
model.fit(X, y, callbacks=[EarlyStopping(monitor='val_loss')])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when EarlyStopping callback is used.")

    def test_fit_with_multiple_callbacks_including_es(self):
        """Ne doit pas signaler si EarlyStopping fait partie des callbacks"""
        code = """
from keras.models import Sequential
from keras.callbacks import EarlyStopping, ModelCheckpoint
model = Sequential()
model.fit(X, y, callbacks=[ModelCheckpoint('cp.ckpt'), EarlyStopping(monitor='val_loss')])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when EarlyStopping is among callbacks.")

if __name__ == '__main__':
    unittest.main()
