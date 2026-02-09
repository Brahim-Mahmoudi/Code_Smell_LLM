# AIC — Anonymous Inference Call

## Name & Intent

**Anonymous Inference Call (AIC)**

Intent: avoid issuing LLM requests without a stable user or session identifier in multi-user systems. The identifier enables traceability, auditing, abuse monitoring, and per-user governance.

## Context

Many providers allow attaching optional request metadata (for example a user or session identifier). In multi-user applications, this metadata links each inference to the originating user or session and supports accountable logging and abuse monitoring.

## Problem

When inference calls are anonymous, incidents, cost spikes, and misuse cannot be attributed to a specific user or session. This weakens debugging, auditing, and policy enforcement and reduces reliability in multi-tenant systems.

## Solution

Propagate a stable, pseudonymous user identifier from the application boundary to every LLM request. Keep the mapping in application storage and log it with model and request metadata for traceability.

## Effect on Software Quality

### Maintainability (M)
- Harder incident analysis and post-mortems
- Weaker operational traceability

### Reliability (R)
- Reduced accountability and monitoring
- Harder per-user throttling and abuse detection

## Minimal Example (bad -> good)

```python
# BAD — multi-user call without user attribution
from openai import OpenAI
client = OpenAI()

def get_response(user_session_id: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
        # Missing user identifier
    )
    return resp.choices[0].message.content

# GOOD — attach a stable user identifier for traceability
from openai import OpenAI
client = OpenAI()

def get_response(user_session_id: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        user=user_session_id
    )
    return resp.choices[0].message.content
```

## Additional Examples

Anthropic (bad -> good)

```python
import anthropic

client = anthropic.Anthropic()

# BAD — missing user attribution
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Summarize this document."}]
)

# GOOD — attach a stable user identifier
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Summarize this document."}],
    metadata={"user_id": user_session_id}
)
```

### Sources

***Papers***

None in our evidence base for AIC.

***Official Documentation***

- [OpenAI, Safety best practices](https://platform.openai.com/docs/guides/safety-best-practices)
- [Google DeepMind, Gemini API Safety guidance](https://ai.google.dev/gemini-api/docs/safety-guidance)
- [Anthropic, Create a Message (Python)](https://platform.claude.com/docs/en/api/python/messages/create)

***Engineering Blogs***

- [Anthropic, Detecting and Countering Malicious Uses of Claude](https://www.anthropic.com/news/detecting-and-countering-malicious-uses-of-claude-march-2025)
- [Nerd For Tech, Safeguarding Your AI: Best Practices for Securing Your OpenAI API](https://medium.com/nerd-for-tech/safeguarding-your-ai-best-practices-for-securing-your-openai-api-key-67e5e585c59a)
- [Prompt Engineering Institute, Complete Guide to Prompt Engineering with Temperature and Top-p](https://promptengineering.org/prompt-engineering-with-temperature-and-top-p/)

***Grey Literature***

- [raz-alon and contributors. [Bug]: Anthropic API throws Bad Request when user_id in metadata contains email or phone number [Issue #10106]. In litellm (GitHub repository). GitHub.](https://github.com/BerriAI/litellm/issues/10106)
- [OpenAI. Need Help: Facing OpenAI Usage Violation Due to user's Abuse - API. OpenAI Developer Community.](https://community.openai.com/t/need-help-facing-openai-usage-violation-due-to-users-abuse/1004947)
- [OpenAI Developer Community. API ban from user abuse - API.](https://community.openai.com/t/api-ban-from-user-abuse/25400)
- [OpenAI Community. Any suggestions for Preventing openai API abuse - API.](https://community.openai.com/t/any-suggestions-for-preventing-openai-api-abuse/1075315)
- [OpenAI. Lessons learned on language model safety and misuse.](https://openai.com/index/language-model-safety-and-misuse/)
- [OpenAI. API Policy Violation Warning - advice on how to best resolve. OpenAI Developer Community.](https://community.openai.com/t/api-policy-violation-warning-advice-on-how-to-best-resolve/788354)
