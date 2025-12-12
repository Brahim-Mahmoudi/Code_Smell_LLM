import ast
import unittest
import sys
import os


sys.path.insert(0, os.path.dirname(__file__))
import generated_rules_R33  


class TestGeneratedRules32(unittest.TestCase):
    def setUp(self):
        # Capture reported messages
        self.messages = []

        def report(message):
            self.messages.append(message)

        # Monkey patch the report function in the generated module
        generated_rules_R33.report = report

    def run_rule(self, code: str):
        """Parse code and run the R33 rule on its AST."""
        self.messages.clear()
        tree = ast.parse(code)
        # Add parent links if needed by predicates
        from generated_rules_R33 import add_parent_info
        add_parent_info(tree)
        # Execute the rule function
        generated_rules_R33.rule_R33(tree)


    ####################################################################
    # TRUE POSITIVES
    # Multi user context is clearly visible
    # Provider supports user or user_id but call omits it
    ####################################################################

    def test_django_view_request_user_missing_user_param(self):
        """Django view uses request.user.id but OpenAI call has no user or metadata."""
        code = """
import openai

def chat_view(request):
    uid = request.user.id
    message = request.POST["message"]
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": message}
        ]
    )
    return response
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report for anonymous OpenAI ChatCompletion in Django view",
        )

    def test_django_view_request_user_access_inline_missing_user_param(self):
        """Django view reads request.user.id in the body but does not propagate it to user."""
        code = """
import openai

def chat_view(request):
    prompt = f"User {request.user.id} asked: " + request.POST["q"]
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report when request.user.id exists but is not passed to user",
        )

    def test_fastapi_endpoint_current_user_missing_user_param(self):
        """FastAPI endpoint has current_user.id but OpenAI call has no user or metadata."""
        code = """
import openai
from fastapi import Depends

class User:
    id: str

def get_current_user():
    return User()

def chat_endpoint(current_user: User = Depends(get_current_user)):
    text = "Hello " + str(current_user.id)
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text}]
    )
    return resp
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report for FastAPI endpoint without user propagation",
        )

    def test_session_user_id_missing_user_param_responses_api(self):
        """Function uses session['user_id'] but OpenAI responses.create omits user."""
        code = """
from openai import OpenAI

client = OpenAI()

def handle_inference(session):
    user_id = session["user_id"]
    result = client.responses.create(
        model="gpt-4.1-mini",
        input="Hello"
    )
    return result
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report when session user_id is not passed to responses.create user",
        )

    def test_anthropic_messages_missing_metadata_user_id(self):
        """Anthropic messages.create in multi user context uses metadata without user_id."""
        code = """
import anthropic

client = anthropic.Anthropic()

def chat_view(request):
    uid = request.user.id
    resp = client.messages.create(
        model="claude-3-haiku-20240307",
        messages=[{"role": "user", "content": "Hi"}],
        metadata={"project": "myapp"}
    )
    return resp
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report when Anthropic metadata has no user_id while request.user.id exists",
        )

    def test_kwargs_config_missing_user_and_metadata(self):
        """Multi user context with kwargs passed to OpenAI but no user or metadata key."""
        code = """
import openai

def chat_view(request):
    uid = request.user.id
    config = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    resp = openai.ChatCompletion.create(**config)
    return resp
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report for kwargs config without user or metadata in multi user context",
        )

    def test_mixed_calls_only_anonymous_openai_call_reported(self):
        """Only the call that omits user in a multi user context should be reported."""
        code = """
import openai

def handler(request):
    uid = request.user.id

    good = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hi"}],
        user=str(uid)
    )

    bad = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hi again"}]
    )

    return good, bad
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            1,
            "Expected exactly one report for the anonymous call",
        )

    ####################################################################
    # TRUE NEGATIVES
    # Either no clear multi user context
    # Or provider specific user_id is correctly propagated
    ####################################################################

    def test_single_user_script_no_request_object(self):
        """No multi user context so no report."""
        code = """
import openai

def generate_once():
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}]
    )
    return response
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report in a simple script without user context",
        )

    def test_django_view_with_openai_user_param(self):
        """Django view propagates request.user.id to OpenAI user parameter."""
        code = """
import openai

def chat_view(request):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
        user=str(request.user.id)
    )
    return response
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report when user is set from request.user.id",
        )

    def test_openai_responses_with_user_param_from_session(self):
        """OpenAI responses.create uses user from session['user_id']."""
        code = """
from openai import OpenAI

client = OpenAI()

