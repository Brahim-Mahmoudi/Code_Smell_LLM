# NSM — No System Message

## Name & Intent

**No System Message (NSM)**

Intent: avoid initiating an LLM chat without a system-role instruction. The system message encodes global controller hints—role, objectives, scope, safety/format constraints—that shape all subsequent turns. Omitting it discards a primary lever for behavioral steering, making responses less consistent and harder to constrain across a conversation. In our empirical study, NSM appears in 34.50% (69/200) of systems.

## Context

Modern chat LLM interfaces (OpenAI, Azure OpenAI, Anthropic, etc.) model dialogue as a sequence of role-tagged messages: system (global guidance), user (task/query), and assistant (model replies). The system message is the canonical place to set persona, domain scope, tone, format contracts, and guardrails. When teams skip this message—often in prototypes, quick demos, or legacy migrations—they effectively start from an under-specified prior, relying on ad-hoc user prompts or post-hoc filtering to coerce behavior.

## Problem

Without a system message, the assistant receives no up-front, global constraints, creating multiple failure modes:

- Ungrounded behavior & drift across turns
- Lower specificity & relevance 
- Weaker constraint adherence
- Heavier prompt payloads
- Harder reproducibility
- Tighter coupling downstream
- Reduced controllability in agent loops

## Solution

### General Guidelines
1. Establish a standardized system message as the first message in every conversation:
   - Define role & scope
   - Specify global constraints
   - Separate concerns
   - Version & test
   - Provide fallbacks
   - Implement governance

### OpenAI Implementation
- Always include a first message with `{"role": "system", "content": "..."}`.
- Keep global rules concise and stable
- Consider combining with `response_format` for shape guarantees
- Pin model versions and maintain tests

## Effect on Software Quality

### Maintainability (M)
- Centralizes global rules
- Facilitates versioning and testing
- Eases refactoring

### Reliability (R)
- Improves consistency
- Reduces format/style violations
- Lowers variance in agent pipelines

## Minimal Example (bad → good)

````python
# BAD — No system message (smell)
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=[
        {"role": "user", "content": "Explain recursion with a simple example."}
    ]
)
text = resp.choices[0].message.content

# GOOD — Add a concise system message to set role/constraints
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a Computer Science tutor. "
                "Explain concepts step by step, avoid jargon, and include a short code example."
            )
        },
        {"role": "user", "content": "Explain recursion with a simple example."}
    ]
)
text = resp.choices[0].message.content

# OPTIONAL — Combine with structured outputs
from openai import OpenAI
import json
client = OpenAI()

schema = {
    "type": "object",
    "required": ["explanation", "code_snippet"],
    "properties": {
        "explanation": {"type": "string", "minLength": 20},
        "code_snippet": {"type": "string"}
    },
    "additionalProperties": False
}

resp = client.chat.completions.create(
    model="gpt-4o-2024-11-20",
    messages=[
        {"role": "system",
         "content": "You are a CS tutor. Respond in JSON with keys: explanation, code_snippet."},
        {"role": "user", "content": "Explain recursion with a simple example."}
    ],
    response_format={"type": "json_schema",
                     "json_schema": {"name": "TutorReply", "schema": schema}}
)
data = json.loads(resp.choices[0].message.content)
````

### Sources

***Papers***


- Qin, Y., Zhang, T., Shen, Y., Luo, W., Sun, H., Zhang, Y., Qiao, Y., Chen, W., Zhou, Z., Zhang, W., & Cui, B. (2024). SysBench: Can Large Language Models Follow System Messages? arXiv. https://doi.org/10.48550/arXiv.2408.10943

- Ronanki, K., Cabrero-Daniel, B., & Berger, C. (2024). Prompt Smells: An Omen for Undesirable Generative AI Outputs. arXiv. https://doi.org/10.48550/arXiv.2401.12611

***Official Documentation***

- [OpenAI — Prompt engineering (roles, instructions)](https://platform.openai.com/docs/guides/prompt-engineering)

- [NVIDIA NeMo — system_message parameter (reference API)](https://docs.nvidia.com/nemo/microservices/25.9.0/pysdk/types/shared/chat_completion_system_message_param.html)

- [Hugging Face Transformers — Chat templating & system tokens]( https://huggingface.co/docs/transformers/en/chat_templating)

***Engineering Blogs***
- [PromptHub — System Messages: Best Practices, Real-world Experiments & Prompt Injection Protectors (2025)]( https://www.prompthub.us/blog/everything-system-messages-how-to-use-them-real-world-experiments-prompt-injection-protectors)

- [PromptHub — The Difference Between System Messages and User Messages (2024–2025)]( https://www.prompthub.us/blog/the-difference-between-system-messages-and-user-messages-in-prompt-engineering)
