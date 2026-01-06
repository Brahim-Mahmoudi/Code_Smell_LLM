# AIC Anonymous Inference Call

## Name & Intent

**Anonymous Inference Call (AIC)**.

***Intent***: prevent untraceable LLM requests in multi user or multi tenant systems by attaching a stable end user identifier or equivalent attribution metadata to each inference call, then propagating it through logs, monitoring, and cost accounting.

***Context***

AIC arises when an application generates LLM outputs on behalf of end users but the inference call is emitted without any end user identifier at the provider boundary and without equivalent attribution in telemetry. Many providers expose optional fields intended to support abuse monitoring, auditing, and operational attribution. When these fields are omitted, the system loses an essential link between a generated output and the user context that triggered it.

***Problem***

Without end user attribution at the boundary, the system cannot reliably answer who triggered a given output, which tenant is affected, or which session produced anomalous behaviour. This weakens incident response, makes debugging user specific issues harder, and complicates governance workflows such as abuse monitoring, safety audits, and compliance investigations. Operationally, it also obscures cost attribution and rate limit enforcement because usage collapses to aggregate signals rather than user scoped signals.

***Solution***

Attach a stable pseudonymized identifier for each end user or session to every inference call in multi user contexts. Ensure the attribution is consistently propagated across wrappers, background jobs, retries, and provider specific SDK layers. Log the attribution alongside request identifiers to support traceability while avoiding direct personal data.

***OpenAI Implementation***

Use the provider supported attribution field for the endpoint you call. In OpenAI APIs this can be a legacy `user` field or a newer `safety_identifier` depending on the surface you use. Prefer a stable pseudonymized value that does not contain raw PII.

***Anthropic Implementation***

Use request metadata such as `metadata.user_id` when creating messages and ensure it is stable across sessions or mapped from your internal user identity.

***Azure OpenAI Implementation***

Use the `user` field where supported to pass a unique end user identifier for abuse monitoring and operational attribution.

## Effect on Software Quality

### Robustness (RO)

AIC increases error proneness during debugging and incident response because user specific prompt histories, tool invocations, tenancy configuration, and authentication context cannot be reconstructed reliably from provider side traces or internal logs.

### Reliability (R)

AIC reduces operational reliability by weakening safety monitoring, anomaly triage, and governance. Abuse detection and rate limiting become less targeted, and cost spikes become harder to attribute. In multi tenant systems, missing attribution increases the chance that harmful or noisy usage patterns remain undetected until they affect overall service quality.

## Minimal Example (bad -> good)

```python
# BAD  Multi user call without end user attribution
from openai import OpenAI
client = OpenAI()

def get_response(user_session_id: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        # Missing attribution field
    )
    return resp.choices[0].message.content


# GOOD  Attach stable pseudonymized attribution and log it
import hashlib
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

def pseudonymize(user_session_id: str) -> str:
    return hashlib.sha256(user_session_id.encode("utf-8")).hexdigest()[:16]

def get_response(user_session_id: str, prompt: str) -> str:
    attribution_id = pseudonymize(user_session_id)

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        safety_identifier=attribution_id,
    )

    logger.info(
        "llm_inference",
        extra={
            "safety_identifier": attribution_id,
            "model": "gpt-4o",
            "request_id": getattr(resp, "id", None),
        },
    )
    return resp.choices[0].message.content
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
