import ast
import unittest
import generated_rules_R9  # Le module généré contenant la règle R9

class TestRuleR9(unittest.TestCase):
    def setUp(self):
        # Capture les messages générés par la fonction report
        self.messages = []
        generated_rules_R9.report = lambda msg: self.messages.append(msg)

    def run_rule(self, code):
        # Parse le code source et exécute la règle R9 sur l'AST
        ast_node = ast.parse(code)
        generated_rules_R9.rule_R9(ast_node)

    def test_basic_gradient_not_cleared(self):
        """
        Test du cas basique sans zero_grad
        """
        code = """
def training_loop():
    for batch in trainloader:
        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
"""
        self.run_rule(code)
        self.assertTrue(
            len(self.messages) > 0,
            "Une alerte devrait être générée car zero_grad() n'est jamais appelé avant backward()"
        )

    def test_correct_gradient_clearing(self):
        """
        Test avec zero_grad correctement placé
        """
        code = """
def training_loop():
    for batch in trainloader:
        optimizer.zero_grad()
        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucune alerte ne devrait être générée car zero_grad() est appelé avant backward()"
        )

    def test_alternative_gradient_clearing(self):
        """
        Test avec des méthodes alternatives de réinitialisation des gradients
        """
        code = """
def training_loop():
    for batch in trainloader:
        model.zero_grad()  # Via le modèle
        outputs = net(inputs)
        loss.backward()
        optimizer.step()

    for batch in trainloader:
        optimizer.zero_grad(set_to_none=True)  # Avec paramètre
        outputs = net(inputs)
        loss.backward()
        optimizer.step()
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucune alerte ne devrait être générée car une forme de zero_grad() est utilisée avant backward()"
        )

    def test_validation_context(self):
        """
        Test dans un contexte de validation
        """
        code = """
def validate():
    with torch.no_grad():
        for batch in loader:
            outputs = net(inputs)
            loss = criterion(outputs, labels)
            loss.backward()  # OK car dans no_grad
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucune alerte ne devrait être générée en phase de validation (no_grad)"
        )

    def test_mixed_training_validation(self):
        """
        Test avec mélange d'entraînement et validation
        """
        code = """
def mixed_loop():
    # Partie entraînement
    for batch in trainloader:
        optimizer.zero_grad()
        outputs = net(inputs)
        loss.backward()
        optimizer.step()

    # Partie validation
    with torch.no_grad():
        for batch in valloader:
            outputs = net(inputs)
            loss = criterion(outputs, labels)
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucune alerte ne devrait être générée pour la partie entraînement (zero_grad présent) ni la validation (no_grad)"
        )

    def test_gradient_accumulation(self):
        """
        Test avec accumulation intentionnelle de gradients
        """
        code = """
def training_with_accumulation():
    optimizer.zero_grad()  # Une seule fois au début
    for i, batch in enumerate(trainloader):
        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        if (i + 1) % accumulation_steps == 0:
            optimizer.step()
            optimizer.zero_grad()
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages), 0,
            "Aucune alerte ne devrait être générée, l'accumulation est intentionnelle et on appelle bien zero_grad avant ou après certaines itérations"
        )

    def test_paddle_backward_clear_grad_ok(self):
        """
        Vérifie qu'en environnement Paddle, appeler backward() puis clear_grad() 
        n'est pas signalé comme un problème.
        """
        code = """
import paddle
import paddle.nn.functional as F

def paddle_training_loop():
    model = SomePaddleModel()
    opt = paddle.optimizer.SGD(learning_rate=0.01, parameters=model.parameters())
    for epoch in range(1):
        inputs = paddle.to_tensor([1.0, 2.0, 3.0])
        preds = model(inputs)
        loss = F.square_error_cost(preds, paddle.to_tensor([1.0, 0.0, 0.0]))
        avg_loss = paddle.mean(loss)
        avg_loss.backward()
        opt.step()
        opt.clear_grad()
"""
        self.run_rule(code)
        # On s'attend à 0 message d'avertissement, 
        # car backward() puis clear_grad() est OK en Paddle
        self.assertEqual(
            len(self.messages), 0,
            "Aucun message ne devrait être généré pour la séquence backward() -> step() -> clear_grad() en Paddle"
        )

    def test_paddle_no_clear_grad_detected(self):
        """
        Vérifie qu'en environnement Paddle, si on appelle backward() 
        sans clear_grad() ni zero_grad(), la règle signale un problème.
        """
        code = """
import paddle
import paddle.nn.functional as F

def paddle_training_loop():
    model = SomePaddleModel()
    opt = paddle.optimizer.SGD(learning_rate=0.01, parameters=model.parameters())
    for epoch in range(1):
        inputs = paddle.to_tensor([1.0, 2.0, 3.0])
        preds = model(inputs)
        loss = F.square_error_cost(preds, paddle.to_tensor([1.0, 0.0, 0.0]))
        avg_loss = paddle.mean(loss)
        avg_loss.backward()
        opt.step()
        # Oubli de clear_grad() => devrait être signalé
"""
        self.run_rule(code)
        # On s'attend à >= 1 message car le backward() est sans clear_grad()
        self.assertGreater(
            len(self.messages), 0,
            "Un avertissement devrait être généré en absence de clear_grad()"
        )


if __name__ == '__main__':
    unittest.main()
