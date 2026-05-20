# Automated Ontology Evaluation for LLM-Generated Ontologies

This repository contains the code, input files, card-sort materials, and evaluation outputs for a research project on automated ontology evaluation methods for LLM-generated ontologies.

The project examines what different automated ontology evaluation methods actually measure, what kind of quality claim their outputs can support, and which assumptions are needed before those claims are valid.

## Research focus

LLM-generated ontologies can be syntactically valid and still contain modelling problems, missing requirements, weak documentation, incorrect relations, or unsupported design choices. Automated evaluation methods can help inspect these outputs, but their results are often narrow. A parser, reasoner, structural metric, pitfall scanner, reference comparison, and competency-question test do not evaluate the same property.

This project therefore separates three layers:

- **evaluation approach**: how the method evaluates the ontology;
- **quality concern**: what aspect of ontology quality the method appears to assess;
- **quality claim**: what can validly be concluded from the method output.

## Repository structure

```text
.
├── card-sort/
├── evaluation/
├── results/
├── docs/
└── README.md
```
