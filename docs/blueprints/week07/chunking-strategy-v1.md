# Chunking Strategy v1

Strategy name: `section_aware_v1`.

## Rules

- Keep parser section boundaries as the first split.
- Split only within a section when content exceeds the configured chunk size.
- Preserve `section_id`, `section_path`, `section_type`, `source_fingerprint`, `doc_version`, `data_release_id`, and `parse_strategy_version`.
- Generate stable `chunk_id` from `source_fingerprint + section_id + section_chunk_index + chunk_strategy_version`.
- Do not merge content across unrelated sections.

## Defaults

- `chunk_size`: manifest `ingest_config.chunk_size` or `512`.
- `chunk_overlap`: manifest `ingest_config.chunk_overlap` or `64`.

## Week08 Contract

Week08 must include `chunk_strategy_version` in its index manifest. If the chunking strategy changes, Week08 should rebuild the index with a new `index_release_id`.
