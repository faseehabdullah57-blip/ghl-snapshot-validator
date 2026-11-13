"""
Field, Dropdown Option, Tag, and Custom Value Validators for GoHighLevel Audits.

Compares live (or simulated) sub-account state against `master_agency_blueprint.json`:
  - Custom field presence, `dataType`, and `model` (`contact` vs `opportunity`)
  - Dropdown Option Diffing (`SINGLE_OPTIONS` / `MULTIPLE_OPTIONS` missing choices)
  - Blank Custom Value & Unresolved Placeholder (`{{...}}`, `TODO`) detection
  - Required agency segmentation tags
  - Optional `--auto-fix` remediation via `GHLAuditClient` POST endpoints
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, List, Optional, Sequence, Union


PLACEHOLDER_PATTERN = re.compile(
    r"(\{\{.*?\}\}|\bTODO\b|\bTBD\b|\bCHANGEME\b|\bFIXME\b|\bPLACEHOLDER\b)",
    re.IGNORECASE,
)


@dataclass
class AuditResult:
    """Represents a single resource audit check result."""

    resource_type: str
    resource_name: str
    expected: str
    actual: str
    status: str  # "PASS", "FAIL", or "FIXED"
    fixable: bool = False
    issue_type: Optional[str] = None
    field_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_key(raw_key: Optional[str]) -> str:
    """Normalize GHL fieldKey strings (stripping {{ }} braces and whitespace)."""
    if not raw_key:
        return ""
    cleaned = raw_key.strip()
    if cleaned.startswith("{{") and cleaned.endswith("}}"):
        cleaned = cleaned[2:-2].strip()
    return cleaned.lower()


def _normalize_custom_value_key(raw_key: Optional[str]) -> str:
    """
    Normalize custom value keys so both `custom_values.agency_calendar_link`
    and `agency_calendar_link` resolve to the same canonical lookup key.
    """
    norm = _normalize_key(raw_key)
    if norm.startswith("custom_values."):
        return norm[len("custom_values.") :]
    return norm


def _extract_option_labels(raw_options: Any) -> List[str]:
    """Extract string option labels from GHL custom field `options` payload."""
    if not raw_options or not isinstance(raw_options, (list, tuple)):
        return []
    extracted: List[str] = []
    for item in raw_options:
        if isinstance(item, str):
            val = item.strip()
            if val:
                extracted.append(val)
        elif isinstance(item, dict):
            label = (
                item.get("label")
                or item.get("name")
                or item.get("value")
                or ""
            )
            val = str(label).strip()
            if val:
                extracted.append(val)
    return extracted


def _has_unresolved_placeholder(value: str) -> bool:
    """Return True if a custom value contains unresolved {{...}} or TODO placeholders."""
    return bool(PLACEHOLDER_PATTERN.search(value))


class FieldValidator:
    """
    Validates GoHighLevel Custom Fields (including dropdown options), Tags,
    and Custom Values (including blank/placeholder detection) against the
    master agency blueprint schema.
    """

    OPTION_DATA_TYPES = {"SINGLE_OPTIONS", "MULTIPLE_OPTIONS", "RADIO", "CHECKBOX"}

    def __init__(
        self,
        blueprint: Optional[Dict[str, Any]] = None,
        client: Optional[Any] = None,
        auto_fix: bool = False,
    ) -> None:
        self.blueprint = blueprint or {}
        self.client = client
        self.auto_fix = auto_fix

    def validate_custom_fields(
        self,
        expected_fields: Optional[Sequence[Dict[str, Any]]] = None,
        actual_fields: Optional[Sequence[Dict[str, Any]]] = None,
        *,
        client: Optional[Any] = None,
        auto_fix: Optional[bool] = None,
    ) -> List[AuditResult]:
        """
        Compare expected custom fields against actual sub-account custom fields.
        Detects:
          - Missing custom fields (`MISSING_CUSTOM_FIELD`)
          - `dataType` mismatches (`DATATYPE_MISMATCH`)
          - `model` mismatches (`MODEL_MISMATCH`)
          - Missing dropdown options (`MISSING_FIELD_OPTIONS`) on SINGLE_OPTIONS / MULTIPLE_OPTIONS fields
        """
        exp_list = (
            list(expected_fields)
            if expected_fields is not None
            else list(self.blueprint.get("customFields", []))
        )
        act_list = list(actual_fields or [])
        active_client = client if client is not None else self.client
        should_fix = self.auto_fix if auto_fix is None else auto_fix

        by_key: Dict[str, Dict[str, Any]] = {}
        by_name_model: Dict[tuple[str, str], Dict[str, Any]] = {}
        by_name: Dict[str, Dict[str, Any]] = {}

        for item in act_list:
            key = _normalize_key(item.get("fieldKey"))
            if key:
                by_key[key] = item
            name_norm = str(item.get("name", "")).strip().lower()
            model_norm = str(item.get("model", "contact")).strip().lower()
            if name_norm:
                by_name_model[(name_norm, model_norm)] = item
                by_name[name_norm] = item

        results: List[AuditResult] = []

        for exp in exp_list:
            name = str(exp.get("name", "Unnamed Field")).strip()
            field_key = str(exp.get("fieldKey", "")).strip()
            exp_type = str(exp.get("dataType", "TEXT")).strip().upper()
            exp_model = str(exp.get("model", "contact")).strip().lower()
            exp_options = _extract_option_labels(exp.get("options"))
            display_name = f"{name} ({field_key})" if field_key else name

            if exp_options:
                expected_desc = (
                    f"dataType={exp_type}, model={exp_model}, "
                    f"options={exp_options}"
                )
            else:
                expected_desc = f"dataType={exp_type}, model={exp_model}"

            norm_key = _normalize_key(field_key)
            matched = (
                by_key.get(norm_key)
                or by_name_model.get((name.lower(), exp_model))
                or by_name.get(name.lower())
            )

            if matched is None:
                if should_fix and active_client is not None:
                    active_client.create_custom_field(exp)
                    results.append(
                        AuditResult(
                            resource_type="Custom Field",
                            resource_name=display_name,
                            expected=expected_desc,
                            actual=f"Created via Auto-Fix ({exp_type}, {exp_model})",
                            status="FIXED",
                            fixable=True,
                            issue_type="MISSING_CUSTOM_FIELD",
                            field_key=field_key,
                            metadata=dict(exp),
                        )
                    )
                else:
                    results.append(
                        AuditResult(
                            resource_type="Custom Field",
                            resource_name=display_name,
                            expected=expected_desc,
                            actual="Missing",
                            status="FAIL",
                            fixable=True,
                            issue_type="MISSING_CUSTOM_FIELD",
                            field_key=field_key,
                            metadata=dict(exp),
                        )
                    )
                continue

            act_type = str(matched.get("dataType", "")).strip().upper()
            act_model = str(matched.get("model", exp_model)).strip().lower()
            act_options = _extract_option_labels(
                matched.get("options") or matched.get("picklistOptions")
            )

            if act_type != exp_type:
                results.append(
                    AuditResult(
                        resource_type="Custom Field",
                        resource_name=display_name,
                        expected=expected_desc,
                        actual=f"dataType={act_type}, model={act_model} [TYPE MISMATCH]",
                        status="FAIL",
                        fixable=False,
                        issue_type="DATATYPE_MISMATCH",
                        field_key=field_key,
                        metadata=dict(exp),
                    )
                )
                continue

            if act_model != exp_model:
                results.append(
                    AuditResult(
                        resource_type="Custom Field",
                        resource_name=display_name,
                        expected=expected_desc,
                        actual=f"dataType={act_type}, model={act_model} [MODEL MISMATCH]",
                        status="FAIL",
                        fixable=False,
                        issue_type="MODEL_MISMATCH",
                        field_key=field_key,
                        metadata=dict(exp),
                    )
                )
                continue

            # Dropdown Option Diffing for SINGLE_OPTIONS / MULTIPLE_OPTIONS fields
            if exp_options and (exp_type in self.OPTION_DATA_TYPES or exp_options):
                act_options_lower = {opt.lower() for opt in act_options}
                missing_options = [
                    opt for opt in exp_options if opt.lower() not in act_options_lower
                ]
                if missing_options:
                    results.append(
                        AuditResult(
                            resource_type="Custom Field",
                            resource_name=display_name,
                            expected=expected_desc,
                            actual=(
                                f"options={act_options} "
                                f"[MISSING OPTIONS: {missing_options}]"
                            ),
                            status="FAIL",
                            fixable=False,
                            issue_type="MISSING_FIELD_OPTIONS",
                            field_key=field_key,
                            metadata={
                                **dict(exp),
                                "missing_options": missing_options,
                                "actual_options": act_options,
                            },
                        )
                    )
                    continue

            actual_desc = (
                f"dataType={act_type}, model={act_model}, options={act_options}"
                if exp_options
                else f"dataType={act_type}, model={act_model}"
            )
            results.append(
                AuditResult(
                    resource_type="Custom Field",
                    resource_name=display_name,
                    expected=expected_desc,
                    actual=actual_desc,
                    status="PASS",
                    fixable=False,
                    issue_type=None,
                    field_key=field_key,
                    metadata=dict(exp),
                )
            )

        return results

    def validate_tags(
        self,
        expected_tags: Optional[Sequence[Union[str, Dict[str, Any]]]] = None,
        actual_tags: Optional[Sequence[Union[str, Dict[str, Any]]]] = None,
        *,
        client: Optional[Any] = None,
        auto_fix: Optional[bool] = None,
    ) -> List[AuditResult]:
        """
        Compare required agency tags against actual sub-account tags.
        Supports both string lists and GHL tag object lists `[{"name": "..."}]`.
        """
        exp_raw = (
            list(expected_tags)
            if expected_tags is not None
            else list(self.blueprint.get("tags", []))
        )
        act_raw = list(actual_tags or [])
        active_client = client if client is not None else self.client
        should_fix = self.auto_fix if auto_fix is None else auto_fix

        actual_tag_names: set[str] = set()
        for item in act_raw:
            if isinstance(item, str):
                actual_tag_names.add(item.strip().lower())
            elif isinstance(item, dict) and "name" in item:
                actual_tag_names.add(str(item["name"]).strip().lower())

        results: List[AuditResult] = []
        for tag_entry in exp_raw:
            tag_name = (
                tag_entry.strip()
                if isinstance(tag_entry, str)
                else str(tag_entry.get("name", "")).strip()
            )
            if not tag_name:
                continue

            if tag_name.lower() in actual_tag_names:
                results.append(
                    AuditResult(
                        resource_type="Tag",
                        resource_name=tag_name,
                        expected="Present",
                        actual="Present",
                        status="PASS",
                        fixable=False,
                        issue_type=None,
                        metadata={"name": tag_name},
                    )
                )
            else:
                if should_fix and active_client is not None:
                    active_client.create_tag(tag_name)
                    results.append(
                        AuditResult(
                            resource_type="Tag",
                            resource_name=tag_name,
                            expected="Present",
                            actual="Created via Auto-Fix (POST /tags)",
                            status="FIXED",
                            fixable=True,
                            issue_type="MISSING_TAG",
                            metadata={"name": tag_name},
                        )
                    )
                else:
                    results.append(
                        AuditResult(
                            resource_type="Tag",
                            resource_name=tag_name,
                            expected="Present",
                            actual="Missing",
                            status="FAIL",
                            fixable=True,
                            issue_type="MISSING_TAG",
                            metadata={"name": tag_name},
                        )
                    )

        return results

    def validate_custom_values(
        self,
        expected_values: Optional[Sequence[Dict[str, Any]]] = None,
        actual_values: Optional[Sequence[Dict[str, Any]]] = None,
        *,
        client: Optional[Any] = None,
        auto_fix: Optional[bool] = None,
    ) -> List[AuditResult]:
        """
        Compare required custom values against actual sub-account custom values.
        Detects:
          - Missing custom values (`MISSING_CUSTOM_VALUE`)
          - Blank/empty custom values (`BLANK_CUSTOM_VALUE`) when `requireNonEmpty` is True
          - Unresolved `{{...}}` or `TODO` placeholder strings (`UNRESOLVED_PLACEHOLDER_VALUE`)
        """
        exp_list = (
            list(expected_values)
            if expected_values is not None
            else list(self.blueprint.get("customValues", []))
        )
        act_list = list(actual_values or [])
        active_client = client if client is not None else self.client
        should_fix = self.auto_fix if auto_fix is None else auto_fix

        by_key: Dict[str, Dict[str, Any]] = {}
        by_short_key: Dict[str, Dict[str, Any]] = {}
        by_name: Dict[str, Dict[str, Any]] = {}

        for item in act_list:
            key = _normalize_key(item.get("fieldKey"))
            short_key = _normalize_custom_value_key(item.get("fieldKey"))
            if key:
                by_key[key] = item
            if short_key:
                by_short_key[short_key] = item
            name_norm = str(item.get("name", "")).strip().lower()
            if name_norm:
                by_name[name_norm] = item

        results: List[AuditResult] = []
        for exp in exp_list:
            name = str(exp.get("name", "Unnamed Custom Value")).strip()
            field_key = str(exp.get("fieldKey", "")).strip()
            require_non_empty = bool(exp.get("requireNonEmpty", True))
            display_name = f"{name} ({field_key})" if field_key else name
            expected_desc = (
                f"fieldKey={field_key} (non-empty)"
                if require_non_empty and field_key
                else (f"fieldKey={field_key}" if field_key else "Present (non-empty)")
            )

            norm_key = _normalize_key(field_key)
            short_key = _normalize_custom_value_key(field_key)
            matched = (
                by_key.get(norm_key)
                or by_short_key.get(short_key)
                or by_name.get(name.lower())
            )

            if matched is None:
                if should_fix and active_client is not None:
                    active_client.create_custom_value(exp)
                    results.append(
                        AuditResult(
                            resource_type="Custom Value",
                            resource_name=display_name,
                            expected=expected_desc,
                            actual="Created via Auto-Fix (POST /customValues)",
                            status="FIXED",
                            fixable=True,
                            issue_type="MISSING_CUSTOM_VALUE",
                            field_key=field_key,
                            metadata=dict(exp),
                        )
                    )
                else:
                    results.append(
                        AuditResult(
                            resource_type="Custom Value",
                            resource_name=display_name,
                            expected=expected_desc,
                            actual="Missing",
                            status="FAIL",
                            fixable=True,
                            issue_type="MISSING_CUSTOM_VALUE",
                            field_key=field_key,
                            metadata=dict(exp),
                        )
                    )
                continue

            # Check for Blank / Empty Value or Unresolved Placeholders ({{...}} / TODO)
            raw_val = matched.get("value")
            str_val = "" if raw_val is None else str(raw_val).strip()

            if require_non_empty and not str_val:
                results.append(
                    AuditResult(
                        resource_type="Custom Value",
                        resource_name=display_name,
                        expected=expected_desc,
                        actual='value="" [BLANK / EMPTY]',
                        status="FAIL",
                        fixable=False,
                        issue_type="BLANK_CUSTOM_VALUE",
                        field_key=field_key,
                        metadata=dict(exp),
                    )
                )
                continue

            if require_non_empty and _has_unresolved_placeholder(str_val):
                results.append(
                    AuditResult(
                        resource_type="Custom Value",
                        resource_name=display_name,
                        expected=expected_desc,
                        actual=f'value="{str_val}" [UNRESOLVED PLACEHOLDER]',
                        status="FAIL",
                        fixable=False,
                        issue_type="UNRESOLVED_PLACEHOLDER_VALUE",
                        field_key=field_key,
                        metadata=dict(exp),
                    )
                )
                continue

            act_key = str(matched.get("fieldKey", field_key)).strip()
            results.append(
                AuditResult(
                    resource_type="Custom Value",
                    resource_name=display_name,
                    expected=expected_desc,
                    actual=f'fieldKey={act_key}, value="{str_val}"'
                    if str_val
                    else f"fieldKey={act_key}",
                    status="PASS",
                    fixable=False,
                    issue_type=None,
                    field_key=field_key,
                    metadata=dict(exp),
                )
            )

        return results

    def validate_all(
        self,
        live_data: Dict[str, Any],
        *,
        client: Optional[Any] = None,
        auto_fix: Optional[bool] = None,
    ) -> List[AuditResult]:
        """Run custom field, tag, and custom value validations together."""
        results: List[AuditResult] = []
        results.extend(
            self.validate_custom_fields(
                self.blueprint.get("customFields", []),
                live_data.get("customFields", []),
                client=client,
                auto_fix=auto_fix,
            )
        )
        results.extend(
            self.validate_tags(
                self.blueprint.get("tags", []),
                live_data.get("tags", []),
                client=client,
                auto_fix=auto_fix,
            )
        )
        results.extend(
            self.validate_custom_values(
                self.blueprint.get("customValues", []),
                live_data.get("customValues", []),
                client=client,
                auto_fix=auto_fix,
            )
        )
        return results


def validate_custom_fields(
    expected_fields: Sequence[Dict[str, Any]],
    actual_fields: Sequence[Dict[str, Any]],
    client: Optional[Any] = None,
    auto_fix: bool = False,
) -> List[AuditResult]:
    """Module-level convenience wrapper for custom field validation."""
    return FieldValidator(client=client, auto_fix=auto_fix).validate_custom_fields(
        expected_fields, actual_fields
    )


def validate_tags(
    expected_tags: Sequence[Union[str, Dict[str, Any]]],
    actual_tags: Sequence[Union[str, Dict[str, Any]]],
    client: Optional[Any] = None,
    auto_fix: bool = False,
) -> List[AuditResult]:
    """Module-level convenience wrapper for tag validation."""
    return FieldValidator(client=client, auto_fix=auto_fix).validate_tags(
        expected_tags, actual_tags
    )


def validate_custom_values(
    expected_values: Sequence[Dict[str, Any]],
    actual_values: Sequence[Dict[str, Any]],
    client: Optional[Any] = None,
    auto_fix: bool = False,
) -> List[AuditResult]:
    """Module-level convenience wrapper for custom value validation."""
    return FieldValidator(client=client, auto_fix=auto_fix).validate_custom_values(
        expected_values, actual_values
    )
