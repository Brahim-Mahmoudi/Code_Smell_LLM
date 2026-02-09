# TNES — LLM Temperature Not Explicitly Set

## Name & Intent

**LLM Temperature Not Explicitly Set (TNES)**

Intent: avoid relying on provider or model defaults for temperature. Temperature controls sampling randomness, and leaving it implicit harms reproducibility, portability, and consistency because defaults vary and can change over time.

## Context

LLM APIs expose temperature alongside other sampling controls such as top_p and top_k. These parameters are core to decoding behavior and must be treated as explicit configuration.

## Problem

Implicit temperature reduces maintainability and reliability. Defaults differ across providers and models and may change over time, silently altering behavior.

## Solution

Always specify temperature explicitly and document the choice. Use low values (about 0.0 to 0.3) for precise, repeatable automation and higher values (about 0.7 to 1.0) for creative generation. Avoid extremes. If top_p or top_k is explicitly set, do not also set temperature to avoid overspecification.

## Effect on Software Quality

### Maintainability (M)
- Configuration is explicit and versionable
- Reduced drift across environments

### Reliability (R)
- Consistent behavior over time and runs
- Fewer surprises from default changes

## Minimal Example (bad -> good)

```python
# BAD — temperature omitted
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=messages
)

# GOOD — temperature explicit
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=messages,
    temperature=1.0
)
```

## Additional Examples

Anthropic

```python
import anthropic

client = anthropic.Anthropic()

# BAD — temperature omitted
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Write a short story."}]
)

# GOOD — temperature explicit
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Write a short story."}],
    temperature=0.9
)
```

Gemini

```python
import google.generativeai as genai

model = genai.GenerativeModel("gemini-1.5-pro")

# BAD — temperature omitted
resp = model.generate_content("Write a short story.")

# GOOD — temperature explicit
resp = model.generate_content(
    "Write a short story.",
    generation_config=genai.GenerationConfig(temperature=0.9)
)
```

### Sources

***Papers***


- Montandon, R., et al. (2024). Default parameters can change over time (on instability from shifting defaults). arXiv:2408.05129. https://arxiv.org/pdf/2408.05129

- OpenReview (2020). On high temperatures and incoherence in language generation. https://openreview.net/forum?id=FBkpCyujtS (PDF: https://openreview.net/pdf?id=FBkpCyujtS)



***Official Documentation***

- [OpenAI — Chat Completions API (temperature parameter)](https://platform.openai.com/docs/api-reference/chat/create)

- [Anthropic/Claude — Messages API (temperature)](https://docs.claude.com/en/api/messages)

- [Google — Gemini API (temperature)](https://ai.google.dev/api/generate-content?hl=en)

- [Ollama — Modelfile defaults (temperature)](https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values)

- [xAI — API reference (chat completions, temperature)](https://docs.x.ai/docs/api-reference#chat-completions)

- [Hugging Face Transformers — Generation config (temperature)](https://huggingface.co/docs/transformers/main_classes/text_generation)


***Engineering Blogs***
- [Vellum — LLM Temperature: How It Works and When You Should Use It](https://www.vellum.ai/llm-parameters/temperature)

- [IBM Think — LLM temperature definition and task guidance](https://www.ibm.com/think/topics/llm-temperature)


***Grey Literature***

- [vllm-project. MCP-USE with VLLM gpt-oss:20b via ChatOpenAI [Issue #26806]. In vllm (GitHub repository). GitHub](https://github.com/vllm-project/vllm/issues/26806)

- [langfuse. Bug — When streaming responses with the OpenAI Responses API, temperature is not captured correctly [Issue #9566] In langfuse (GitHub repository). GitHub.](https://github.com/langfuse/langfuse/issues/9566)