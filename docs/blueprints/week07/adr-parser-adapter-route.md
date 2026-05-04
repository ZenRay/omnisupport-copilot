# ADR: Parser Adapter Route

## Decision

Week07 uses a parser adapter with four modes:

- `auto`
- `docling`
- `unstructured`
- `fallback`

`auto` routes PDF-like assets toward Docling and text/HTML-like assets toward Unstructured. If an optional parser dependency is unavailable, the adapter falls back to the stdlib parser and records the reason.

## Why

Course environments vary. Some enterprise machines can run Docker/Podman but cannot install native parser dependencies. A hard dependency on Docling or Unstructured would make Week07 fragile for students.

## Consequences

- The fallback path is deterministic and testable.
- Parser capability is written into every section and anchor.
- Week08 can reject or down-rank fallback outputs if the course later enables stricter indexing gates.
- Real Docling/Unstructured integration remains an instructor-scale upgrade, not a separate architecture.
