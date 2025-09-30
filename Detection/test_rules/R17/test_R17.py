import ast
import unittest
import generated_rules_R17  # Le module généré contenant la règle R17

class TestGeneratedRules17(unittest.TestCase):
    def setUp(self):
        # Réinitialise la liste des messages pour chaque test
        self.messages = []
        def report(message):
            self.messages.append(message)
        # "Monkey-patch" de la fonction report du module généré
        generated_rules_R17.report = report

    def run_rule(self, code):
        ast_node = ast.parse(code)
        generated_rules_R17.rule_R17(ast_node)

    def test_iterrows_detection(self):
        """Détecte l'utilisation de iterrows sur un DataFrame"""
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
for index, row in df.iterrows():
    print(row['A'])
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, 
                        "Une itération via iterrows aurait dû être détectée")
        if self.messages:
            print("Message généré (iterrows):", self.messages[0])

    def test_itertuples_detection(self):
        """Détecte l'utilisation de itertuples sur un DataFrame"""
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
for row in df.itertuples():
    print(row.A)
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, 
                        "Une itération via itertuples aurait dû être détectée")
        if self.messages:
            print("Message généré (itertuples):", self.messages[0])

    def test_tensorflow_loop_detection(self):
        """Détecte une boucle Python sur un tenseur TensorFlow"""
        code = """
import tensorflow as tf
x = tf.random.uniform([500, 10])
z = tf.zeros([10])
for i in range(500):
    z += x[i]
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, 
                        "Une itération sur un tenseur via boucle Python aurait dû être détectée")
        if self.messages:
            print("Message généré (TensorFlow):", self.messages[0])

    def test_no_false_positive_on_non_dataframe_chain(self):
        """Ne détecte pas un faux positif sur une chaîne d'appels qui n'est pas une DataFrame"""
        code = """
class CustomCollection:
    def query(self, x):
        return self
    def sort_values(self, x):
        return [1, 2, 3]

collection = CustomCollection()
filtered_collection = collection.query("A > 1").sort_values("B")

for item in filtered_collection:
    print(item)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0,
                     "Aucun message ne devrait être généré pour une itération sur un objet non-DataFrame")

    def test_values_complexe(self):
        code ="""
cv_results_df = pd.DataFrame.from_dict(cv_estimator.cv_results_)

if max_tuning_runs is None:
    cv_results_best_n_df = cv_results_df
else:
    rank_column_name = "rank_test_score"
    if rank_column_name not in cv_results_df.columns.values:
        rank_column_name = first_custom_rank_column(cv_results_df)
        warnings.warn(
            f"Top {max_tuning_runs} child runs will be created based on ordering in "
            f"{rank_column_name} column.  You can choose not to limit the number of "
            "child runs created by setting `max_tuning_runs=None`."
        )
    cv_results_best_n_df = cv_results_df.nsmallest(max_tuning_runs, rank_column_name)
    # Log how many child runs will be created vs omitted.
    _log_child_runs_info(max_tuning_runs, len(cv_results_df))

for _, result_row in cv_results_best_n_df.iterrows():
    tags_to_log = dict(child_tags) if child_tags else {}
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, 
                        "Une itération via iterrows aurait dû être détectée")
        if self.messages:
            print("Message généré (TensorFlow):", self.messages[0])


    def test_vectorized_no_issue(self):
        """Ne signale pas une opération vectorisée"""
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
result = df.add(1)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, 
                         "Aucun message ne devrait être généré pour une opération vectorisée")

    def test_loop_over_list_no_issue(self):
        """Ne signale pas une boucle classique sur une liste"""
        code = """
data = [1, 2, 3]
for item in data:
    print(item)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, 
                         "Aucun message ne devrait être généré pour une boucle sur une liste classique")
        
    def test_dataframe_transformation_chain_iterrows(self):
        """Détecte une itération via iterrows sur un DataFrame transformé en chaîne"""
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
filtered_df = df.query("A > 1").sort_values("B")
for _, row in filtered_df.iterrows():
    print(row["A"])
"""
        self.run_rule(code)
        self.assertTrue(len(self.messages) > 0, 
                        "Une itération via iterrows sur un DataFrame transformé aurait dû être détectée")
        if self.messages:
            print("Message généré (transform_chain):", self.messages[0])


if __name__ == '__main__':
    unittest.main()
