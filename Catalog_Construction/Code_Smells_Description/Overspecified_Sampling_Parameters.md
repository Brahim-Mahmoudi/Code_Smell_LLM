
# Code Smell: Overspecified Sampling Parameters (OSP)

## Definition

The Overspecified Sampling Parameters (OSP) code smell occurs when multiple sampling controls are specified simultaneously in a call to an LLM. These parameters (`temperature`, `top_p`, `top_k`) are not independent — they each modify or constrain the distribution of next-token probabilities — which can make the final decoding behavior hard to predict and difficult to reproduce.

## Motivation

Modern LLM runtimes expose several sampling controls that influence decoding stochasticity:
- **temperature**: controls overall randomness
- **top_p** (nucleus sampling): restricts to tokens whose cumulative probability reaches p
- **top_k**: limits to the k most probable tokens

Problems arise when these controls are combined because:
- Exact semantics differ across providers
- The application order is not always clear
- Which parameter becomes dominant can change without warning
- Reproducibility across providers can become impossible

## Impact

- **Reduced maintainability**: behavior becomes harder to understand and document
- **Compromised portability**: different providers may return different results
- **Harder debugging**: effects of individual parameters are difficult to isolate
- **Silent regressions**: quality changes without clear explanation

## Examples

### ❌ Bad practices
```python
# Multiple sampling controls in a single call
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a story"}],
    temperature=0.9,
    top_p=0.95,
    top_k=50  # Overspecification!
)

# OpenAI-style call with multiple controls
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Write a story"}],
    temperature=0.8,
    top_p=0.9  # Overspecification!
)

# Wrapper configuration with overspecification
llm = ChatAnthropic(
    model="claude-3-opus-20240229",
    temperature=1.0,
    top_p=0.95,  # Overspecification!
    top_k=40
)

# Overspecification via context manager
with client.with_options(temperature=0.9, top_p=0.95):
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": "Generate content"}]
    )

# Split between context and call site
def generate_text():
    with client.with_options(temperature=0.8):
        return client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": "Write"}],
            top_p=0.9  # Overspecification!
        )
```

### ✅ Good practices
```python
# Single control: temperature only
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a creative story"}],
    temperature=0.9
)

# Single control: top_p only
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Produce diverse outputs"}],
    top_p=0.95
)

# Centralized sampling configuration
SAMPLING_CONFIGS = {
    "creative": {"temperature": 0.9},
    "balanced": {"temperature": 0.7},
    "factual": {"temperature": 0.3},
    "deterministic": {"temperature": 0.0},
    "diverse": {"top_p": 0.95},
    "focused": {"top_p": 0.5}
}

def generate_with_config(prompt, config_name="balanced"):
    config = SAMPLING_CONFIGS[config_name]
    return client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": prompt}],
        **config
    )

# Context manager with a single control
with client.with_options(temperature=0.8):
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": "Generate"}]
    )
```

## Task-specific sampling guide
```python
TASK_SAMPLING = {
    # Creative tasks (higher temperature)
    "creative_writing": {"temperature": 0.9},
    "brainstorming": {"temperature": 0.8},
    "storytelling": {"temperature": 0.85},
    
    # Conversational tasks (medium temperature)
    "general_chat": {"temperature": 0.7},
    "summarization": {"temperature": 0.5},
    
    # Precise tasks (low temperature)
    "translation": {"temperature": 0.3},
    "code_generation": {"temperature": 0.2},
    "data_extraction": {"temperature": 0.1},
    
    # Deterministic tasks (zero temperature)
    "classification": {"temperature": 0.0},
    "structured_output": {"temperature": 0.0},
    "yes_no_questions": {"temperature": 0.0}
}

def generate_for_task(prompt, task_type):
    sampling = TASK_SAMPLING.get(task_type, {"temperature": 0.7})
    return client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": prompt}],
        **sampling
    )
```

## Detection strategy

Detecting OSP can be framed as a structural check over LLM invocation sites:

1. **Parse the code**: build an AST with scope information
2. **Identify calls**: detect provider-specific call sites (`messages.create`, `chat.completions.create`, etc.)
3. **Check sampling controls**: detect multiple sampling parameters set at the same call
4. **Context analysis**: account for context managers and option wrappers
5. **Conservative exclusions**: ignore cases with a single explicit parameter

## Recommendations

1. **Pick a single primary control** per call
2. **Document the rationale** for the chosen control
3. **Centralize defaults** in a wrapper layer
4. **Validate with regression tests** after provider or model changes
5. **Avoid implicit defaults** that may change across providers

## Limitations

- Static detection cannot fully resolve dynamically constructed configurations
- May miss overspecification spread across separate configuration files
- Conservative handling of wrappers that pass parameters indirectly
- Does not judge whether the selected control is the correct choice for a task



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
