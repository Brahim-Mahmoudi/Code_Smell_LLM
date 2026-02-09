# OSP — Overspecified Sampling Parameters

## Name & Intent

**Overspecified Sampling Parameters (OSP)**

Intent: avoid setting multiple sampling controls (temperature, top_p, top_k) in the same call. These controls are not independent, and combining them makes decoding behavior harder to predict and reproduce.

## Context

Modern LLM APIs expose several parameters that shape randomness. Their exact semantics and supported combinations vary across providers and model families.

## Problem

OSP occurs when multiple randomness controls are pinned at once. This overspecification makes the effective decoding policy hard to reason about and harder to reproduce across providers, which reduces maintainability and portability.

## Solution

Pick a single primary control for randomness and document the choice. If temperature is used, set it explicitly. If top_p or top_k is used, keep temperature unset. Validate changes with small regression suites when updating models or providers.

## Effect on Software Quality

### Maintainability (M)
- Simpler, explainable sampling configuration

### Reliability (R)
- More stable generation behavior across environments

## Minimal Example (bad -> good)

```python
import anthropic

client = anthropic.Anthropic()

# BAD — multiple sampling controls
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Write a sci-fi story about Mars."}
    ],
    temperature=0.9,
    top_p=0.95
)

# GOOD — single primary control
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Write a sci-fi story about Mars."}
    ],
    temperature=0.9
)
```

## Additional Examples

Gemini

```python
import google.generativeai as genai

model = genai.GenerativeModel("gemini-1.5-pro")

# BAD — multiple sampling controls
resp = model.generate_content(
    "Write a creative story.",
    generation_config=genai.GenerationConfig(
        temperature=0.9,
        top_p=0.95
    )
)

# GOOD — single primary control
resp = model.generate_content(
    "Write a creative story.",
    generation_config=genai.GenerationConfig(temperature=0.9)
)
```

### Sources

***Papers***

None in our evidence base for OSP.

***Official Documentation***

- [Microsoft, Azure OpenAI REST API (temperature, top_p)](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/latest?view=foundry-classic)
- [Anthropic, Create a Text Completion (API reference)](https://docs.anthropic.com/claude/reference/complete_post)
- [OpenAI Developer Community, Clarifications on setting temperature = 0](https://community.openai.com/t/clarifications-on-setting-temperature-0/886447)

***Engineering Blogs***

- [Simon Willison, llm-anthropic](https://pypi.org/project/llm-anthropic/)
- [Medium, Setting Top-K, Top-P and Temperature in LLMs](https://rumn.medium.com/setting-top-k-top-p-and-temperature-in-llms-3da3a8f74832)
- [Novita AI, What Are Large Language Model Settings: Temperature, Top P And Max Tokens](https://medium.com/@marketing_novita.ai/what-are-large-language-model-settings-temperature-top-p-and-max-tokens-a482d8d817b2)
- [Malhar, Understanding LLM Settings for Optimal Performance](https://medium.com/@justmalhar/understanding-llm-settings-for-optimal-performance-83ee29c50392)
- [Prompt Engineering Institute, Complete Guide to Prompt Engineering with Temperature and Top-p](https://promptengineering.org/prompt-engineering-with-temperature-and-top-p/)

***Grey Literature***

- [n8n.io. AI Agent with Anthropic models fails temperature and top_p cannot both be specified for this model [Issue #18304]. In n8n (GitHub repository). GitHub.](https://github.com/n8n-io/n8n/issues/18304)
- [intel. default values of max_generated_tokens, top_k, top_p, and temperature? [Issue #11033]. In ipex-llm (GitHub repository). GitHub.](https://github.com/intel/ipex-llm/issues/11033)
- [Hugging Face. The document of generation seems to wrongly describe the default value of top_p, top_k and temperature [Issue #35045]. In transformers (GitHub repository). GitHub.](https://github.com/huggingface/transformers/issues/35045)
- [RepoWise. Ensure Deterministic and Fully Consistent LLM Output [Issue #11]. In backend (GitHub repository). GitHub.](https://github.com/RepoWise/backend/issues/11)
- [mpfaffenberger. Add Recommended Sampling Parameters for GLM Model [Issue #70]. In code_puppy (GitHub repository). GitHub.](https://github.com/mpfaffenberger/code_puppy/issues/70)
- [haktancetin. LLM Randomness [Issue #24]. In 496_CookBuddyProject (GitHub repository). GitHub.](https://github.com/haktancetin/496_CookBuddyProject/issues/24)
