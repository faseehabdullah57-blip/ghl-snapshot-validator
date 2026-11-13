"""
CLI Entrypoint for `ghl-snapshot-validator`.

Audits single or multiple GoHighLevel (GHL) sub-accounts against a master
agency snapshot blueprint (`schemas/master_agency_blueprint.json`), catching
silent configuration drift across Custom Fields (with dropdown option diffing),
Pipelines/Stages, Tags, Custom Values (with blank/placeholder detection), and
Workflows (`published` vs `draft`), with optional `--auto-fix` remediation and
Markdown client QA handoff report generation (`--report-out`).

Usage Examples:
    python -m src.cli.main --mock
    python -m src.cli.main --mock --auto-fix --report-out qa_handoff.md
    python -m src.cli.main --locations-file schemas/sample_locations.json --mock --auto-fix
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

# Ensure project root is on sys.path when invoked directly as `python src/cli/main.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover

    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


from src.services.ghl_audit_client import GHLAPIError, GHLAuditClient
from src.utils.reporter import AuditReporter
from src.validators.field_validator import AuditResult, FieldValidator
from src.validators.pipeline_validator import PipelineValidator
from src.validators.workflow_validator import WorkflowValidator


DEFAULT_SCHEMA_PATH = "schemas/master_agency_blueprint.json"


def build_parser() -> argparse.ArgumentParser:
    """Configure and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ghl-snapshot-validator",
        description=(
            "Audit one or more GoHighLevel (GHL) sub-accounts against a master "
            "agency snapshot blueprint schema and optionally remediate drift."
        ),
    )
    parser.add_argument(
        "--location-id",
        dest="location_id",
        default=None,
        help="GoHighLevel Sub-Account Location ID (falls back to GHL_LOCATION_ID env var).",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help="GoHighLevel API v2 Private Integration / Bearer Token (falls back to GHL_API_KEY env var).",
    )
    parser.add_argument(
        "--locations-file",
        dest="locations_file",
        default=None,
        help="Path to JSON file containing multiple sub-account locations for batch agency auditing.",
    )
    parser.add_argument(
        "--schema-file",
        dest="schema_file",
        default=None,
        help=f"Path to master snapshot blueprint JSON (default: {DEFAULT_SCHEMA_PATH}).",
    )
    parser.add_argument(
        "--auto-fix",
        dest="auto_fix",
        action="store_true",
        default=False,
        help="Automatically create missing tags, custom fields, and custom values via GHL API v2 POST requests.",
    )
    parser.add_argument(
        "--mock",
        dest="mock",
        action="store_true",
        default=False,
        help="Run against built-in simulated sub-account state(s) with intentional drift without live GHL credentials.",
    )
    parser.add_argument(
        "--report-out",
        dest="report_out",
        default=None,
        help="Export a clean Markdown client QA handoff report to the specified file path.",
    )
    return parser


def resolve_project_file(file_path: str) -> Path:
    """Resolve a file path relative to CWD or project root."""
    candidate = Path(file_path)
    if candidate.is_file():
        return candidate

    root_candidate = PROJECT_ROOT / file_path
    if root_candidate.is_file():
        return root_candidate

    raise FileNotFoundError(
        f"File not found at '{file_path}' or '{root_candidate}'."
    )


def load_blueprint_schema(schema_file: str = DEFAULT_SCHEMA_PATH) -> Dict[str, Any]:
    """Load and parse the master agency blueprint JSON schema."""
    resolved = resolve_project_file(schema_file)
    with resolved.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_locations_file(locations_file: str) -> List[Dict[str, str]]:
    """
    Load and normalize a batch locations JSON file into a list of
    `{"locationId": "...", "name": "..."}` dicts.
    """
    resolved = resolve_project_file(locations_file)
    with resolved.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    raw_list = (
        payload.get("locations", [])
        if isinstance(payload, dict)
        else (payload if isinstance(payload, list) else [])
    )

    normalized: List[Dict[str, str]] = []
    for item in raw_list:
        if isinstance(item, str) and item.strip():
            normalized.append({"locationId": item.strip(), "name": item.strip()})
        elif isinstance(item, dict):
            loc_id = str(
                item.get("locationId") or item.get("id") or ""
            ).strip()
            loc_name = str(item.get("name") or loc_id).strip()
            if loc_id:
                normalized.append({"locationId": loc_id, "name": loc_name})

    if not normalized:
        raise ValueError(f"No valid locations found in '{locations_file}'.")
    return normalized


