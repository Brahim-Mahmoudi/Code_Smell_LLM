# Methodology: Literature Review & Code-Smell Extraction (LLM Integration)

This document details how we (i) searched and selected the literature on LLM integration code smells  and (ii) constructed the resulting code-smell catalog.

### Here are the code smells descriptions :

- [No_Structured_Output](Code_Smells_Description/No_Structured_Output.md)
- [No_System_Message](Code_Smells_Description/No_System_Message.md)
- [No_Version_Model_Pinning](Code_Smells_Description/No_Version_Model_Pinning.md)
- [Temperature_Not_Explicitly_Set](Code_Smells_Description/Temperature_Not_Explicitly_Set.md)
- [Unbounded_Max_Metrics](Code_Smells_Description/Unbounded_Max_Metrics.md)
- [Overspecified_Sampling_Parameters](Code_Smells_Description/Overspecified_Sampling_Parameters.md)
- [Reasoning_Effort_Not_Explicitly_Set](Code_Smells_Description/Reasoning_Effort_Not_Explicitly_Set.md)
- [Raw_Vision_Payload](Code_Smells_Description/Raw_Vision_Payload.md)
- [Anonymous_Inference_Call](Code_Smells_Description/Anonymous_Inference_Call.md)


## Methodology

### Scope & Research Questions

We target code-level issues that arise when integrating Large Language Models (LLMs) into software systems (e.g., API misuse, quota handling, structured output, prompt plumbing, reliability, cost/performance risks). Our review asks:

- **RQ1 — Evidence**: What defects, smells, or anti-patterns are reported around LLM/AI integration?
- **RQ2 — Practices**: What mitigation strategies, refactorings, or best practices are suggested?
- **RQ3 — Catalog**: How can these findings be consolidated into a practitioner-oriented code smell catalog?

### Data Sources

- **Academic literature**: ACM Digital Library, Compendex, IEEE Xplore, ScienceDirect, SpringerLink, Scopus, arXiv, Wiley
- **Grey and empirical literature**: Provider documentation, engineering blogs, GitHub issues, GitHub repositories, Stack Overflow, technical posts

### Catalog Construction Methodology

The code smell was identified through a systematic multi-source approach combining academic literature review with grey and empirical literature mining.

#### 1. Systematic Literature Review (SLR)

We followed the updated PRISMA 2020 guidelines and Kitchenham et al.'s guidelines for systematic reviews in software engineering. The review consisted of four main steps:

**Search Strategy**:
- **Databases**: ACM Digital Library, Compendex, IEEE Xplore, ScienceDirect, SpringerLink, Scopus, arXiv, Wiley
- **Time Frame**: 2017-2025 (capturing the rise of LLM research)
- **Search Query** (using PICO framework):
```
  ("large language model*" OR "LLM*") AND 
  ("integrat*" OR "API*" OR "software system*") AND 
  ("misuse*" OR "defect*" OR "bug*" OR "smell*" OR "pitfall*")
```

**Selection Process**:
1. **Database Identification**: Initial search yielded 2,243 papers across seven libraries
2. **Duplicates Removal**: Exact match on title, first author, and venue
3. **Screening**: Two-phase screening using inclusion/exclusion criteria
   - Phase 1: Title and abstract screening (Cohen's Kappa κ=0.85, near-perfect agreement)
   - Phase 2: Full-text review (Cohen's Kappa κ=0.93, near-perfect agreement)
4. **Snowballing**: Two iterations of backward and forward snowballing added 16 studies
5. **Final Selection**: 27 papers retained for evidence extraction

**Inclusion Criteria**:
- Written in English
- Published between 2017-2025
- Presents LLM-based software system or engineering practice
- Reports concrete integration issues, misuses, defects, or failures
- Provides technical detail about LLM invocation or API configuration
- Provides information to characterize at least one LLM code smell
- Full text available online
- Peer-reviewed

**Exclusion Criteria**:
- Secondary sources (reviews, surveys, opinion pieces)
- No LLM API/SDK interaction described
- No implementation detail for analyzing integration defects
- Focuses exclusively on training/datasets without integration aspects
- Not available online or not in English

#### 2. Grey and Empirical Literature Mining

To capture real-world practices not yet documented in academic venues, we conducted structured mining of grey and empirical literature using GLiSE [Grey Literature Search Engine](https://arxiv.org/abs/2512.23066), a three-step, prompt-driven and ML-powered tool for extracting software engineering literature from Google, GitHub issues, GitHub repositories, and Stack Overflow.

**GLiSE Methodology**:

1. **Prompts Creation**: We created ten distinct textual prompts with varying granularity:
   - Generic prompts for broad LLM integration coverage
   - Specific prompts targeting particular API features and functionalities
   - This multi-prompt approach mitigates risks of overly generic or narrow searches

2. **Extraction with GLiSE**: For each prompt, GLiSE:
   - Generates source-specific search queries
   - Executes queries using respective APIs
   - Screens results based on semantic relevance using embeddings and ML classifiers
   - **Initial Results**: 574 sources (167 Google, 181 GitHub issues, 226 GitHub repos, 0 Stack Overflow)

3. **Manual Filtering**: Additional screening to ensure quality and relevance:
   - GLiSE's automated filtering combined with manual review
   - Strict relevance criteria specific to LLM code smells
   - Exclusion of sources confused with related concepts (e.g., code smells in LLM-generated code)
   - **Final Selection**: 118 sources (47 Google, 40 GitHub issues, 31 GitHub repos, 0 Stack Overflow)

**Complementary Manual Searches**: Targeted searches of official documentation from major providers:
- OpenAI, Gemini, Anthropic, Hugging Face, Ollama
- Focus on reliable sources directly aligned with study subject

#### 3. Evidence Synthesis and Triangulation

For each candidate code smell:
- **Multi-source validation**: Required converging evidence across academic, grey, and empirical sources
- **Triangulation**: Academic publications provide systematic views; grey literature reflects practical developer concerns
- **Conservative admission**: Smells admitted only when:
  - Observable at code level
  - Supported by multiple independent sources
  - Associated with accessible remediation strategy
  - Can be classified within the taxonomy

**Documentation Structure**: Each smell formalized with:
- Name & Definition
- Context & Motivation
- Problem description
- Solution & recommendations
- Examples (bad → good)
- Detection strategy
- Quality effects (robustness, performance, maintainability, reliability)
- Sources & references


### Threats to Validity

- **Search bias**: Mitigated via multiple portals, PRISMA guidelines, and snowballing
- **Grey-literature credibility**: Mitigated through GLiSE's ML-powered filtering and favoring official provider documentation
- **Evolving APIs**: Reasoning controls are recent; we timestamp sources and note model/API versions
- **Construct validity**: Smells target code-integration phenomena; definitions underwent multi-source triangulation and expert review
- **Observability limits**: Static analysis may miss reasoning configuration in external files or dynamic contexts
- **Corpus composition**: Open-source Python projects may not reflect industrial or multi-language practices