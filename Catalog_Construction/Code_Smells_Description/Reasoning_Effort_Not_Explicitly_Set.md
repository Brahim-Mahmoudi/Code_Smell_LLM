# Code Smell: Reasoning Effort Not Explicitly Set (RENES)

## Definition

**Reasoning Effort Not Explicitly Set (RENES)** is an anti-pattern that occurs when reasoning-capable LLMs (like OpenAI's o1, o3, or GPT-5 series) are called without explicitly configuring the reasoning depth or effort parameter. These models perform internal reasoning before generating responses, and failing to specify this parameter leads to unpredictable behavior and costs.

## Motivation

Reasoning-capable LLMs expose controls that determine how much internal reasoning they perform before generating a response. These controls directly affect:

- **Accuracy and robustness** for complex tasks
- **Latency** and response time
- **Cost** per API call
- **Reproducibility** of results

Not setting reasoning effort explicitly can lead to:
- **Non-transparent behavior changes** when migrating models or endpoints
- **Reproducibility issues** across different deployments
- **Cost surprises** when defaults change
- **Performance inconsistencies** without visible code changes
- **Maintainability problems** as model versions evolve

## Impact

Relying on implicit reasoning defaults causes:
- Unpredictable costs as provider defaults may change
- Inconsistent performance across deployments
- Difficulty reproducing results
- Hidden complexity in debugging
- Unclear optimization opportunities

## Examples

###  Bad Practices
```python
# OpenAI o1/o3/GPT-5 without reasoning effort
client = OpenAI()
response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role": "user", "content": "Complex analysis task"}]
    # Missing reasoning effort!
)

# Anthropic Claude with thinking without depth
response = anthropic.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    thinking={"type": "enabled"},  # No budget specified!
    messages=[{"role": "user", "content": "Solve this"}]
)

# Google Gemini thinking mode without budget
response = model.generate_content(
    "Complex reasoning task",
    generation_config={"thinking_mode": True}  # No budget!
)

# LangChain with reasoning model without effort
llm = ChatOpenAI(model="o1-preview")  # No reasoning effort!
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run(input)

# Implicit default reliance
def solve_problem(problem):
    # Relies on whatever the provider's default is
    return client.responses.create(
        model="o3-2025-01-31",
        input=[{"role": "user", "content": problem}]
    )
```

### ✅ Good Practices
```python
# OpenAI with explicit reasoning effort
response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role": "user", "content": "Complex analysis task"}],
    reasoning={"effort": "medium"}  # Explicit control
)

# High-stakes task with maximum reasoning
response = client.responses.create(
    model="o3-2025-01-31",
    input=[{"role": "user", "content": "Safety-critical decision"}],
    reasoning={"effort": "high"}  # Documented choice
)

# Low-latency task with minimal reasoning
response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    input=[{"role": "user", "content": "Simple classification"}],
    reasoning={"effort": "minimal"}  # Performance-optimized
)

# Anthropic with explicit thinking budget
response = anthropic.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    thinking={
        "type": "enabled",
        "budget_tokens": 5000  # Explicit budget
    },
    messages=[{"role": "user", "content": "Solve this"}]
)

# Google Gemini with explicit thinking budget
response = model.generate_content(
    "Complex reasoning task",
    generation_config={
        "thinking_mode": True,
        "thinking_budget": 3000  # Explicit budget
    }
)

# LangChain with explicit configuration
llm = ChatOpenAI(
    model="o1-preview",
    model_kwargs={"reasoning_effort": "medium"}  # Explicit
)
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run(input)
```

### Context-Appropriate Configuration
```python
# Interactive chatbot: low latency priority
def handle_chat_message(user_input):
    """Fast responses for interactive use."""
    return client.responses.create(
        model="gpt-5.1-mini-2025-02-01",
        input=[{"role": "user", "content": user_input}],
        reasoning={"effort": "minimal"}  # Fast responses
    )

# Code review: high accuracy priority
def review_code(code):
    """Thorough analysis for code quality."""
    return client.responses.create(
        model="o3-2025-01-31",
        input=[{"role": "user", "content": f"Review this code: {code}"}],
        reasoning={"effort": "high"}  # Thorough analysis
    )

# Batch processing: cost-performance balance
def process_batch(items):
    """Balanced approach for batch jobs."""
    return [
        client.responses.create(
            model="gpt-5.1-mini-2025-02-01",
            input=[{"role": "user", "content": item}],
            reasoning={"effort": "medium"}  # Cost-performance balance
        )
        for item in items
    ]

# Safety-critical decision: maximum reasoning
def evaluate_safety_risk(scenario):
    """Maximum reasoning for safety decisions."""
    return client.responses.create(
        model="o3-2025-01-31",
        input=[{"role": "user", "content": f"Evaluate safety: {scenario}"}],
        reasoning={"effort": "high"}  # Safety-critical
    )

# Simple classification: minimal reasoning
def classify_category(text):
    """Quick classification task."""
    return client.responses.create(
        model="gpt-5.1-mini-2025-02-01",
        input=[{"role": "user", "content": f"Classify: {text}"}],
        reasoning={"effort": "minimal"}  # Simple task
    )
```

## Reasoning Effort Guidelines by Task Type
```python
REASONING_CONFIGS = {
    # Minimal reasoning (fast, low cost)
    "simple_classification": {
        "effort": "minimal",
        "use_cases": ["Category classification", "Sentiment analysis", "Simple Q&A"]
    },
    "interactive_chat": {
        "effort": "minimal",
        "use_cases": ["Chatbot responses", "Real-time interactions", "Quick lookups"]
    },
    "text_generation": {
        "effort": "minimal",
        "use_cases": ["Content drafting", "Simple formatting", "Basic summaries"]
    },
    
    # Medium reasoning (balanced)
    "data_analysis": {
        "effort": "medium",
        "use_cases": ["Report generation", "Trend analysis", "Standard insights"]
    },
    "code_generation": {
        "effort": "medium",
        "use_cases": ["Function writing", "Code refactoring", "API integration"]
    },
    "content_creation": {
        "effort": "medium",
        "use_cases": ["Article writing", "Documentation", "Marketing copy"]
    },
    
    # High reasoning (thorough, higher cost)
    "complex_problem_solving": {
        "effort": "high",
        "use_cases": ["Mathematical proofs", "Algorithm design", "System architecture"]
    },
    "code_review": {
        "effort": "high",
        "use_cases": ["Security review", "Performance analysis", "Architecture review"]
    },
    "safety_critical": {
        "effort": "high",
        "use_cases": ["Medical advice", "Legal analysis", "Safety evaluations"]
    },
    "research_analysis": {
        "effort": "high",
        "use_cases": ["Literature review", "Hypothesis generation", "Deep analysis"]
    }
}

def get_reasoning_config(task_type):
    """Get appropriate reasoning configuration for task type."""
    return REASONING_CONFIGS.get(
        task_type,
        {"effort": "medium"}  # Safe default
    )

def create_request_with_task(prompt, task_type):
    """Create request with task-appropriate reasoning."""
    config = get_reasoning_config(task_type)
    return client.responses.create(
        model="gpt-5.1-mini-2025-02-01",
        input=[{"role": "user", "content": prompt}],
        reasoning=config
    )
```

## Detection Strategy

RENES detection can be formulated as a structural check of reasoning-capable model calls:

1. **AST parsing**: Analyze source code and build syntax tree with context
2. **Identify reasoning-capable models**: Detect calls to o1, o3, gpt-5 series, Claude with thinking, Gemini with thinking mode
3. **Check reasoning parameter presence**: Verify absence of `reasoning_effort`, `reasoning` dict with `effort` key, `thinking_budget`, or similar controls
4. **Model family recognition**: Identify by model name patterns, API endpoint patterns, known reasoning model identifiers
5. **Smart exclusions**: Ignore non-reasoning models, calls where reasoning is explicitly disabled, models without reasoning support
6. **Report**: `WARNING: Reasoning-capable model called without explicit reasoning effort at line N`

## Recommendations

### Essential Rules

1. **Always set reasoning effort explicitly** as part of your model call contract
2. **Document reasoning choices** in code comments or configuration
3. **Match reasoning level to task criticality**:
   - `minimal`: Interactive UIs, simple tasks, high-throughput scenarios
   - `medium`: Standard analytical tasks, balanced use cases
   - `high`: Safety-critical, complex problem-solving, high-stakes decisions

### Best Practices

4. **Version control reasoning configurations** alongside model versions
5. **Monitor cost and latency** impacts when changing reasoning levels
6. **Include reasoning parameters** in experimental protocols for reproducibility
7. **Create task-specific presets** for common use cases
8. **Test across reasoning levels** to find optimal balance
9. **Log reasoning effort** alongside other request metadata
10. **Review reasoning defaults** when updating model versions

## Configuration Management
```python
# Centralized reasoning configuration
class ReasoningConfig:
    """Centralized reasoning effort management."""
    
    PRESETS = {
        "fast": {"effort": "minimal"},
        "balanced": {"effort": "medium"},
        "thorough": {"effort": "high"}
    }
    
    @classmethod
    def for_task(cls, task_type):
        """Get reasoning config for specific task."""
        return REASONING_CONFIGS.get(task_type, cls.PRESETS["balanced"])
    
    @classmethod
    def for_latency_budget(cls, max_seconds):
        """Choose reasoning based on latency budget."""
        if max_seconds < 5:
            return cls.PRESETS["fast"]
        elif max_seconds < 15:
            return cls.PRESETS["balanced"]
        else:
            return cls.PRESETS["thorough"]
    
    @classmethod
    def for_cost_budget(cls, max_cost_per_request):
        """Choose reasoning based on cost budget."""
        if max_cost_per_request < 0.01:
            return cls.PRESETS["fast"]
        elif max_cost_per_request < 0.05:
            return cls.PRESETS["balanced"]
        else:
            return cls.PRESETS["thorough"]

# Usage
def solve_with_config(problem, task_type="code_generation"):
    reasoning = ReasoningConfig.for_task(task_type)
    return client.responses.create(
        model="gpt-5.1-mini-2025-02-01",
        input=[{"role": "user", "content": problem}],
        reasoning=reasoning
    )
```

## Limitations

Static detection has several limitations:

- **Cannot detect dynamic reasoning configuration** passed through variables or config files
- **May not recognize** all provider-specific reasoning parameter names
- **Conservative on custom wrappers** that abstract API calls
- **Cannot validate** if the chosen reasoning level is appropriate for the task
- **Misses reasoning controls** in newer or less common LLM providers
- **Cannot detect** when reasoning models are used through third-party libraries with different parameter names

## Cost and Latency Implications
```python
# Typical cost and latency patterns (approximate)

# Minimal reasoning
# - Latency: 1-3 seconds
# - Cost multiplier: 1x baseline
# - Best for: Simple tasks, high volume

# Medium reasoning
# - Latency: 5-15 seconds
# - Cost multiplier: 2-3x baseline
# - Best for: Standard analysis, balanced needs

# High reasoning
# - Latency: 15-60+ seconds
# - Cost multiplier: 4-10x baseline
# - Best for: Complex problems, critical decisions
```

## Validation Checklist

Before deploying reasoning-capable model calls:

- [ ] Is reasoning effort explicitly set?
- [ ] Is the effort level appropriate for the task?
- [ ] Is the reasoning configuration documented?
- [ ] Are cost implications understood and budgeted?
- [ ] Are latency requirements met?
- [ ] Is the configuration version-controlled?
- [ ] Are reasoning parameters logged for debugging?
- [ ] Has the configuration been tested across scenarios?

## Provider-Specific Syntax
```python
# OpenAI o1/o3/GPT-5
response = client.responses.create(
    model="gpt-5.1-mini-2025-02-01",
    reasoning={"effort": "medium"}
)

# Anthropic Claude (thinking mode)
response = client.messages.create(
    model="claude-3-opus-20240229",
    thinking={"type": "enabled", "budget_tokens": 5000}
)

# Google Gemini
response = model.generate_content(
    prompt,
    generation_config={"thinking_mode": True, "thinking_budget": 3000}
)

# Azure OpenAI
response = client.chat.completions.create(
    model="gpt-5-deployment",
    reasoning_effort="medium"
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

