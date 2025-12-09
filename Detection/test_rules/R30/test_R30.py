import ast
import unittest
import sys
import os

# Ensure the generated_rules_R30 module in the same directory is importable
sys.path.insert(0, os.path.dirname(__file__))
import generated_rules_R30  # The file generated for rule R30 (Reasoning Effort Not Explicitly Set)


class TestGeneratedRules30(unittest.TestCase):
    def setUp(self):
        # Capture reported messages
        self.messages = []

        def report(message):
            self.messages.append(message)

        # Monkey-patch the report function in the generated module
        generated_rules_R30.report = report

    def run_rule(self, code: str):
        """Parse code and run the R30 rule on its AST."""
        self.messages.clear()
        tree = ast.parse(code)
        # make sure parent pointers exist
        if hasattr(generated_rules_R30, "add_parent_info"):
            generated_rules_R30.add_parent_info(tree)
        generated_rules_R30.rule_R30(tree)

    # ========== TRUE POSITIVES (should report MISSING REASONING EFFORT) ==========

    def test_openai_reasoning_model_no_effort(self):
        """OpenAI reasoning model without reasoning parameter -> REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role": "user", "content": "Solve this complex problem"}],
    temperature=0.2
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for reasoning model without reasoning effort")

    def test_openai_o1_model_no_reasoning_effort(self):
        """OpenAI o1 model without reasoning_effort -> REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="o1-preview",
    messages=[{"role":"user","content":"Complex reasoning task"}]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for o1 model without reasoning_effort")

    def test_openai_o1_mini_no_reasoning_effort(self):
        """OpenAI o1-mini model without reasoning_effort -> REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="o1-mini",
    messages=[{"role":"user","content":"Analyze this"}],
    temperature=0.5
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for o1-mini without reasoning_effort")

    def test_anthropic_claude_thinking_mode_not_set(self):
        """Anthropic Claude without thinking parameter -> REPORT."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Complex reasoning task"}]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Claude reasoning model without thinking parameter")

    def test_google_gemini_thinking_mode_not_set(self):
        """Google Gemini 2.0 thinking model without thinking config -> REPORT."""
        code = """
import google.generativeai as genai
model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
response = model.generate_content("Solve this complex problem")
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Gemini thinking model without thinking config")

    def test_multiple_reasoning_calls_no_effort(self):
        """Two reasoning model calls without effort -> expect two reports."""
        code = """
from openai import OpenAI
client = OpenAI()
r1 = client.responses.create(model="gpt-5.1-mini-2025-02-01", input=[{"role":"user","content":"A"}])
r2 = client.responses.create(model="o1-preview", input=[{"role":"user","content":"B"}])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 2, "Expected exactly two reports for two reasoning calls without effort")

    # ========== TRUE NEGATIVES (reasoning effort explicitly set should NOT report) ==========

    def test_openai_with_reasoning_effort_minimal(self):
        """OpenAI with reasoning effort set to minimal -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role": "user", "content": "Solve this"}],
    temperature=0.2,
    reasoning={"effort": "minimal"}
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect report when reasoning effort is explicitly set")

    def test_openai_with_reasoning_effort_medium(self):
        """OpenAI with reasoning effort set to medium -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="o1-preview",
    input=[{"role": "user", "content": "Complex task"}],
    reasoning={"effort": "medium"}
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect report when reasoning effort medium is set")

    def test_openai_with_reasoning_effort_high(self):
        """OpenAI with reasoning effort set to high -> NO REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="o1-mini",
    messages=[{"role":"user","content":"Safety critical analysis"}],
    reasoning_effort="high"
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect report when reasoning_effort is high")

    def test_anthropic_with_thinking_enabled(self):
        """Anthropic Claude with thinking enabled -> NO REPORT."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Complex reasoning"}],
    thinking={"type": "enabled", "budget_tokens": 5000}
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect report when thinking is explicitly configured")

    def test_google_gemini_with_thinking_config(self):
        """Google Gemini with thinking config -> NO REPORT."""
        code = """
import google.generativeai as genai
model = genai.GenerativeModel(
    "gemini-2.0-flash-thinking-exp-01-21",
    generation_config={"thinking_config": {"mode": "enabled"}}
)
response = model.generate_content("Solve this")
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect report when thinking_config is set")

    def test_openai_with_reasoning_depth(self):
        """OpenAI with reasoning_depth parameter -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role": "user", "content": "Task"}],
    reasoning_depth=3
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect report when reasoning_depth is set")

    # ========== FALSE POSITIVES TO AVOID ==========

    def test_non_reasoning_model_gpt4(self):
        """Non-reasoning model (GPT-4) without reasoning params -> NO REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role":"user","content":"Simple task"}]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Non-reasoning models should not be flagged")

    def test_non_reasoning_model_gpt_35(self):
        """Non-reasoning model (GPT-3.5) -> NO REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role":"user","content":"Task"}],
    temperature=0.7
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "GPT-3.5 is not a reasoning model")

    def test_non_reasoning_claude_model(self):
        """Non-reasoning Claude model -> NO REPORT."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Task"}]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Non-reasoning Claude models should not be flagged")

    def test_non_llm_create_call(self):
        """Non-LLM object with create method -> NO REPORT."""
        code = """
class CustomClient:
    def create(self, model, input): return None

client = CustomClient()
result = client.create(model="some-model", input="data")
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Non-LLM create() should not be flagged")

    # ========== MIXED CASES ==========

    def test_mixed_reasoning_and_non_reasoning(self):
        """One reasoning model without effort, one non-reasoning -> report only reasoning."""
        code = """
import openai

# Reasoning model without effort
resp1 = openai.ChatCompletion.create(
    model="o1-preview",
    messages=[{"role":"user","content":"A"}]
)

# Non-reasoning model
resp2 = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role":"user","content":"B"}]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1, "Should report only the reasoning model without effort")

    def test_mixed_with_and_without_effort(self):
        """One reasoning call with effort, one without -> report only the one without."""
        code = """
from openai import OpenAI
client = OpenAI()

# Without effort
r1 = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role":"user","content":"A"}]
)

# With effort
r2 = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role":"user","content":"B"}],
    reasoning={"effort": "high"}
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1, "Should report only the call without reasoning effort")


if __name__ == '__main__':
    unittest.main()