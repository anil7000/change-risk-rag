# Change Risk RAG

[![CI](https://github.com/anil7000/change-risk-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/anil7000/change-risk-rag/actions/workflows/ci.yml)

The tool inspects a local plan and emits curated resource/action findings, not raw before/after data. It combines deterministic risk heuristics with retrieved change runbooks and optional LLM review guidance.

Original project created for **Anil Kumar Tangirala**. Python 3.11+; no runtime package dependencies. Version 0.1 is a runnable reference implementation with synthetic examples, not a claim of production deployment.

## Problem it solves

Terraform plans describe changes, but reviewers still need to identify destructive operations, exposure changes and unknown values, then relate them to recovery procedures. Sending a raw plan to a model can unnecessarily expose secrets.

## How it works

```text
Terraform plan JSON --> Schema and action validation
Schema and action validation --> Deterministic risk rules
Deterministic risk rules --> Curated findings without raw values
Change runbooks --> Retrieval
Curated findings without raw values --> Retrieval
Retrieval --> Optional LLM advice
Optional LLM advice --> Citation validation
Citation validation --> Review report
```

1. Validate the supplied JSON and run deterministic domain checks.
2. Select relevant operational facts instead of forwarding a complete raw export.
3. Redact common credential patterns and load bounded local Markdown/text knowledge.
4. Chunk knowledge into 220-word windows with a 40-word overlap; rank with BM25.
5. Optionally combine embedding similarity with BM25 using reciprocal-rank fusion.
6. Give the configured LLM the question, facts and retrieved evidence. Reject malformed answers or missing/unknown citation IDs.
7. Return facts, workflow results, evidence, uncertainty and advisory synthesis separately.

Citation-ID validation does not verify semantic entailment: a valid citation can still support a mistaken model interpretation. Human review is part of the workflow. No retrieved text is treated as authorization to run commands.

## Capabilities

| Risk signal | What is checked |
| --- | --- |
| Delete / replace | Both replacement orders; stateful resource types receive critical review priority |
| New public ingress | New IPv4/IPv6 world CIDRs for supported AWS security-group ingress shapes |
| Protection removal | Disabling deletion protection on supported stateful resources |
| Unknown values | Nested after_unknown values produce explicit uncertainty |
| Forget actions | Resource leaving Terraform management requires ownership review |
| Plan status | Errored and incomplete plan flags are reported |
| Scope / data minimization | Variables, outputs and raw resource values are excluded from model facts |
| Recovery guidance | Retrieves rollout/rollback runbooks for citation-checked LLM advice |

## Quick start: offline, no keys

```bash
git clone https://github.com/anil7000/change-risk-rag.git
cd change-risk-rag
python -m opsrag --input examples/sample.json --format markdown
# Produce a JSON plan using your existing Terraform workflow:
# terraform show -json tfplan > plan.json
python -m opsrag --input plan.json --kb knowledge --format json
```

Inspect each finding's code, severity and resource address. Use --question to focus on backup, rollback, exposure or unknown-value review.

Expects Terraform plan JSON format major version 1 with resource_changes. It reads a local export only and never runs terraform plan/apply. Raw plans can contain sensitive values: keep them outside this repository and share only through your approved workflow.

### What the sample demonstrates

The synthetic plan replaces a database, disables its deletion protection, includes an unknown endpoint and adds world-wide ingress. The deterministic rating is critical. No-op resources do not count as changes, and public egress is not mislabeled as new ingress.

## Enable real LLM + RAG synthesis

Use a local Ollama server or another endpoint implementing the compatible chat-completions API. Install/pull your chosen model separately; this project does not download a model, supply an API key, or create paid resources.

```bash
export OPS_API_BASE=http://localhost:11434/v1
export OPS_MODEL=YOUR_INSTALLED_CHAT_MODEL
# Optional, for hybrid retrieval: install a compatible embedding model first.
# export OPS_EMBED_MODEL=YOUR_INSTALLED_EMBEDDING_MODEL
# For a hosted HTTPS endpoint, set OPS_API_KEY in your shell/secret manager.
python -m opsrag --input examples/sample.json --llm --format markdown
```

PowerShell equivalent:

```powershell
$env:OPS_API_BASE = 'http://localhost:11434/v1'
$env:OPS_MODEL = 'YOUR_INSTALLED_CHAT_MODEL'
python -m opsrag --input examples/sample.json --llm --format markdown
```

The .env.example file documents settings; it is **not automatically loaded**. Credentials belong in environment variables. Without --llm, all analysis and lexical retrieval run locally and no model calls occur. With --llm, curated facts, questions and retrieved chunks are sent to the configured endpoint. Setting OPS_EMBED_MODEL also sends question/runbook text for embeddings. Review your data and endpoint before enabling it.

The default endpoint is loopback-only HTTP. Remote endpoints must use HTTPS; embedded URL credentials and HTTP redirects are rejected. Model requests have a 45-second timeout and a 2 MB response limit. Corpus limits are 500 files, 256 KB/file and 2 MB total. These are basic safeguards, not comprehensive DLP or prompt-injection protection.

## Test and inspect

```bash
python -m unittest discover -s tests -v
python -m opsrag --input examples/sample.json --format json
```

Tests cover domain behavior and edge cases, retrieval ranking, abstention, invalid citations, redaction, and real HTTP transport against a deterministic local test double for chat and embeddings. The test double validates integration mechanics, **not live-model answer quality**. A live model has not been evaluated in this repository's initial build. GitHub Actions runs the suite on Python 3.11, 3.12 and 3.13.

Optional container CLI:

```bash
docker build -t change-risk-rag .
docker run --rm change-risk-rag
```

The image runs as a non-root user. The initial build was tested with Python; a Docker build requires Docker and is not represented as verified unless you run it. For the interactive bot, run the documented Python command on the host; the CLI Docker image is not configured as a network service.

## Repository map

```text
opsrag/domain.py       Domain checks and curated facts
opsrag/rag.py          BM25, optional embeddings, transport and citation checks
opsrag/cli.py          JSON/Markdown CLI
knowledge/runbook.md  Original synthetic starter knowledge
examples/sample.json  Reproducible synthetic input
tests/                Behavioral and transport tests
.github/workflows/    CI matrix
```

## Limits and next engineering steps

Risk is a transparent heuristic, not a probability of failure. Resource-specific checks currently cover a limited set of AWS ingress/stateful shapes plus destructive actions for other resource types. Existing exposure changes, arbitrary IAM policy semantics and every provider's schema are not fully modeled. Human review remains necessary even when no rules trigger. No patch or plan is applied.

Future work: broaden domain fixtures, evaluate retrieval/answer quality with a real model, implement enterprise identity/audit requirements before shared deployment, and add connector integrations only when their data/access scope is defined.

## Engineering references

- [HashiCorp: Terraform JSON format](https://developer.hashicorp.com/terraform/internals/json-format)
- [Ollama's compatible API documentation](https://docs.ollama.com/api/openai-compatibility)

The operational rules and examples here are original starter implementations informed by public documentation. The three companion projects share an original retrieval/transport core while implementing different domain logic. Source code was developed with AI assistance and is maintained under this account; imported projects elsewhere in the profile retain their own upstream history and licenses.

## License

MIT. Copyright (c) 2026 Anil Kumar Tangirala. See [LICENSE](LICENSE).
