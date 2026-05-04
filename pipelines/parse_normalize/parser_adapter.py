"""Parser adapter routing for Week07 document normalization."""

import re

from pipelines.parse_normalize.models import (
    DEFAULT_PARSE_STRATEGY_VERSION,
    ParsedSection,
    ParserCapability,
    SourceDocument,
    stable_id,
)


SECTION_SPLIT_RE = re.compile(r"\n\s*\n+")


def _base_warning(document: SourceDocument, parser_name: str) -> list[str]:
    warnings = list(document.warnings)
    if parser_name == "fallback":
        warnings.append("fallback_parser_used")
    return sorted(set(warnings))


def _capability(
    *,
    parser_name: str,
    asset_type: str,
    fallback_used: bool,
    warnings: list[str],
) -> ParserCapability:
    if parser_name == "docling" and not fallback_used:
        return ParserCapability(
            preserves_page=True,
            preserves_bbox=True,
            preserves_table=True,
            fallback_used=False,
            warnings=warnings,
        )
    if parser_name == "unstructured" and not fallback_used:
        return ParserCapability(
            preserves_page=asset_type == "pdf",
            preserves_bbox=False,
            preserves_table=True,
            fallback_used=False,
            warnings=warnings,
        )
    return ParserCapability(
        preserves_page=asset_type == "pdf",
        preserves_bbox=False,
        preserves_table=False,
        fallback_used=True,
        warnings=warnings,
    )


def _paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    parts = [p.strip() for p in SECTION_SPLIT_RE.split(normalized) if p.strip()]
    if parts:
        return parts
    return [normalized]


def _section_type_for(text: str, index: int) -> str:
    if index == 0 and len(text) <= 120:
        return "title"
    if text.lstrip().startswith(("-", "*", "1.")):
        return "list"
    return "text"


def _fallback_parse(
    document: SourceDocument,
    *,
    parser_backend: str,
    parse_strategy_version: str,
    warnings: list[str],
) -> list[ParsedSection]:
    capability = _capability(
        parser_name=parser_backend,
        asset_type=document.asset_type,
        fallback_used=True,
        warnings=warnings,
    ).to_dict()
    sections: list[ParsedSection] = []
    for index, paragraph in enumerate(_paragraphs(document.raw_text)):
        page_no = 1 if document.asset_type == "pdf" else None
        bbox_missing_reason = "fallback_parser_no_bbox" if document.asset_type == "pdf" else None
        section_path = paragraph.splitlines()[0][:80] if paragraph else f"section_{index}"
        section_id = stable_id(
            "section",
            document.source_fingerprint,
            document.doc_id,
            index,
            section_path,
        )
        sections.append(
            ParsedSection(
                section_id=section_id,
                doc_id=document.doc_id,
                source_id=document.source_id,
                source_fingerprint=document.source_fingerprint,
                asset_type=document.asset_type,
                section_index=index,
                section_path=section_path or f"section_{index}",
                section_type=_section_type_for(paragraph, index),
                content=paragraph,
                page_no=page_no,
                bbox=None,
                bbox_missing_reason=bbox_missing_reason,
                parser_backend="fallback",
                parser_capability=capability,
                parse_strategy_version=parse_strategy_version,
                data_release_id=document.data_release_id,
                doc_version=document.doc_version,
                source_url_or_path=document.source_url_or_path,
                metadata={
                    "manifest_id": document.manifest_id,
                    "batch_id": document.batch_id,
                    "raw_available": document.raw_available,
                },
            )
        )
    return sections


def _parse_with_unstructured(
    document: SourceDocument,
    *,
    parse_strategy_version: str,
    warnings: list[str],
) -> list[ParsedSection]:
    try:
        from unstructured.partition.text import partition_text
    except Exception:
        warnings.append("unstructured_unavailable_fallback_used")
        return _fallback_parse(
            document,
            parser_backend="fallback",
            parse_strategy_version=parse_strategy_version,
            warnings=warnings,
        )

    elements = partition_text(text=document.raw_text)
    capability = _capability(
        parser_name="unstructured",
        asset_type=document.asset_type,
        fallback_used=False,
        warnings=warnings,
    ).to_dict()
    sections: list[ParsedSection] = []
    for index, element in enumerate(elements):
        content = str(element).strip()
        if not content:
            continue
        section_path = content.splitlines()[0][:80]
        section_id = stable_id("section", document.source_fingerprint, document.doc_id, index, section_path)
        sections.append(
            ParsedSection(
                section_id=section_id,
                doc_id=document.doc_id,
                source_id=document.source_id,
                source_fingerprint=document.source_fingerprint,
                asset_type=document.asset_type,
                section_index=index,
                section_path=section_path or f"section_{index}",
                section_type=_section_type_for(content, index),
                content=content,
                page_no=None,
                bbox=None,
                bbox_missing_reason=None,
                parser_backend="unstructured",
                parser_capability=capability,
                parse_strategy_version=parse_strategy_version,
                data_release_id=document.data_release_id,
                doc_version=document.doc_version,
                source_url_or_path=document.source_url_or_path,
                metadata={"manifest_id": document.manifest_id, "batch_id": document.batch_id},
            )
        )
    return sections


def parse_document(
    document: SourceDocument,
    *,
    parser: str = "auto",
    parse_strategy_version: str = DEFAULT_PARSE_STRATEGY_VERSION,
) -> list[ParsedSection]:
    requested = parser
    if parser == "auto":
        requested = "docling" if document.asset_type == "pdf" else "unstructured"

    warnings = _base_warning(document, "fallback" if requested == "fallback" else requested)

    if requested == "fallback":
        return _fallback_parse(
            document,
            parser_backend="fallback",
            parse_strategy_version=parse_strategy_version,
            warnings=warnings,
        )

    if requested == "unstructured":
        return _parse_with_unstructured(
            document,
            parse_strategy_version=parse_strategy_version,
            warnings=warnings,
        )

    if requested == "docling":
        try:
            from docling.document_converter import DocumentConverter  # noqa: F401
        except Exception:
            warnings.append("docling_unavailable_fallback_used")
            return _fallback_parse(
                document,
                parser_backend="fallback",
                parse_strategy_version=parse_strategy_version,
                warnings=warnings,
            )
        warnings.append("docling_adapter_minimal_fallback_used")
        return _fallback_parse(
            document,
            parser_backend="fallback",
            parse_strategy_version=parse_strategy_version,
            warnings=warnings,
        )

    raise ValueError(f"Unsupported parser: {parser}")


def parse_documents(
    documents: list[SourceDocument],
    *,
    parser: str = "auto",
    parse_strategy_version: str = DEFAULT_PARSE_STRATEGY_VERSION,
) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    for document in documents:
        sections.extend(
            parse_document(
                document,
                parser=parser,
                parse_strategy_version=parse_strategy_version,
            )
        )
    return sections
