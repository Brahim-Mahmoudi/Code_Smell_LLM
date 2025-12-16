import ast
import unittest
import sys
import os


sys.path.insert(0, os.path.dirname(__file__))
import generated_rules_R32  # The file generated for the Overspecified Sampling rule


class TestGeneratedRules32(unittest.TestCase):
    def setUp(self):
        # Capture reported messages
        self.messages = []

        def report(message):
            self.messages.append(message)

        # Monkey patch the report function in the generated module
        generated_rules_R32.report = report

    def run_rule(self, code: str):
        """Parse code and run the R32 rule on its AST."""
        self.messages.clear()
        tree = ast.parse(code)
        # Add parent links if needed by predicates
        from generated_rules_R32 import add_parent_info
        add_parent_info(tree)
        # Execute the rule function
        generated_rules_R32.rule_R32(tree)

    # TRUE POSITIVES - OpenAI

    def test_openai_completion_temperature_and_top_p(self):
        """Should report when OpenAI completion sets both temperature and top_p."""
        code = """
import openai
response = openai.Completion.create(
    model="text-davinci-003",
    prompt="Hello world",
    temperature=0.7,
    top_p=0.9,
    max_tokens=100
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for temperature + top_p")
        

    def test_openai_chat_temperature_and_top_k(self):
        """Should report when OpenAI ChatCompletion sets both temperature and top_k."""
        code = """
import openai
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.8,
    top_k=40
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for temperature + top_k")

    def test_openai_kwargs_temperature_and_top_p(self):
        """Should report when kwargs dict provides both temperature and top_p."""
        code = """
import openai
params = {
    "model": "gpt-4",
    "prompt": "Hello",
    "temperature": 0.6,
    "top_p": 0.95
}
response = openai.Completion.create(**params)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for overspecified sampling in kwargs")

    def test_openai_client_with_options_temperature_and_top_p(self):
        """Should report when client.with_options config sets temperature and top_p."""
        code = """
from openai import OpenAI
client = OpenAI()
with client.with_options(temperature=0.7, top_p=0.9):
    response = client.completions.create(
        model="gpt-3.5-turbo",
        prompt="Hi"
    )
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for overspecified sampling in with_options")

    def test_openai_client_with_options_temperature_and_top_k(self):
        """Should report when client.with_options config sets temperature and top_k."""
        code = """
from openai import OpenAI
client = OpenAI()
with client.with_options(temperature=0.7, top_k=20):
    response = client.completions.create(
        model="gpt-3.5-turbo",
        prompt="Hi"
    )
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for temperature + top_k in with_options")

    # TRUE POSITIVES - Anthropic

    def test_anthropic_completions_temperature_and_top_p(self):
        """Should report when Anthropic completion sets both temperature and top_p."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.completions.create(
    model="claude-3-opus-20240229",
    prompt="Hello world",
    temperature=0.7,
    top_p=0.9,
    max_tokens_to_sample=200
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Anthropic temperature + top_p")

    def test_anthropic_messages_temperature_and_top_k(self):
        """Should report when Anthropic messages.create sets temperature and top_k."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-haiku-20240307",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.6,
    top_k=40,
    max_tokens=128
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Anthropic temperature + top_k")

    # TRUE POSITIVES - Gemini / Vertex

    def test_gemini_generate_content_temperature_and_top_p(self):
        """Should report when Gemini generate_content sets both temperature and top_p."""
        code = """
from vertexai.generative_models import GenerativeModel

