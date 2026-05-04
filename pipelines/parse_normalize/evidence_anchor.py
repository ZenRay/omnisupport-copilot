"""Evidence anchor generation for Week07 chunks."""

from pipelines.parse_normalize.models import DocumentChunk, EvidenceAnchor, ParsedSection, stable_id, utc_now_iso


def _sections_by_id(sections: list[ParsedSection]) -> dict[str, ParsedSection]:
    return {section.section_id: section for section in sections}


def build_evidence_anchors(
    sections: list[ParsedSection],
    chunks: list[DocumentChunk],
) -> list[EvidenceAnchor]:
    section_lookup = _sections_by_id(sections)
    anchors: list[EvidenceAnchor] = []

    for chunk in chunks:
        section = section_lookup[chunk.section_id]
        if section.asset_type == "pdf":
            anchor_type = "page" if section.page_no else "fallback"
            bbox_missing_reason = section.bbox_missing_reason or "parser_did_not_emit_bbox"
        elif section.parser_capability.get("fallback_used"):
            anchor_type = "fallback"
            bbox_missing_reason = section.bbox_missing_reason
        else:
            anchor_type = "section"
            bbox_missing_reason = section.bbox_missing_reason

        anchor_id = stable_id(
            "anchor",
            chunk.chunk_id,
            section.section_id,
            section.source_fingerprint,
            section.section_path,
        )
        anchor = EvidenceAnchor(
            anchor_id=anchor_id,
            chunk_id=chunk.chunk_id,
            section_id=section.section_id,
            doc_id=section.doc_id,
            source_id=section.source_id,
            source_fingerprint=section.source_fingerprint,
            asset_type=section.asset_type,
            anchor_type=anchor_type,
            source_url_or_path=section.source_url_or_path or section.source_id,
            section_path=section.section_path,
            doc_version=section.doc_version,
            page_no=section.page_no,
            bbox=section.bbox,
            bbox_missing_reason=bbox_missing_reason,
            parser_backend=section.parser_backend,
            parser_capability=section.parser_capability,
            data_release_id=section.data_release_id,
            created_at=utc_now_iso(),
        )
        chunk.evidence_anchor_ids = [anchor.anchor_id]
        chunk.anchor_count = 1
        anchors.append(anchor)

    return anchors
