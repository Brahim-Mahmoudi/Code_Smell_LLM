# Methodology: Literature Review & Code-Smell Extraction (LLM Integration)

This document details how we (i) searched and selected the literature on LLM integration code smells & anti-patterns and (ii) constructed the resulting code-smell catalog.

## 1) Scope & Research Questions

We target code-level issues that arise when integrating Large Language Models (LLMs) into software systems (e.g., API misuse, quota handling, structured output, prompt plumbing, reliability, cost/performance risks). Our review asks:

- **RQ1 — Evidence**: What defects, smells, or anti-patterns are reported around LLM/AI integration?
- **RQ2 — Practices**: What mitigation strategies, refactorings, or best practices are suggested?
- **RQ3 — Catalog**: How can these findings be consolidated into a practitioner-oriented code smell catalog?

## 2) Search Strategy

We combined topic, platform/vendor, and software-quality facets using Boolean operators (Figure 1).





### 2.1 Data Sources

- **Academic**: Google Scholar, ACM Digital Library, IEEE Xplore, arXiv, Scopus.
- **Grey literature**: provider docs, engineering blogs, cookbooks, issue trackers, Q&A, and technical posts.

### 2.2 Boolean Queries (core template)

We instantiated the diagram into reproducible strings (adapt prefixes/suffixes per portal):

- **Academic :**  
```sql
( large language model OR LLM  OR retrieval-Augmented Generation OR  RAG OR intelligent systems OR foundation models OR transformers )
AND
( agent defects OR code smells OR code defects OR prompt smells OR code quality OR best practices OR refactoring OR technical debt OR common coding mistakes OR coding anti-pattern OR setting OR inference OR inference practice OR inference quality OR failures OR Reliability OR Robustness OR Performance OR Maintanbility )
```

- **ACM :**
```sql 
Title:(("large language model" OR LLM OR "foundation models" OR transformers) AND ("code smells" OR "code defects" OR "prompt smells" OR "code quality" OR "best practices" OR "technical debt" OR "common coding mistakes" OR "anti-pattern" OR "inference quality")) OR Keyword:(("large language model" OR LLM OR "foundation models" OR transformers) AND ("code smells" OR "code defects" OR "prompt smells" OR "code quality" OR "best practices" OR "technical debt" OR "common coding mistakes" OR "anti-pattern")) "filter": {ACM Content: DL}

```

- **IEE Explore :**
```sql 
(("Document Title":"large language model" OR "Document Title":LLM OR "Document Title":"foundation models" OR "Document Title":transformers 
OR "Author Keywords":"large language model" OR "Author Keywords":LLM OR "Author Keywords":"foundation models" OR "Author Keywords":transformers)
AND
("Document Title":"code smells" OR "Document Title":"code defects" OR "Document Title":"prompt smells" OR "Document Title":"code quality" OR "Document Title":"best practices" OR "Document Title":"technical debt" OR "Document Title":"common coding mistakes" OR "Document Title":"anti-pattern" OR "Document Title":"inference quality" OR "Document Title":failures 
OR "Author Keywords":"code smells" OR "Author Keywords":"code defects" OR "Author Keywords":"prompt smells" OR "Author Keywords":"code quality" OR "Author Keywords":"best practices" OR "Author Keywords":"technical debt" OR "Author Keywords":"common coding mistakes" OR "Author Keywords":"anti-pattern" OR "Author Keywords":"inference quality" OR "Author Keywords":failures))

```
- **Scopus :**
```sql 
TITLE ( ( "large language model" OR LLM OR "foundation models" OR transformers ) AND ( "code smells" OR "code defects" OR "prompt smells" OR "code quality" OR "best practices" OR "technical debt" OR "common coding mistakes" OR "anti-pattern" OR inference OR "inference quality" OR failures ) ) AND PUBYEAR > 2016 AND PUBYEAR < 2026 AND ( LIMIT-TO ( SUBJAREA , "COMP" ) )
```

- **ArXiv :** See script 
```sql
((ti:"large language model" OR abs:"large language model" OR ti:"LLM" OR abs:"LLM" OR ti:"foundation models" OR abs:"foundation models" OR ti:"transformers" OR abs:"transformers"))

AND

((ti:"code smells" OR abs:"code smells" OR ti:"code defects" OR abs:"code defects" OR ti:"prompt smells" OR abs:"prompt smells" OR ti:"code quality" OR abs:"code quality" OR ti:"best practices" OR abs:"best practices" OR ti:"technical debt" OR abs:"technical debt" OR ti:"common coding mistakes" OR abs:"common coding mistakes" OR ti:"anti-pattern" OR abs:"anti-pattern" OR ti:"inference quality" OR abs:"inference quality" OR ti:"failures" OR abs:"failures"))
```
 







