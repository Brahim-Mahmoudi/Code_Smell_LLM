# NSO — No Structured Output

## Name & Intent

**No Structured Output (NSO)**

Intent: avoid consuming free-form LLM text where structured fields (for example JSON) are required. Enforce and validate a schema at the boundary before parsing, indexing, executing, or storing the output.

## Context

LLM-integrating systems often expect typed fields but rely on free-form inference output. This smell applies when the output is later parsed, indexed, or executed as if it were structured.

## Problem

Without an enforced output schema, the system may receive free-form text where structured fields are expected. This leads to schema drift, missing or renamed fields, type mismatches, and silent truncation that passes as success. Downstream parsers and storage paths then fail or accept corrupted data, degrading reliability.

## Solution

Enforce structured output at the API boundary. With OpenAI, declare a JSON Schema via `response_format` and validate the response before use. Always handle refusals or schema violations explicitly.

## Effect on Software Quality

### Robustness (RO)
- Schema drift and type mismatches
- Truncation that passes as success

### Reliability (R)
- Inconsistent runs and corrupted stored data
- Injection risk in downstream execution and storage paths

## Minimal Example (bad -> good)

```python
# BAD — free-form output; brittle parsing
from openai import OpenAI
client = OpenAI()

messages = [{"role": "user", "content": "Return user profile"}]

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=messages
)
text = resp.choices[0].message.content
# Downstream code assumes JSON and may crash or misparse.

# GOOD — enforce JSON Schema and validate at the boundary
from openai import OpenAI
import json, jsonschema

client = OpenAI()

user_schema = {
    "type": "object",
    "required": ["id", "name", "email"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "email": {"type": "string"}
    },
    "additionalProperties": False
}

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=messages,
    response_format={
        "type": "json_schema",
        "json_schema": {"name": "UserRecord", "schema": user_schema}
    }
)

data = json.loads(resp.choices[0].message.content)
jsonschema.validate(instance=data, schema=user_schema)
```

## Additional Examples

Anthropic (tool schema for structured output)

```python
import anthropic

client = anthropic.Anthropic()

profile_schema = {
    "type": "object",
    "required": ["id", "name", "email"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "email": {"type": "string"}
    },
    "additionalProperties": False
}

# BAD — free-form text only
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Return user profile"}]
)

# GOOD — enforce a structured tool schema
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Return user profile"}],
    tools=[{
        "name": "emit_profile",
        "description": "Return a user profile",
        "input_schema": profile_schema
    }],
    tool_choice={"type": "tool", "name": "emit_profile"}
)
```

Gemini (JSON response + validation)

```python
import json, jsonschema
import google.generativeai as genai

model = genai.GenerativeModel("gemini-1.5-pro")

profile_schema = {
    "type": "object",
    "required": ["id", "name", "email"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "email": {"type": "string"}
    },
    "additionalProperties": False
}

# BAD — plain text without schema control
resp = model.generate_content("Return user profile")

# GOOD — request JSON and validate
resp = model.generate_content(
    "Return user profile as JSON with id, name, email",
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json"
    )
)

data = json.loads(resp.text)
jsonschema.validate(instance=data, schema=profile_schema)
```

### Sources

***Papers***

- Michael Xieyang Liu, Frederick Liu, Alexander J. Fiannaca, Terry Koo, Lucas Dixon, Michael Terry, and Carrie J. Cai. 2024. "We Need Structured Output":Towards User-centered Constraints on Large Language Model Output. In Extended Abstracts of the CHI Conference on Human Factors in Computing Systems (Honolulu, HI, USA) (CHI EA ’24). Association for Computing Machinery, New York, NY, USA, Article 10, 9 pages. doi:10.1145/3613905.3650756

***Official Documentation***

- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs)
- [Dev.to (Pydantic)](https://dev.to/devasservice/a-practical-guide-on-structuring-llm-outputs-with-pydantic-50b4)
- [Kharitonov (TDS/Medium)](https://medium.com/data-science/enforcing-json-outputs-in-commercial-llms-3db590b9b3c8)

***Engineering Blogs***
- [Kharitonov, Enforcing JSON Outputs in Commercial LLMs](https://medium.com/data-science/enforcing-json-outputs-in-commercial-llms-3db590b9b3c8)
- [Dev.to, Structuring LLM Outputs with Pydantic](https://dev.to/devasservice/a-practical-guide-on-structuring-llm-outputs-with-pydantic-50b4)
- [Okareo, Validate the Output of LLM-Based Products](https://okareo.com/blog/posts/validate-llm-output)
- [Modelmetry, Ensure LLM Output Adheres to a JSON Schema](https://modelmetry.com/blog/how-to-ensure-llm-output-adheres-to-a-json-schema)

***Grey Literature***

- [dgy516. test(functional) — streaming JSON missing required; completions logprobs structure [Pull request #60]. In vllm_cibench (GitHub repository). GitHub.]( https://github.com/dgy516/vllm_cibench/pull/60)

- [vllm-project. Structured output is not correctly enforced when using GPT-OSS [Issue #23120]. In vllm (GitHub repository). GitHub. ](https://github.com/vllm-project/vllm/issues/23120)

- [Microsoft. Python — OpenAI Responses client structured output does not work with streaming responses [Issue #238]. In agent-framework (GitHub repository). GitHub.]( https://github.com/microsoft/agent-framework/issues/238)

- [BerriAI. Responses — add structured output for SDK [Pull request #14206]. In litellm (GitHub repository). GitHub.](https://github.com/BerriAI/litellm/pull/14206)