def execute_snapshot_audit(
    blueprint: Dict[str, Any],
    client: GHLAuditClient,
    *,
    auto_fix: bool = False,
) -> List[AuditResult]:
    """
    Execute all field, dropdown option, pipeline, tag, custom value, and
    workflow validations against the sub-account state returned by `client`.
    """
    live_state = client.fetch_all_snapshot_data()

    field_validator = FieldValidator(
        blueprint=blueprint,
        client=client,
        auto_fix=auto_fix,
    )
    pipeline_validator = PipelineValidator(blueprint=blueprint)
    workflow_validator = WorkflowValidator(blueprint=blueprint)

    results: List[AuditResult] = []
    results.extend(
        field_validator.validate_custom_fields(
            blueprint.get("customFields", []),
            live_state.get("customFields", []),
        )
    )
    results.extend(
        pipeline_validator.validate_pipelines(
            blueprint.get("pipelines", []),
            live_state.get("pipelines", []),
        )
    )
    results.extend(
        field_validator.validate_tags(
            blueprint.get("tags", []),
            live_state.get("tags", []),
        )
    )
    results.extend(
        field_validator.validate_custom_values(
            blueprint.get("customValues", []),
            live_state.get("customValues", []),
        )
    )
    if "workflows" in blueprint:
        results.extend(
            workflow_validator.validate_workflows(
                blueprint.get("workflows", []),
                live_state.get("workflows", []),
            )
        )
    return results


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    client: Optional[GHLAuditClient] = None,
    console: Optional[Any] = None,
) -> int:
    """
    Main CLI entrypoint.
    Returns:
        0 if all checks across all audited locations pass (or are resolved via `--auto-fix`)
        1 if any discrepancies remain or a configuration/API error occurs
    """
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    location_id = args.location_id or os.getenv("GHL_LOCATION_ID", "").strip()
    api_key = args.api_key or os.getenv("GHL_API_KEY", "").strip()
    schema_file = (
        args.schema_file
        or os.getenv("GHL_SCHEMA_FILE", "").strip()
        or DEFAULT_SCHEMA_PATH
    )

    try:
        blueprint = load_blueprint_schema(schema_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Failed to load blueprint schema: {exc}", file=sys.stderr)
        return 1

    # Determine target location(s)
    target_locations: List[Dict[str, Optional[str]]] = []
    if args.locations_file:
        try:
            loaded_locs = load_locations_file(args.locations_file)
            for entry in loaded_locs:
                target_locations.append(
                    {"locationId": entry["locationId"], "name": entry.get("name")}
                )
        except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError) as exc:
            print(f"ERROR: Failed to load locations file: {exc}", file=sys.stderr)
            return 1
    else:
        if args.mock and not location_id:
            location_id = (
                client.location_id if client is not None else "mock-subaccount-loc-001"
            )
        if not args.mock and client is None and (not location_id or not api_key):
            print(
                "ERROR: Missing required GHL credentials. Provide --location-id and "
                "--api-key (or set GHL_LOCATION_ID and GHL_API_KEY in .env), or pass "
                "--mock to run against the built-in simulated sub-account.",
                file=sys.stderr,
            )
            return 1
        target_locations.append({"locationId": location_id, "name": None})

    if not args.mock and client is None and not api_key:
        print(
            "ERROR: Missing GHL_API_KEY / --api-key for live sub-account audit.",
            file=sys.stderr,
        )
        return 1

    reporter = AuditReporter(console=console)
    schema_basename = Path(schema_file).name
    location_reports: List[Dict[str, Any]] = []

    for loc_entry in target_locations:
        loc_id = str(loc_entry["locationId"] or "mock-subaccount-loc-001")
        loc_name = loc_entry.get("name")

        active_client = client or GHLAuditClient(
            api_key=api_key,
            location_id=loc_id,
            mock=args.mock,
        )

        try:
            results = execute_snapshot_audit(
                blueprint=blueprint,
                client=active_client,
                auto_fix=args.auto_fix,
            )
        except GHLAPIError as exc:
            print(f"ERROR auditing location '{loc_id}': {exc}", file=sys.stderr)
            return 1

        summary = reporter.render(
            results,
            location_id=loc_id,
            location_name=loc_name,
            schema_name=schema_basename,
            auto_fix=args.auto_fix,
            mock=args.mock,
        )
        location_reports.append(
            {
                "location_id": loc_id,
                "location_name": loc_name,
                "results": results,
                "summary": summary,
            }
        )

    scoreboard_summary = reporter.render_agency_scoreboard(
        location_reports,
        schema_name=schema_basename,
        auto_fix=args.auto_fix,
        mock=args.mock,
    )

    if args.report_out:
        try:
            reporter.export_markdown_report(
                args.report_out,
                location_reports,
                schema_name=schema_basename,
                auto_fix=args.auto_fix,
                mock=args.mock,
            )
        except OSError as exc:
            print(
                f"ERROR: Failed to write Markdown report to '{args.report_out}': {exc}",
                file=sys.stderr,
            )
            return 1

    return scoreboard_summary["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
