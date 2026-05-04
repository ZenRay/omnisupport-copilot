# Week07 Unstructured Data Runbook

Week7：非结构化数据工程，从原始文档到带证据锚点的可检索文档资产。

## Scope

This runbook validates the Student Core path:

1. Validate Week07 JSON contracts.
2. Run parser adapter in deterministic fallback mode or `auto` mode.
3. Generate sections, chunks, evidence anchors, parse run report, quality report, and Week08-ready gate.
4. Load Dagster definitions without breaking Week06/Week08.
5. Hand off only evidence-anchored chunks to Week08.

Week07 does not build embeddings, create vector indexes, call an LLM, or generate citations.

## Start Local Stack

```bash
cp infra/env/.env.example infra/env/.env.local

docker compose --env-file infra/env/.env.local -f infra/docker-compose.yml up -d --build postgres minio minio_init
```

Podman-compatible route:

```bash
podman compose --env-file infra/env/.env.local -f infra/docker-compose.yml up -d --build postgres minio minio_init
```

## Run Contract Tests

```bash
docker compose --profile tools --env-file infra/env/.env.local -f infra/docker-compose.yml run --rm devbox \
  pytest tests/contract/test_week07_parse_contracts.py -v
```

Expected: valid fixtures pass, missing-anchor and PDF-missing-page fixtures fail as intended.

## Run Parse Dry-Run

```bash
docker compose --profile tools --env-file infra/env/.env.local -f infra/docker-compose.yml run --rm devbox \
  python -m pipelines.parse_normalize.run_parse \
  --manifest-path data/seed_manifests/manifest_workspace_helpcenter_v1.json \
  --parser auto \
  --chunk-strategy section_aware_v1 \
  --data-release-id week07-dev-local \
  --dry-run \
  --artifacts-dir artifacts/week07 \
  --report-json reports/week07/parse_run_report.json \
  --quality-report-md reports/week07/chunk_quality_report.md \
  --week8-gate-json reports/week07/week8_ready_gate.json
```

Expected outputs:

- `artifacts/week07/sections.json`
- `artifacts/week07/chunks.json`
- `artifacts/week07/evidence_anchors.json`
- `artifacts/week07/chunk_quality_samples.json`
- `reports/week07/parse_run_report.json`
- `reports/week07/chunk_quality_report.md`
- `reports/week07/week8_ready_gate.json`

The default manifest points to placeholder S3 paths. In a local classroom checkout, this should produce deterministic fallback output and mark `source_path_missing_synthetic_fallback`. This is expected for dry-run teaching.

## Run With A Local File

```bash
cat > /tmp/week07-help.html <<'HTML'
<h1>Workspace Recovery</h1>
<p>Admins can restore workspace access by validating identity and replaying recovery steps.</p>
<p>Every recovery answer must cite source evidence and preserve release lineage.</p>
HTML

docker compose --profile tools --env-file infra/env/.env.local -f infra/docker-compose.yml run --rm devbox \
  python -m pipelines.parse_normalize.run_parse \
  --input-path /tmp/week07-help.html \
  --source-id doc:workspace:localdemo01 \
  --content-type html \
  --parser fallback \
  --data-release-id week07-local-file-demo \
  --dry-run \
  --artifacts-dir artifacts/week07-local-file \
  --report-json reports/week07/parse_run_report_local_file.json \
  --quality-report-md reports/week07/chunk_quality_report_local_file.md \
  --week8-gate-json reports/week07/week8_ready_gate_local_file.json
```

Expected: fallback parser is still marked, but because the raw file is real, `week8_ready` can be true when anchors and metadata are complete.

## Run Integration Tests

```bash
docker compose --profile tools --env-file infra/env/.env.local -f infra/docker-compose.yml run --rm devbox \
  pytest tests/integration/test_week07_parse_pipeline.py tests/integration/test_week07_quality_gate.py -v
```

## Validate Dagster Definitions

```bash
docker compose --profile tools --env-file infra/env/.env.local -f infra/docker-compose.yml run --rm devbox \
  python -c "from pipelines.definitions import defs; print(defs)"
```

Expected: definitions load with ingestion, parse/normalize, lakehouse, Week06 data factory, and Week08 indexing assets registered.

## Week1-Week6 Regression Checks

```bash
docker compose --profile tools --env-file infra/env/.env.local -f infra/docker-compose.yml run --rm devbox \
  pytest tests/contract/ -v

docker compose --profile tools --env-file infra/env/.env.local -f infra/docker-compose.yml run --rm devbox \
  pytest tests/integration/test_week06_definitions_loadable.py -v
```

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `source_path_missing_synthetic_fallback` | Manifest references S3 placeholder objects | Use dry-run for class, or provide local files with `--input-path`. |
| `source_fingerprint mismatch` | `--expected-fingerprint` does not match raw bytes | Recompute the fingerprint or point to the correct file. |
| `missing_evidence_anchor` | Chunk generation ran without anchor generation | Use `run_parse.py`; do not call chunking alone for Week08 handoff. |
| `week8_ready=false` | Synthetic fallback or blocking quality error | Fix raw source availability or quality gate error before indexing. |
| Dagster import error | Devbox image is stale after dependency changes | Rebuild devbox with Docker or Podman compose. |

## Handoff To Week08

Week08 can consume:

- `artifacts/week07/chunks.json`
- `artifacts/week07/evidence_anchors.json`
- `reports/week07/week8_ready_gate.json`
- `document_chunk` rows mapped to `knowledge_section`
- `evidence_anchor` rows or artifacts
- `chunk_strategy_version`
- `parse_strategy_version`
- `source_fingerprint`
- `doc_version`
- `quality_status`

Week08 cannot assume:

- Chunks without anchors are indexable.
- LLM-generated citations are valid.
- `allowed_for_indexing=false` data can be indexed.
- Fallback parser output has full Docling coordinates.
- Parse/chunk strategy version can be ignored.