## 3) Study Selection Workflow

We followed a PRISMA-like funnel.



### Steps

1. Search & import from all sources; normalize metadata; remove exact duplicates.
2. Title/abstract screening against inclusion/exclusion rules (below).
3. Snowballing (backward/forward) on the surviving set.
4. Full-text screening and eligibility decision.


### Inclusion Criteria

- Discusses code-level LLM/AI integration issues (not only model internals).
- Provides concrete symptoms, failure modes, smells/anti-patterns, or actionable practices.
- Peer-reviewed venue or credible technical source (for grey literature).

### Exclusion Criteria

- Pure ML/LLM modeling papers without software integration focus.
- Opinion pieces lacking technical detail or verifiable examples.
- Duplicates/extended abstracts without additional evidence.

## 4) Data Extraction & Coding

For each included item, we extracted:

- Bibliographic info (venue, year, link)
- Context (API/SDK/runtime, deployment setting)
- Defect/smell description (name, intent, when it appears)
- Mechanism (root cause, triggering conditions)
- Effects (reliability, performance, cost, security, reproducibility, maintainability)
- Mitigations (tests, guards, refactorings, patterns)
- Artifacts (code snippets, configs, logs)
- Evidence type (empirical study, industrial report, doc guideline, bug/issue)

Two reviewers independently coded items and reconciled disagreements. We computed Cohen's κ to assess agreement on inclusion and on smell assignments, then resolved via adjudication.

## 5) Building the Code-Smell Catalog

We synthesized the evidence into a catalog construction pipeline (Figure 3).

![Catalog construction pipeline](static/Extraction_Methodology.png)
*Figure 3 — Catalog construction and validation pipeline.*


Following this methodology, we extracted 5 new LLM integration code smells:
For each code smell we have:
- **Name & Intent**
- **Context**
- **Problem**
- **Solution**
- **Effect on Software Quality**
- **Minimal Example (bad → good)**
- **Sources/References**

### Here are the code smells descriptions :

- [No_Structured_Output](Code_Smells_Description/No_Structured_Output.md)
- [No_System_Message](Code_Smells_Description/No_System_Message.md)
- [No_Version_Model_Pinning](Code_Smells_Description/No_Version_Model_Pinning.md)
- [Temperature_Not_Explicitly_Set](Code_Smells_Description/Temperature_Not_Explicitly_Set.md)
- [Unbounded_Max_Metrics](Code_Smells_Description/Unbounded_Max_Metrics.md)

### Pipeline Stages

1. Paper mining: extract candidate smells, symptoms, and mitigations from included papers.
2. Grey-literature mining: triangulate with provider docs, cookbooks, and engineering posts.
3. GitHub mining: scan representative LLM-integrating repos to observe real-world instances.
4. Stack Overflow mining: collect common failure patterns and developer remedies.
5. Library documentation checks: align smells with official API semantics (limits, timeouts, streaming, JSON, retries).
6. Normalization: merge synonyms; define each smell with Name, Intent, Context, Problem, Consequences, Refactoring/Fix, and Minimal (bad→good) example.
7. Validation: internal walkthroughs and expert feedback on clarity, distinctness, and actionability.
8. Final catalog: stable identifiers and cross-references to evidence and examples.

## 6) Quality Assurance

- Dual screening & coding with κ statistics and reconciliation.
- Traceability: each catalog entry cites one or more source items (paper or grey literature) and, where possible, code evidence.
- Replicability: we preserve the query strings, inclusion/exclusion rules, and versioned datasets (papers list, grey-lit list, mined snippets).

## 7) Threats to Validity

- Search bias: mitigated via multiple portals, synonym expansion, and snowballing.
- Grey-literature credibility: mitigated by favoring provider docs and well-established engineering sources.
- Evolving APIs: vendor limits and SDKs change; we timestamp sources and note model/API versions.
- Construct validity: our smells target code-integration phenomena (not prompt quality alone); definitions underwent expert review.

## 8) Reuse Checklist

 Run the Boolean queries (Section 2.2) on your target portals.  
 Apply the funnel (Figure 2) with the stated criteria.  
 Extract with the schema in Section 4; compute Cohen's κ.  
 Build/validate the catalog via the pipeline in Figure 3.  
 Archive query strings, lists of included items, and examples.

## Figures

- **Figure 1**: Query.png — Search facets and Boolean composition.
- **Figure 2**: Paper_Selection_Process.png — Selection funnel and counts.
- **Figure 3**: Extraction_Methodology.png — Catalog construction pipeline.