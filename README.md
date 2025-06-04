# COSÌ - Catalogo Online dei Segnali discorsivi dell’Italiano

## Authors

**Miriam Voghera¹*,°, Andrea Sansò¹°, Iolanda Alfano¹°, Alfonsina Buoniconto¹°, Giovanni Di Paola¹°, Pasquale Esposito¹°, Flavio Pisciotta¹°, Carmela Sammarco¹°, Luisa Troncone¹°**  
¹ Laboratorio PAROLE, DipSUm - Dipartimento di Studi Umanistici, Università di Salerno

---

## Table of Contents

- [Introduction](#introduction)
- [Background and Motivation](#background-and-motivation)
- [Annotation Initiatives](#annotation-initiatives)
- [Building COSÌ](#building-così)
  - [General Architecture](#general-architecture)
  - [A Corpus-Based Approach](#a-corpus-based-approach)
  - [Selecting DMs](#selecting-dms)
  - [Annotation Schema Design](#annotation-schema-design)
  - [Interoperability](#interoperability-with-the-source-corpus)
- [References](#references)

---

## Introduction

**COSÌ** is an open online catalog of Italian discourse markers (Segnali discorsivi).  
It provides a comprehensive, corpus-based resource for the analysis, annotation, and exploration of discourse markers (DMs) in contemporary spoken Italian.

---

## Background and Motivation

To our knowledge, the only existing online resource entirely devoted to DMs is the _Diccionario de Partículas Discursivas del Español_ (DPDE; Briz et al. 2008). While excellent, its static design presents certain limitations that COSÌ aims to overcome:

- No direct link to the corpus for spoken examples; speaker metadata is inaccessible.
- Register information is presented assertively, rather than allowing user-driven context exploration.
- Prosodic features are only accessible via limited examples, sometimes inferred from written language.
- No dynamic, corpus-driven exploration or reproducible annotation process.

COSÌ is grounded in the philosophy of **linked data**, focusing on interoperability, sustainability, and reusability. It is designed to interact with the _Kiparla_ corpus of spoken Italian.

---

## Annotation Initiatives

The main prior annotation model for DMs is **MDMA** (Bolly et al., 2015). It:

- Covers all stages of DM analysis—from identification to annotation.
- Uses corpus-based, objective, and replicable criteria.
- Distinguishes DM and non-DM uses of the same lexical items.
- Relies on syntactic, semantic, and contextual criteria.
- Maximizes objectivity and inter-annotator agreement.

COSÌ builds on MDMA’s strengths, especially in operationalizing objective criteria, and extends annotation to:

- Clusters of DMs, macro- and micro-functions.
- Systematic connection with a large spoken corpus for sociolinguistic profiling and cluster analysis.

---

## Building COSÌ

### General Architecture

COSÌ consists of **two parts**:

1. **Website**  
   - User interface to explore each DM’s frequency, functions, and usage profiles.

2. **Open Repository**  
   - Data files, annotation guidelines, substitution test results, and occurrence contexts.

For each DM, you will find:

- Annotated occurrences from Kiparla (contextualized with X words before/after).
- Substitution tests for transparent and verifiable DM annotation.
- Functional annotation files.

---

### A Corpus-Based Approach

Development relies on a **corpus-based approach** ([Biber et al., 1994]), focusing on the **KIParla** corpus ([Mauri et al., 2019]) and its modules (KIP, KIPasti, ParlaTO, ParlaBO), current as of 2025.

---

### Selecting DMs

DM selection combined:

- **Frequency**: Frequency lists from KIParla and VoLIP ([Voghera et al., 2014]).
- **Functional Salience and Theoretical Relevance**: Tokens flagged as potential DMs from out-of-context frequency lists.

Key numbers:

- 1,517 tokens (min 100 occurrences); 175 flagged as potential DMs.
- Occurrence frequencies from 30,666 (eh) to 101 (evidentemente).
- For high-frequency DMs (>800), max 800 random instances extracted; for rare DMs, all are included.

Occurrences are extracted randomly via NoSketchEngine, with full KIParla metadata for traceability and interoperability.

---

### Annotation Schema Design

Annotation distinguishes between DM and non-DM uses with **three diagnostic substitution tests**, tailored to each DM due to morphosyntactic variability.

Functional annotation draws on literature, adapted for transparency and practical coverage (see 4.1). A **medium level of granularity** balances descriptive depth with feasibility.

---

### Interoperability with the Source Corpus

- All DM occurrences retain full KIParla metadata.
- Annotation is compatible with the **CoNLL-U format** used for the KIParla treebank ([Pannitto & Mauri, 2024; Pannitto, 2024]).
- Ensures long-term reusability and integration with related linguistic resources.

---

## References

- Biber, D., et al. (1994). [Title].  
- Briz, A., et al. (2008). _Diccionario de Partículas Discursivas del Español (DPDE)_.  
- Bolly, C., et al. (2015). [Title].  
- Mauri, C., et al. (2019). [Title].  
- Voghera, M., et al. (2014). [Title].  
- Pannitto, G. & Mauri, C. (2024). [Title].  

---

**For questions or contributions, please contact:**  


Laboratorio PAROLE, DipSUm, Università di Salerno


