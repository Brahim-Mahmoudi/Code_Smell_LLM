# NMVP — No Model Version Pinning

## Name & Intent

**No Model Version Pinning (NMVP)**

Intent: avoid reproducibility and audit gaps that arise when calling an LLM by a moving alias (for example `gpt-4o`) rather than an immutable version or snapshot (for example `gpt-4o-2024-11-20`). Pinning the exact model version stabilizes behavior across time and enables traceability.

## Context

Providers expose moving aliases and immutable versions. Aliases can advance as providers update weights, prompts, or safety filters. When aliases propagate into production, behavior can drift silently.

## Problem

Using aliases removes explicit versioning. Weights and safety layers can change without notice and shift behavior, reducing maintainability, traceability, and reproducibility.

## Solution

Always specify an immutable model identifier and record it with run metadata. Update versions through change control instead of relying on moving aliases.

## Effect on Software Quality

### Maintainability (M)
- Traceability and auditability
- Controlled upgrades

### Reliability (R)
- Stable behavior across time and environments
- Reproducible evaluations

## Minimal Example (bad -> good)

```python
# BAD — using a moving alias
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)

# GOOD — pin an immutable version
from openai import OpenAI
client = OpenAI()

MODEL_ID = "gpt-4o-2024-11-20"
resp = client.chat.completions.create(
    model=MODEL_ID,
    messages=messages
)
```

## Additional Examples

Anthropic

```python
import anthropic

client = anthropic.Anthropic()

# BAD — moving alias
message = client.messages.create(
    model="claude-3-5-sonnet",
    max_tokens=256,
    messages=[{"role": "user", "content": "Summarize this."}]
)

# GOOD — pinned version
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Summarize this."}]
)
```

Gemini

```python
import google.generativeai as genai

# BAD — moving alias
model = genai.GenerativeModel("gemini-1.5-pro")
resp = model.generate_content("Summarize this.")

# GOOD — pinned version
model = genai.GenerativeModel("gemini-1.5-pro-002")
resp = model.generate_content("Summarize this.")
```

### Sources

***Papers***


- Wilson, G., Aruliah, D. A., Brown, C. T., et al. (2014). Best Practices for Scientific Computing. PLoS Biology. https://pmc.ncbi.nlm.nih.gov/articles/PMC3886731/

- Morishige, M., & Koshihara, R. (2025). Ensuring Reproducibility in Generative AI Systems for General Use Cases: A Framework for Regression Testing and Open Datasets. doi:10.48550/arXiv.2505.02854

- Albertoni, R., Colantonio, S., Skrzypczyński, P., & Stefanowski, J. (2023). Reproducibility of Machine Learning: Terminology, Recommendations and Open Issues. arXiv. https://arxiv.org/abs/2302.12691

- Reyes, F., Gamage, Y., Skoglund, G., Baudry, B., & Monperrus, M. (2024). BUMP: A Benchmark of Reproducible Breaking Dependency Updates. arXiv / SANER 2024. https://arxiv.org/abs/2401.09906

- Venturini, D., Cogo, FR., Polato, I., Gerosa, MA., and Wiese, IS. (2023). I Depended on You and You Broke Me: An Empirical Study of Manifesting Breaking Changes in Client Packages. arXiv:2301.04563 doi:10.48550/arXiv.2301.04563 TOSEM, 2023.

***Official Documentation***

- [Microsoft Learn — Manage foundation model lifecycle (governance & versioning)](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/manage-foundation-models-lifecycle)

- [Hugging Face Transformers — from_pretrained(..., revision=...)](https://huggingface.co/docs/transformers/main_classes/model#transformers.PreTrainedModel.from_pretrained.revision)

- [OpenAI — Model pages and release notes (model availability & changes)](https://platform.openai.com/docs/models/gpt-4o)

- [OpenAI — Model pages and release notes (model availability & changes)](https://help.openai.com/en/articles/9624314-model-release-notes)

- [xAI — Models overview](https://docs.x.ai/docs/overview)

- [Google AI — Gemini docs](https://ai.google.dev/)

- [Anthropic — Claude models overview](https://docs.claude.com/en/docs/about-claude/models/overview#model-comparison-table)

- [Ollama — Local model tags](https://ollama.com/)

- [OpenRouter — Multi-provider routing](https://openrouter.ai/)

***Engineering Blogs***
- [Hugging Face — Model Hub (commit snapshots)](https://huggingface.co/)

- [LangChain — Ollama integration (pinning tags in local runtimes)](https://python.langchain.com/docs/integrations/chat/ollama/)

