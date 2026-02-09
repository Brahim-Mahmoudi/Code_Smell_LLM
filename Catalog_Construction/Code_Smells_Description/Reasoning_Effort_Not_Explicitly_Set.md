# RENES — Reasoning Effort Not Explicitly Set

## Name & Intent

**Reasoning Effort Not Explicitly Set (RENES)**

Intent: avoid calling reasoning-capable models without explicitly configuring their reasoning control (for example reasoning effort or depth). These controls affect accuracy, latency, and cost, and defaults can change across models or over time.

## Context

Reasoning-capable models expose controls for how much internal reasoning they perform before emitting tokens. Providers implement this as a parameter like reasoning effort, reasoning depth, or a reasoning budget. Defaults are model-specific and may evolve.

## Problem

When reasoning control is left implicit, behavior depends on provider defaults that differ across models and can change without code changes. This harms reproducibility and maintainability, and can silently change latency and cost.

## Solution

Treat reasoning control as part of the public contract for any reasoning-capable call. Always set it explicitly and document the choice. Use lower effort for interactive or high-throughput scenarios and higher effort for complex or high-risk tasks.

## Effect on Software Quality

### Maintainability (M)
- Explicit configuration improves traceability
- Fewer hidden behavior changes when models evolve

### Reliability (R)
- More consistent accuracy across deployments
- Predictable behavior under model upgrades

### Performance (P)
- Controlled latency and cost

## Minimal Example (bad -> good)

```python
# BAD — reasoning effort omitted
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[
        {"role": "system", "content": "You are a careful assistant."},
        {"role": "user", "content": "Explain the main tradeoffs for safety-critical code review."}
    ],
    temperature=0.2
)

# GOOD — reasoning effort set explicitly
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[
        {"role": "system", "content": "You are a careful assistant."},
        {"role": "user", "content": "Explain the main tradeoffs for safety-critical code review."}
    ],
    temperature=0.2,
    reasoning={"effort": "minimal"}
)
```

## Additional Examples

Anthropic (thinking budget)

```python
import anthropic

client = anthropic.Anthropic()

# BAD — thinking enabled without explicit budget
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=512,
    thinking={"type": "enabled"},
    messages=[{"role": "user", "content": "Analyze the tradeoffs in this design."}]
)

# GOOD — explicit thinking budget
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=512,
    thinking={"type": "enabled", "budget_tokens": 3000},
    messages=[{"role": "user", "content": "Analyze the tradeoffs in this design."}]
)
```

### Sources

***Papers***
- Author, F., Author, S., Author, T. (2025). Themes of building LLM-based applications for production: A practitioner's view. In: Proceedings of the 2025 IEEE/ACM 4th International Conference on AI Engineering (CAIN). IEEE, Ottawa, Canada.
- Wen, H., Wu, X., Sun, Y., Zhang, F., Chen, L., Wang, J., Liu, Y., Liu, Y., Zhang, Y., Li, Y. (2025). BudgetThinker: Empowering budget-aware LLM reasoning with control tokens. https://doi.org/10.48550/arXiv.2508.17196
- Wang, J., Jain, S., Zhang, D., Ray, B., Kumar, V., Athiwaratkun, B. (2024). Reasoning in token economies: Budget-aware evaluation of LLM reasoning strategies. https://doi.org/10.18653/v1/2024.emnlp-main.1112
- Chen, Z., Ye, Y., Zhou, Z. (2025). Adaptively robust LLM inference optimization under prediction uncertainty.
- Han, T., Wang, Z., Fang, C., Zhao, S., Ma, S., Chen, Z. (2025). Token-budget-aware LLM reasoning. https://doi.org/10.18653/v1/2025.findings-acl

***Official Documentation***
- [OpenAI — Reasoning guide](https://platform.openai.com/docs/guides/reasoning)
- [OpenAI — Models overview](https://platform.openai.com/docs/models)
- [Anthropic — Extended thinking in the Messages API](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)
- [Google AI for Developers — Gemini thinking parameters and OpenAI compatibility](https://ai.google.dev/gemini-api/docs/thinking)

***Engineering Blogs***
- [latent.space — Notes on OpenAI o1 and reasoning controls](https://www.latent.space/p/o1)
- [Simon Willison — o1 and reasoning effort in practice](https://simonwillison.net/2024/Sep/12/openai-o1/)

***Grey Literature***
- OpenInterpreter. Add reasoning effort parameter support (Issue #1742). In open-interpreter (GitHub repository). GitHub. https://github.com/OpenInterpreter/open-interpreter/issues/1742
- LibreChat. Add reasoning_effort support for o1 models (Issue #6083). In LibreChat (GitHub repository). GitHub. https://github.com/danny-avila/LibreChat/issues/6083