model = GenerativeModel("gemini-1.5-flash")
response = model.generate_content(
    "Hello",
    temperature=0.7,
    top_p=0.9
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Gemini temperature + top_p")

    # TRUE POSITIVES - HuggingFace pipeline

    def test_hf_pipeline_temperature_and_top_p(self):
        """Should report when HF pipeline output call sets temperature and top_p."""
        code = """
from transformers import pipeline
generator = pipeline("text-generation", model="gpt2")
result = generator(
    "Hello",
    temperature=0.7,
    top_p=0.9,
    max_length=50
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for HF pipeline temperature + top_p")

    # TRUE POSITIVES - LangChain constructors

    def test_langchain_chatopenai_temperature_and_top_p(self):
        """Should report when LangChain ChatOpenAI sets temperature and top_p."""
        code = """
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    top_p=0.9
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for LangChain ChatOpenAI temperature + top_p")

    # TRUE NEGATIVES - OpenAI

    def test_openai_completion_temperature_only(self):
        """Should not report when only temperature is set."""
        code = """
import openai
response = openai.Completion.create(
    model="text-davinci-003",
    prompt="Hello world",
    temperature=0.7,
    max_tokens=100
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for temperature only")

    def test_openai_completion_top_p_only(self):
        """Should not report when only top_p is set."""
        code = """
import openai
response = openai.Completion.create(
    model="text-davinci-003",
    prompt="Hello world",
    top_p=0.9,
    max_tokens=100
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for top_p only")

    def test_openai_completion_top_k_only(self):
        """Should not report when only top_k is set."""
        code = """
import openai
response = openai.Completion.create(
    model="text-davinci-003",
    prompt="Hello world",
    top_k=50,
    max_tokens=100
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for top_k only")

    def test_openai_no_sampling_parameters(self):
        """Should not report when no sampling parameters are set."""
        code = """
import openai
response = openai.Completion.create(
    model="text-davinci-003",
    prompt="Hello world",
    max_tokens=100
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report with no sampling parameters")

    def test_openai_with_options_temperature_only(self):
        """Should not report when with_options config sets only temperature."""
        code = """
from openai import OpenAI
client = OpenAI()
with client.with_options(temperature=0.4):
    response = client.completions.create(
        model="gpt-3.5-turbo",
        prompt="Hi"
    )
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for temperature only in with_options")

    def test_openai_with_options_top_p_only(self):
        """Should not report when with_options config sets only top_p."""
        code = """
from openai import OpenAI
client = OpenAI()
with client.with_options(top_p=0.9):
    response = client.completions.create(
        model="gpt-3.5-turbo",
        prompt="Hi"
    )
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for top_p only in with_options")

    # TRUE NEGATIVES - Anthropic

    def test_anthropic_completion_temperature_only(self):
        """Should not report when Anthropic completion sets only temperature."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.completions.create(
    model="claude-3-opus-20240229",
    prompt="Hello world",
    temperature=0.7,
    max_tokens_to_sample=200
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for Anthropic temperature only")

    # TRUE NEGATIVES - Gemini

    def test_gemini_generate_content_temperature_only(self):
        """Should not report when Gemini generate_content sets only temperature."""
        code = """
from vertexai.generative_models import GenerativeModel

model = GenerativeModel("gemini-1.5-flash")
response = model.generate_content(
    "Hello",
    temperature=0.7
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for Gemini temperature only")

    # TRUE NEGATIVES - HF pipeline

    def test_hf_pipeline_top_p_only(self):
        """Should not report when HF pipeline call sets only top_p."""
        code = """
from transformers import pipeline
generator = pipeline("text-generation", model="gpt2")
result = generator(
    "Hello",
    top_p=0.9,
    max_length=50
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Did not expect a report for HF top_p only")

    # NON LLM CASES

    def test_non_llm_api_call(self):
        """Should not report for non LLM API calls."""
        code = """
import requests
response = requests.get("https://api.example.com/data", timeout=5)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report for non LLM calls")

    def test_regular_function_with_sampling_like_params(self):
        """Should not report for user functions that take temperature and top_p."""
        code = """
def sample_text(text, temperature=1.0, top_p=0.9):
    return text

result = sample_text("Hello", temperature=0.7, top_p=0.8)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report for regular functions")

    # COMPLEX CASES

    def test_multiple_llm_calls_mixed_sampling(self):
        """Should only report for calls that overspecify sampling."""
        code = """
import openai

# Should be reported
response1 = openai.Completion.create(
    model="text-davinci-003",
    prompt="First",
    temperature=0.7,
    top_p=0.9
)

# Should not be reported
response2 = openai.Completion.create(
    model="text-davinci-003",
    prompt="Second",
    temperature=0.5
)

# Should not be reported
response3 = openai.Completion.create(
    model="text-davinci-003",
    prompt="Third",
    top_p=0.8
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1, "Should report exactly one overspecified sampling call")

    def test_kwargs_config_temperature_and_top_k(self):
        """Should report when config dict has temperature and top_k."""
        code = """
import openai
config = {
    "temperature": 0.6,
    "top_k": 30,
    "max_tokens": 50
}
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hi"}],
    **config
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for temperature + top_k in kwargs config")

    def test_kwargs_config_temperature_only(self):
        """Should not report when config dict only has temperature."""
        code = """
import openai
config = {
    "temperature": 0.6,
    "max_tokens": 50
}
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hi"}],
    **config
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when config has only temperature")


if __name__ == "__main__":
    unittest.main()
