from typing import Dict, List, Tuple, Iterable, Set
from pydantic import ValidationError
from ..schemas.product_schemas import Product
from ..schemas.persona_schemas import BuyerPersona
from ..schemas.mapping_schemas import PersonaWithMappings
from ..schemas.outreach_schemas import OutreachSequence
from ..schemas.pipeline_schemas import (
    PipelineCompletenessIssue,
    PipelineSectionReport,
    PipelineCompletenessReport,
    CrossComponentCheck,
)


def _is_non_empty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def _item_key(item: Dict, idx: int) -> str:
    if isinstance(item, dict):
        return item.get("persona_name") or item.get("product_name") or item.get("name") or f"#{idx}"
    return f"#{idx}"


def _field_score_for_item(item: Dict, required_fields: List[str]) -> float:
    missing = [f for f in required_fields if f not in item]
    blanks = [f for f in required_fields if f in item and not _is_non_empty(item.get(f))]
    denom = max(1, len(required_fields))
    penalty = len(missing) + len(blanks)
    return round(max(0.0, 1.0 - penalty / denom), 4)


def _field_completion_rates(items: List[Dict], required_fields: List[str]) -> Dict[str, float]:
    total = len(items or [])
    if total <= 0:
        return {f: 0.0 for f in required_fields}
    rates: Dict[str, float] = {}
    for f in required_fields:
        cnt = 0
        for it in items or []:
            if isinstance(it, dict) and _is_non_empty(it.get(f)):
                cnt += 1
        rates[f] = round(cnt / total, 4)
    return rates


def _compute_section_field_scores(items: List[Dict], model_cls) -> Tuple[Dict[str, float], float, Dict[str, float]]:
    required_fields = _required_field_names(model_cls)
    scores_map: Dict[str, float] = {}
    scores_list: List[float] = []
    for idx, it in enumerate(items or []):
        as_dict = it if isinstance(it, dict) else {}
        score = _field_score_for_item(as_dict, required_fields)
        key = _item_key(as_dict, idx)
        scores_map[key] = score
        scores_list.append(score)
    avg_score = round(sum(scores_list) / len(scores_list), 4) if scores_list else 0.0
    field_rates = _field_completion_rates(items or [], required_fields)
    return scores_map, avg_score, field_rates


def _format_error_path(loc: Tuple) -> str:
    parts: List[str] = []
    for p in loc:
        if isinstance(p, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{p}]"
            else:
                parts.append(f"[{p}]")
        else:
            parts.append(str(p))
    return ".".join(parts)


def _required_field_names(model_cls) -> List[str]:
    names: List[str] = []
    try:
        for name, f in model_cls.model_fields.items():
            is_required = getattr(f, "is_required", None)
            if callable(is_required):
                if is_required():
                    names.append(name)
            else:
                if f.default is None:
                    names.append(name)
    except Exception:
        names = list(getattr(model_cls, "model_fields", {}).keys())
    return names


def _field_key_from_loc(loc: Tuple) -> str:
    if not loc:
        return "<root>"
    parts: List[str] = []
    for p in loc:
        if isinstance(p, int):
            parts.append("[]")
        else:
            parts.append(str(p))
    return ".".join(parts)


def _blank_required_violations(item: Dict, required_fields: List[str]) -> List[str]:
    violations: List[str] = []
    for name in required_fields:
        if name in item:
            v = item.get(name)
            if v is None:
                violations.append(name)
            elif isinstance(v, str) and v.strip() == "":
                violations.append(name)
            elif isinstance(v, (list, dict)) and len(v) == 0:
                violations.append(name)
    return violations


def _validate_list(items: List[Dict], model_cls) -> Tuple[int, int, List[PipelineCompletenessIssue], int, List[str], Dict[str, int], int, Dict[str, int]]:
    total = len(items or [])
    valid = 0
    issues: List[PipelineCompletenessIssue] = []
    missing_required_cnt = 0
    field_missing_counts: Dict[str, int] = {}
    required_fields = _required_field_names(model_cls)
    blank_required_cnt = 0
    field_blank_counts: Dict[str, int] = {}

    for idx, item in enumerate(items or []):
        try:
            model_cls(**item)
            # Additional blank checks for required fields
            blanks = _blank_required_violations(item, required_fields)
            if blanks:
                for b in blanks:
                    issues.append(PipelineCompletenessIssue(
                        path=b,
                        message="Field is blank (required non-empty)",
                        type="value_error.blank",
                    ))
                    field_blank_counts[b] = field_blank_counts.get(b, 0) + 1
                blank_required_cnt += 1
                # Do not count as valid when required fields are blank
                continue
            valid += 1
        except ValidationError as e:
            for err in e.errors():
                loc = err.get("loc", ())
                path = _format_error_path(loc)
                msg = err.get("msg", "")
                typ = err.get("type", None)
                full_path = path if path else f"[{idx}]"
                issues.append(PipelineCompletenessIssue(path=full_path, message=msg, type=typ))
                if (typ and "missing" in typ.lower()) or ("required" in msg.lower()):
                    key = _field_key_from_loc(loc)
                    field_missing_counts[key] = field_missing_counts.get(key, 0) + 1
                    missing_required_cnt += 1

    return (
        total,
        valid,
        issues,
        missing_required_cnt,
        required_fields,
        field_missing_counts,
        blank_required_cnt,
        field_blank_counts,
    )


