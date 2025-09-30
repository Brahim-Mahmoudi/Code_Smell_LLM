![Overview](static/AI-based%20system.png)

# SpecDetect4LLM Documentation

Welcome to the SpecDetect4LLM documentation.

This space contains structured guides and reference materials to help users and contributors.

## Sections

- [Usage Guide](docs/usage.md)
- [Usage Guide with Docker](docs/docker.md)
- [Rules Overview](docs/rules.md)
- [Predicate Library](docs/predicates.md)
- [Add New Rule](docs/add_rule.md)
- [Comparative Specification with Other DSL](docs/comparaison_other_dsl.md)
- [Ground Truth Construction](docs/Ground_Truth_Construction.md)
- [Comparative Precision with Other Tools](docs/Comparison_other_tools.md)


## Structure of the repo 

```
/docs # all the documentation

/static # images of the repo

/DSL_Compare # Comparison between other DSL (Semgrep and CodeQL)

/RAG # Other project with (LLM) RAG to create new rules

/Evaluation # Evaluation folder with ground truth and mlflow comparison 

/grammar # grammar of the DSL in .lark

/parser # DSL parser in .py

/test_rules # all the rules with all the files needed to test each
     /RX # all the rules X between 1 and 29 
        /generated_rules_RX.py # the matcher generated 
        /test_RX.py # the test file of the rule 
        /test_RX.dsl # the rule write in DSL Format

/docs # all the documentation

/static # images of the repo
    
/grammar # grammar of the DSL in .lark

/parser # DSL parser in .py

/test_rules # all the rules with all the files needed to test each
    /RX # all the rules X between 1 and 22 
        /generated_rules_RX.py # the matcher generated 
        /test_RX.py # the test file of the rule 
        /test_RX.dsl # the rule write in DSL Format
```