def handle_inference(session):
    uid = session["user_id"]
    result = client.responses.create(
        model="gpt-4.1-mini",
        input="Hello",
        user=str(uid)
    )
    return result
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report when responses.create user is set from session user_id",
        )

    def test_anthropic_messages_with_metadata_user_id(self):
        """Anthropic messages.create includes metadata user_id from request.user.id."""
        code = """
import anthropic

client = anthropic.Anthropic()

def chat_view(request):
    uid = str(request.user.id)
    resp = client.messages.create(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": "Hello"}],
        metadata={"user_id": uid}
    )
    return resp
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report when metadata.user_id is present",
        )

    def test_fastapi_endpoint_with_metadata_dict_containing_user_id(self):
        """FastAPI endpoint builds metadata dict with user_id and passes it to OpenAI."""
        code = """
import openai
from fastapi import Depends

class User:
    id: str

def get_current_user():
    return User()

def endpoint(current_user: User = Depends(get_current_user)):
    meta = {"user_id": str(current_user.id), "project": "myapp"}
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hi"}],
        metadata=meta
    )
    return resp
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report when metadata dict contains user_id",
        )

    def test_non_llm_api_call_in_multi_user_context(self):
        """Non LLM HTTP call in multi user context should not be reported."""
        code = """
import requests

def view(request):
    uid = request.user.id
    resp = requests.get("https://api.example.com/data", timeout=5)
    return resp
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Should not report non LLM calls even if request.user.id is used",
        )

    def test_regular_helper_function_ignoring_user_id(self):
        """Local helper that ignores user id is not an LLM call."""
        code = """
def helper(text, user_id):
    return f"{user_id}: {text}"

def view(request):
    uid = request.user.id
    out = helper("hello", uid)
    return out
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Should not report regular helper functions",
        )

    def test_openai_chat_kwargs_with_metadata_user_id(self):
        """Should not report when user_id is present in metadata inside kwargs dict."""
        code = """
import openai

def chat_view(request):
    uid = request.user.id
    config = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "metadata": {"user_id": str(uid)}
    }
    resp = openai.ChatCompletion.create(**config)
    return resp
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report when metadata.user_id is provided via **kwargs",
        )

    def test_openai_chat_kwargs_without_metadata_user_id(self):
        """Should report when multi user context exists and kwargs miss any user identifier."""
        code = """
import openai

def chat_view(request):
    uid = request.user.id
    config = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "metadata": {"project": "myapp"}
    }
    resp = openai.ChatCompletion.create(**config)
    return resp
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report when metadata lacks user identifier in **kwargs",
        )

    def test_openai_responses_with_metadata_user_id(self):
        """Should not report when OpenAI responses.create uses metadata user_id from session."""
        code = """
from openai import OpenAI

client = OpenAI()

def handle_inference(session):
    uid = session["user_id"]
    meta = {"user_id": str(uid), "project": "analytics"}
    result = client.responses.create(
        model="gpt-4.1-mini",
        input="Hello",
        metadata=meta
    )
    return result
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report when responses.create metadata carries user_id",
        )

    def test_openai_responses_kwargs_metadata_without_user_id(self):
        """Should report when multi user context exists and metadata in kwargs lacks user_id."""
        code = """
from openai import OpenAI

client = OpenAI()

def handle_inference(session):
    uid = session["user_id"]
    params = {
        "model": "gpt-4.1-mini",
        "input": "Hello",
        "metadata": {"project": "dashboard"}
    }
    result = client.responses.create(**params)
    return result
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report when responses.create metadata in **params has no user_id",
        )

    def test_anthropic_messages_kwargs_with_metadata_user_id(self):
        """Should not report when Anthropic messages.create gets metadata.user_id via kwargs."""
        code = """
import anthropic

client = anthropic.Anthropic()

def chat_view(request):
    uid = request.user.id
    meta = {"user_id": str(uid), "project": "myapp"}
    args = {
        "model": "claude-3-haiku-20240307",
        "messages": [{"role": "user", "content": "Hi"}],
        "metadata": meta
    }
    resp = client.messages.create(**args)
    return resp
"""
        self.run_rule(code)
        self.assertEqual(
            len(self.messages),
            0,
            "Did not expect a report when Anthropic metadata.user_id flows through **args",
        )

    def test_anthropic_messages_kwargs_metadata_without_user_id(self):
        """Should report when Anthropic messages.create metadata lacks user_id in kwargs."""
        code = """
import anthropic

client = anthropic.Anthropic()

def chat_view(request):
    uid = request.user.id
    meta = {"project": "myapp"}
    args = {
        "model": "claude-3-haiku-20240307",
        "messages": [{"role": "user", "content": "Hi"}],
        "metadata": meta
    }
    resp = client.messages.create(**args)
    return resp
"""
        self.run_rule(code)
        self.assertTrue(
            self.messages,
            "Expected a report when Anthropic metadata from **args has no user_id",
        )



if __name__ == "__main__":
    unittest.main()
