# NSM — No System Message

## Name & Intent

**No System Message (NSM)**

Intent: avoid initiating an LLM chat without a system role instruction. The system message sets global behavior, constraints, and tone for the assistant across the conversation.

## Context

Role-based chat APIs model dialogue as a sequence of role-tagged messages. The system message is the canonical place to define the assistant role, scope, and constraints that apply to all turns.

## Problem

Without a system message, the model lacks high-level guidance. Outputs become more generic and less consistent, and adherence to constraints weakens. This reduces reliability and usually requires longer user prompts or extra iterations to achieve acceptable results.

## Solution

Always include a clear system message that defines role, goals, and constraints. Keep task specifics in the user message.

## Effect on Software Quality

### Maintainability (M)
- Centralizes global rules
- Easier versioning and testing

### Reliability (R)
- More consistent outputs
- Better adherence to format and constraints

## Minimal Example (bad -> good)

```python
# BAD — no system message
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=[
        {"role": "user", "content": "Explain recursion with an example."}
    ]
)
text = resp.choices[0].message.content

# GOOD — add a concise system message
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=[
        {"role": "system", "content": "You are a Computer Science tutor. Answer clearly."},
        {"role": "user", "content": "Explain recursion with an example."}
    ]
)
text = resp.choices[0].message.content
```

## Additional Examples

Anthropic

```python
import anthropic

client = anthropic.Anthropic()

# BAD — no system message
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Explain recursion."}]
)

# GOOD — system message anchors behavior
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    system="You are a Computer Science tutor. Answer clearly.",
    messages=[{"role": "user", "content": "Explain recursion."}]
)
```

Gemini

```python
import google.generativeai as genai

# BAD — no system instruction
model = genai.GenerativeModel("gemini-1.5-pro")
resp = model.generate_content("Explain recursion.")

# GOOD — set system instruction
model = genai.GenerativeModel(
    "gemini-1.5-pro",
    system_instruction="You are a Computer Science tutor. Answer clearly."
)
resp = model.generate_content("Explain recursion.")
```

### Sources

***Papers***

- Minbyul Jeong, Jungho Cho, Minsoo Khang, Dawoon Jung, and Teakgyu Hong. 2025. System Message Generation for User Preferences using Open-Source Models. arXiv. https://arxiv.org/abs/2502.11330

- Anna Neumann, Elisabeth Kirsten, Muhammad Bilal Zafar, and Jatinder Singh. 2025. Position is Power: System Prompts as a Mechanism of Bias in Large Language Models (LLMs). In Proceedings of the 2025 ACM Conference on Fairness, Accountability, and Transparency (FAccT ’25). ACM, 573–598. doi:10.1145/3715275.3732038

***Official Documentation***

- [OpenAI — Prompt engineering (roles, instructions)](https://platform.openai.com/docs/guides/prompt-engineering)

- [NVIDIA NeMo — system_message parameter (reference API)](https://docs.nvidia.com/nemo/microservices/25.9.0/pysdk/types/shared/chat_completion_system_message_param.html)

- [Hugging Face Transformers — Chat templating & system tokens]( https://huggingface.co/docs/transformers/en/chat_templating)

***Engineering Blogs***
- [PromptHub — System Messages: Best Practices, Real-world Experiments & Prompt Injection Protectors (2025)]( https://www.prompthub.us/blog/everything-system-messages-how-to-use-them-real-world-experiments-prompt-injection-protectors)

- [Stack Overflow — What is the use case of System role](https://stackoverflow.com/questions/76272624/what-is-the-use-case-of-system-role)