def _ratio(valid: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(valid / total, 4)


def _unique_names(names: Iterable[str]) -> Tuple[bool, List[str]]:
    seen: Set[str] = set()
    dups: List[str] = []
    for n in names:
        if n in seen:
            dups.append(n)
        else:
            seen.add(n)
    return (len(dups) == 0, dups)


def evaluate_pipeline_completeness(payload: Dict) -> PipelineCompletenessReport:
    products = payload.get("products") or []
    personas = payload.get("personas") or []
    mappings = payload.get("personas_with_mappings") or []
    sequences = payload.get("sequences")  # may be None

    sections = {}

    # Products (required)
    p_total, p_valid, p_issues, p_missing, p_required, p_missing_map, p_blank_cnt, p_blank_map = _validate_list(products, Product)
    sections["products"] = PipelineSectionReport(
        name="products",
        required=True,
        present=len(products) > 0,
        total_items=p_total,
        valid_items=p_valid,
        missing_required_errors=p_missing,
        completeness_ratio=_ratio(p_valid, p_total),
        errors=p_issues,
        required_fields=p_required,
        field_missing_counts=p_missing_map,
        blank_required_errors=p_blank_cnt,
        field_blank_counts=p_blank_map,
    )

    # Aggregate field completeness for products (omit per-item scores)
    try:
        _p_scores, p_avg, p_rates = _compute_section_field_scores(products, Product)
        sections["products"].avg_field_score = p_avg
        sections["products"].field_completion_rates = p_rates
    except Exception:
        pass

    # Personas (required)
    pe_total, pe_valid, pe_issues, pe_missing, pe_required, pe_missing_map, pe_blank_cnt, pe_blank_map = _validate_list(personas, BuyerPersona)
    sections["personas"] = PipelineSectionReport(
        name="personas",
        required=True,
        present=len(personas) > 0,
        total_items=pe_total,
        valid_items=pe_valid,
        missing_required_errors=pe_missing,
        completeness_ratio=_ratio(pe_valid, pe_total),
        errors=pe_issues,
        required_fields=pe_required,
        field_missing_counts=pe_missing_map,
        blank_required_errors=pe_blank_cnt,
        field_blank_counts=pe_blank_map,
    )

    # Field completeness scores for personas
    try:
        pe_scores, pe_avg, pe_rates = _compute_section_field_scores(personas, BuyerPersona)
        sections["personas"].item_field_scores = pe_scores
        sections["personas"].avg_field_score = pe_avg
        sections["personas"].field_completion_rates = pe_rates
    except Exception:
        pass

    # Mappings (required)
    m_total, m_valid, m_issues, m_missing, m_required, m_missing_map, m_blank_cnt, m_blank_map = _validate_list(mappings, PersonaWithMappings)
    sections["personas_with_mappings"] = PipelineSectionReport(
        name="personas_with_mappings",
        required=True,
        present=len(mappings) > 0,
        total_items=m_total,
        valid_items=m_valid,
        missing_required_errors=m_missing,
        completeness_ratio=_ratio(m_valid, m_total),
        errors=m_issues,
        required_fields=m_required,
        field_missing_counts=m_missing_map,
        blank_required_errors=m_blank_cnt,
        field_blank_counts=m_blank_map,
    )

    # Field completeness scores for mappings
    try:
        m_scores, m_avg, m_rates = _compute_section_field_scores(mappings, PersonaWithMappings)
        sections["personas_with_mappings"].item_field_scores = m_scores
        sections["personas_with_mappings"].avg_field_score = m_avg
        sections["personas_with_mappings"].field_completion_rates = m_rates
    except Exception:
        pass

    # Sequences (optional)
    if sequences is not None:
        s_total, s_valid, s_issues, s_missing, s_required, s_missing_map, s_blank_cnt, s_blank_map = _validate_list(sequences, OutreachSequence)

        # Soft checks that complement model validation
        for idx, seq in enumerate(sequences or []):
            try:
                total_touches = seq.get("total_touches")
                touches = seq.get("touches") or []
                if total_touches is not None and isinstance(total_touches, int):
                    if total_touches != len(touches):
                        s_issues.append(PipelineCompletenessIssue(
                            path=f"sequences[{idx}].total_touches",
                            message=f"total_touches ({total_touches}) does not match touches length ({len(touches)})",
                            type="value_error.mismatch",
                        ))

                if touches:
                    prev_order = 0
                    for t in touches:
                        so = t.get("sort_order", 0)
                        if so != prev_order + 1:
                            s_issues.append(PipelineCompletenessIssue(
                                path=f"sequences[{idx}].touches[{so}]",
                                message="sort_order must be sequential starting from 1",
                                type="value_error",
                            ))
                            break
                        prev_order = so
            except Exception:
                pass

        sections["sequences"] = PipelineSectionReport(
            name="sequences",
            required=False,
            present=len(sequences) > 0,
            total_items=s_total,
            valid_items=s_valid,
            missing_required_errors=s_missing,
            completeness_ratio=_ratio(s_valid, s_total),
            errors=s_issues,
            required_fields=s_required,
            field_missing_counts=s_missing_map,
            blank_required_errors=s_blank_cnt,
            field_blank_counts=s_blank_map,
        )

        # Field completeness scores for sequences
        try:
            s_scores, s_avg, s_rates = _compute_section_field_scores(sequences, OutreachSequence)
            sections["sequences"].item_field_scores = s_scores
            sections["sequences"].avg_field_score = s_avg
            sections["sequences"].field_completion_rates = s_rates
        except Exception:
            pass

    # Cross-component checks
    cross_issues: List[PipelineCompletenessIssue] = []

    persona_names_from_personas = {p.get("persona_name") for p in personas if isinstance(p, dict) and p.get("persona_name")}
    mapping_persona_names = {pm.get("persona_name") for pm in mappings if isinstance(pm, dict) and pm.get("persona_name")}

    # mapping.persona_name must exist in personas
    for name in mapping_persona_names:
        if name not in persona_names_from_personas:
            cross_issues.append(PipelineCompletenessIssue(
                path="personas_with_mappings.*.persona_name",
                message=f"persona_name '{name}' not found in personas",
                type="value_error.reference",
            ))

    # sequence.persona_name must exist in personas (if sequences present)
    if sequences is not None:
        for idx, seq in enumerate(sequences or []):
            name = seq.get("persona_name")
            if name and name not in persona_names_from_personas:
                cross_issues.append(PipelineCompletenessIssue(
                    path=f"sequences[{idx}].persona_name",
                    message=f"persona_name '{name}' not found in personas",
                    type="value_error.reference",
                ))

    # Unique persona names in personas
    def _names(iterable):
        return [p.get("persona_name") for p in iterable if isinstance(p, dict) and p.get("persona_name")]

    unique_ok, dups = _unique_names(_names(personas))
    if not unique_ok:
        for dup in dups:
            cross_issues.append(PipelineCompletenessIssue(
                path="personas.*.persona_name",
                message=f"Duplicate persona_name '{dup}'",
                type="value_error.duplicate",
            ))

    cross_component = CrossComponentCheck(
        passed=len(cross_issues) == 0,
        issues=cross_issues,
    )

    required_sections = ["products", "personas", "personas_with_mappings"]
    required_present = {k: sections[k].present for k in required_sections}

    # Scores
    req_ratios = [sections[k].completeness_ratio for k in required_sections]
    score_required_only = round(sum(req_ratios) / len(req_ratios), 4)

    opt_ratios = req_ratios[:]
    if "sequences" in sections:
        opt_ratios.append(sections["sequences"].completeness_ratio)
    score_including_optional = round(sum(opt_ratios) / len(opt_ratios), 4)

    # Overall completeness
    is_complete = (
        all(required_present.values())
        and all(r == 1.0 for r in req_ratios)
        and cross_component.passed
    )

    return PipelineCompletenessReport(
        is_complete=is_complete,
        required_sections_present=required_present,
        sections=sections,
        cross_component=cross_component,
        score_required_only=score_required_only,
        score_including_optional=score_including_optional,
    )


