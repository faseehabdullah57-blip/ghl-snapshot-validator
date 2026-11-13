"""
Comprehensive Automated Test Suite for `ghl-snapshot-validator`.

Covers:
  1. Custom field `dataType` and `model` mismatch detection
  2. Dropdown Option Diffing (`SINGLE_OPTIONS` missing choices like `"Enterprise"`)
  3. Blank Custom Value (`""`) & Unresolved Placeholder (`{{...}}`, `TODO`) detection
  4. Workflow publication validation (`draft` vs `published` and missing workflows)
  5. Opportunity pipeline presence and stage ordering drift checks
  6. Missing agency tag detection
  7. `--auto-fix` GHL API v2 POST remediation calls & HTTP 429 retry/backoff
  8. Multi-location batch agency audits (`--locations-file`) & Agency Health Scoreboard
  9. Markdown client QA handoff report export (`--report-out`)
  10. CLI exit codes (`0` when compliant or resolved via `--auto-fix`, `1` when drift remains)
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Dict
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pytest  # type: ignore

    PYTEST_AVAILABLE = True
except ImportError:  # pragma: no cover
    PYTEST_AVAILABLE = False

    class _FallbackMonkeyPatch:
        def delenv(self, name: str, raising: bool = True) -> None:
            if name in os.environ:
                del os.environ[name]
            elif raising:
                raise KeyError(name)

    class _FallbackPytest:
        MonkeyPatch = _FallbackMonkeyPatch

        @staticmethod
        def fixture(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

    pytest = _FallbackPytest()  # type: ignore

from src.cli.main import load_blueprint_schema, main
from src.services.ghl_audit_client import (
    COMPLIANT_MOCK_SUBACCOUNT_STATE,
    GHLAuditClient,
)
from src.validators.field_validator import (
    FieldValidator,
    validate_custom_fields,
    validate_custom_values,
    validate_tags,
)
from src.validators.pipeline_validator import PipelineValidator, validate_pipelines
from src.validators.workflow_validator import WorkflowValidator, validate_workflows


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def master_blueprint() -> Dict[str, Any]:
    """Load the canonical master_agency_blueprint.json schema."""
    return load_blueprint_schema("schemas/master_agency_blueprint.json")


@pytest.fixture
def compliant_subaccount_state() -> Dict[str, Any]:
    """Return a 100% compliant sub-account state matching master_agency_blueprint.json."""
    return copy.deepcopy(COMPLIANT_MOCK_SUBACCOUNT_STATE)


# =============================================================================
# 1. Custom Field & Dropdown Option Diffing Tests
# =============================================================================


def test_custom_field_datatype_mismatch_detected() -> None:
    """Detect when a live custom field has a mismatched dataType (e.g. TEXT vs NUMERICAL)."""
    expected = [
        {
            "name": "Lead Score",
            "fieldKey": "contact.lead_score",
            "dataType": "NUMERICAL",
            "model": "contact",
        }
    ]
    actual = [
        {
            "id": "cf_1",
            "name": "Lead Score",
            "fieldKey": "contact.lead_score",
            "dataType": "TEXT",
            "model": "contact",
        }
    ]

    results = validate_custom_fields(expected, actual)
    assert len(results) == 1
    assert results[0].status == "FAIL"
    assert results[0].issue_type == "DATATYPE_MISMATCH"
    assert results[0].fixable is False


def test_dropdown_option_diffing_detects_missing_choices() -> None:
    """
    Detect when a SINGLE_OPTIONS custom field is missing required dropdown
    options (e.g., missing 'Enterprise' in contact.subscription_tier).
    """
    expected = [
        {
            "name": "Subscription Tier",
            "fieldKey": "contact.subscription_tier",
            "dataType": "SINGLE_OPTIONS",
            "model": "contact",
            "options": ["Starter", "Growth", "Enterprise"],
        }
    ]
    actual = [
        {
            "id": "cf_tier",
            "name": "Subscription Tier",
            "fieldKey": "contact.subscription_tier",
            "dataType": "SINGLE_OPTIONS",
            "model": "contact",
            "options": ["Starter", "Growth"],  # Missing "Enterprise"
        }
    ]

    results = validate_custom_fields(expected, actual)
    assert len(results) == 1
    res = results[0]
    assert res.status == "FAIL"
    assert res.issue_type == "MISSING_FIELD_OPTIONS"
    assert "Enterprise" in res.actual
    assert res.metadata["missing_options"] == ["Enterprise"]


def test_custom_field_missing_and_model_mismatch() -> None:
    """Detect missing custom fields and model mismatches (contact vs opportunity)."""
    expected = [
        {
            "name": "Onboarding Kickoff Date",
            "fieldKey": "contact.onboarding_kickoff_date",
            "dataType": "DATE",
            "model": "contact",
        },
        {
            "name": "Projected MRR",
            "fieldKey": "opportunity.projected_mrr",
            "dataType": "NUMERICAL",
            "model": "opportunity",
        },
    ]
    actual = [
        {
            "id": "cf_mrr",
            "name": "Projected MRR",
            "fieldKey": "opportunity.projected_mrr",
            "dataType": "NUMERICAL",
            "model": "contact",  # Drift: expected opportunity
        }
    ]

    results = validate_custom_fields(expected, actual)
    assert len(results) == 2
    assert results[0].status == "FAIL"
    assert results[0].issue_type == "MISSING_CUSTOM_FIELD"
    assert results[1].status == "FAIL"
    assert results[1].issue_type == "MODEL_MISMATCH"


# =============================================================================
# 2. Blank Custom Value & Placeholder Detection Tests
# =============================================================================


def test_blank_and_placeholder_custom_values_detected() -> None:
    """
    Flag custom values that are blank/whitespace (`""`), contain unresolved
    `{{...}}` handlebars or `TODO` placeholders, or are completely missing.
    """
    expected_values = [
        {
            "name": "Agency Calendar Link",
            "fieldKey": "custom_values.agency_calendar_link",
            "requireNonEmpty": True,
        },
        {
            "name": "Support Email",
            "fieldKey": "custom_values.support_email",
            "requireNonEmpty": True,
        },
        {
            "name": "Twilio Default Sender Number",
            "fieldKey": "custom_values.twilio_default_sender",
            "requireNonEmpty": True,
        },
        {
            "name": "Stripe Billing Portal URL",
            "fieldKey": "custom_values.stripe_billing_portal_url",
            "requireNonEmpty": True,
        },
    ]
    actual_values = [
        {
            "id": "cv1",
            "name": "Agency Calendar Link",
            "fieldKey": "custom_values.agency_calendar_link",
            "value": "   ",  # Blank / whitespace-only
        },
        {
            "id": "cv2",
            "name": "Support Email",
            "fieldKey": "support_email",  # Short key format
            "value": "TODO: configure agency support email",  # Unresolved TODO placeholder
        },
        {
            "id": "cv3",
            "name": "Twilio Default Sender Number",
            "fieldKey": "custom_values.twilio_default_sender",
            "value": "+18005550199",  # Valid non-empty
        },
        # Stripe Billing Portal URL is missing
    ]

    results = validate_custom_values(expected_values, actual_values)
    assert len(results) == 4

    assert results[0].status == "FAIL"
    assert results[0].issue_type == "BLANK_CUSTOM_VALUE"

    assert results[1].status == "FAIL"
    assert results[1].issue_type == "UNRESOLVED_PLACEHOLDER_VALUE"

    assert results[2].status == "PASS"
    assert results[2].issue_type is None

    assert results[3].status == "FAIL"
    assert results[3].issue_type == "MISSING_CUSTOM_VALUE"


# =============================================================================
# 3. Workflow Publication Status Validation Tests
# =============================================================================


def test_draft_and_missing_workflows_detected() -> None:
    """Flag workflows stuck in 'draft' status or missing altogether."""
    expected_workflows = [
        {"name": "01. Speed to Lead - Instant SMS", "expectedStatus": "published"},
        {"name": "02. Appointment Reminder Sequence", "expectedStatus": "published"},
        {"name": "03. No-Show Re-Engagement Drip", "expectedStatus": "published"},
    ]
    actual_workflows = [
        {
            "id": "wf1",
            "name": "01. Speed to Lead - Instant SMS",
            "status": "published",
        },
        {
            "id": "wf2",
            "name": "02. Appointment Reminder Sequence",
            "status": "draft",  # Stuck in draft!
        },
        # 03. No-Show Re-Engagement Drip is missing
    ]

    results = validate_workflows(expected_workflows, actual_workflows)
    assert len(results) == 3

    assert results[0].status == "PASS"
    assert results[1].status == "FAIL"
    assert results[1].issue_type == "WORKFLOW_STATUS_DRIFT"
    assert "draft" in results[1].actual

    assert results[2].status == "FAIL"
    assert results[2].issue_type == "MISSING_WORKFLOW"


# =============================================================================
# 4. Pipeline & Stage Ordering Validation Tests
# =============================================================================


def test_pipeline_stage_ordering_drift_detected() -> None:
    """Detect when pipeline stages exist but their positions/sequence are out of order."""
    expected_pipelines = [
        {
            "name": "SaaS Sales & Acquisition Pipeline",
            "stages": [
                {"name": "New Inbound Lead", "position": 0},
                {"name": "Discovery Call Booked", "position": 1},
                {"name": "Demo Completed", "position": 2},
                {"name": "Proposal Sent", "position": 3},
                {"name": "Closed Won", "position": 4},
            ],
        }
    ]
    actual_pipelines = [
        {
            "id": "pipe_1",
            "name": "SaaS Sales & Acquisition Pipeline",
            "stages": [
                {"id": "s0", "name": "New Inbound Lead", "position": 0},
                {"id": "s1", "name": "Discovery Call Booked", "position": 1},
                {"id": "s3", "name": "Proposal Sent", "position": 2},
                {"id": "s2", "name": "Demo Completed", "position": 3},
                {"id": "s4", "name": "Closed Won", "position": 4},
            ],
        }
    ]

    results = validate_pipelines(expected_pipelines, actual_pipelines)
    assert len(results) == 6
    stage_results = {r.resource_name: r for r in results[1:]}
    assert (
        stage_results["SaaS Sales & Acquisition Pipeline -> Demo Completed"].issue_type
        == "STAGE_ORDER_DRIFT"
    )
    assert (
        stage_results["SaaS Sales & Acquisition Pipeline -> Proposal Sent"].issue_type
        == "STAGE_ORDER_DRIFT"
    )


def test_missing_tag_detection() -> None:
    """Detect missing agency tags while marking existing tags as PASS."""
    expected_tags = [
        "Hot Lead",
        "Disqualified",
        "Re-Engagement Needed",
        "Onboarding Complete",
    ]
    actual_tags = [{"id": "t1", "name": "Hot Lead"}, {"id": "t2", "name": "Disqualified"}]

    results = validate_tags(expected_tags, actual_tags)
    by_name = {r.resource_name: r for r in results}
    assert by_name["Hot Lead"].status == "PASS"
    assert by_name["Re-Engagement Needed"].status == "FAIL"
    assert by_name["Re-Engagement Needed"].issue_type == "MISSING_TAG"
    assert by_name["Onboarding Complete"].status == "FAIL"


# =============================================================================
# 5. `--auto-fix` API Calls & HTTP 429 Retry Verification
# =============================================================================


@patch("src.services.ghl_audit_client.requests.post")
def test_auto_fix_triggers_ghl_api_v2_post_requests(mock_post: MagicMock) -> None:
    """
    Verify that enabling `auto_fix=True` issues POST requests to GHL API v2
    for missing tags, custom fields, and custom values with required headers.
    """
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"status": "created"}
    mock_post.return_value = mock_response

    client = GHLAuditClient(
        api_key="pit-live-token-xyz",
        location_id="loc_subaccount_999",
        mock=False,
    )

    blueprint = {
        "customFields": [
            {
                "name": "Onboarding Kickoff Date",
                "fieldKey": "contact.onboarding_kickoff_date",
                "dataType": "DATE",
                "model": "contact",
            }
        ],
        "tags": ["Onboarding Complete"],
        "customValues": [
            {
                "name": "Stripe Billing Portal URL",
                "fieldKey": "custom_values.stripe_billing_portal_url",
                "value": "https://billing.agency-ops.io/portal",
            }
        ],
    }
    empty_live_state: Dict[str, Any] = {
        "customFields": [],
        "tags": [],
        "customValues": [],
    }

    validator = FieldValidator(blueprint=blueprint, client=client, auto_fix=True)
    results = validator.validate_all(empty_live_state)

    assert len(results) == 3
    assert all(r.status == "FIXED" for r in results)
    assert mock_post.call_count == 3

    for call in mock_post.call_args_list:
        headers = call.kwargs["headers"]
        assert headers["Authorization"] == "Bearer pit-live-token-xyz"
        assert headers["Version"] == "2021-07-28"


@patch("src.services.ghl_audit_client.requests.get")
def test_ghl_client_retries_on_429_rate_limit(mock_get: MagicMock) -> None:
    """Verify GHLAuditClient retries automatically when receiving HTTP 429."""
    rate_limited_resp = MagicMock()
    rate_limited_resp.status_code = 429

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {"workflows": [{"name": "01. Speed to Lead - Instant SMS", "status": "published"}]}

    mock_get.side_effect = [rate_limited_resp, ok_resp]

    client = GHLAuditClient(
        api_key="token-123",
        location_id="loc_retry",
        max_retries=2,
        backoff_factor=0.0,
    )
    workflows = client.get_workflows()
    assert len(workflows) == 1
    assert mock_get.call_count == 2


# =============================================================================
# 6. Multi-Location Batch Audit, Markdown Export & CLI Exit Codes
# =============================================================================


def test_multi_location_batch_audit_and_markdown_export() -> None:
    """
    Verify `--locations-file schemas/sample_locations.json --mock --auto-fix --report-out`
    audits all 3 sub-accounts and exports a complete Markdown QA Handoff Report.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_file = Path(tmp_dir) / "qa_handoff_report.md"
        exit_code = main(
            [
                "--locations-file",
                "schemas/sample_locations.json",
                "--mock",
                "--auto-fix",
                "--report-out",
                str(report_file),
            ]
        )
        # Summit Roofing (loc_summit_roofing_003) has unfixable drift (draft workflow, blank CV, etc.)
        assert exit_code == 1
        assert report_file.is_file()

        content = report_file.read_text(encoding="utf-8")
        assert "## Agency Health Scoreboard" in content
        assert "loc_apex_dental_001" in content
        assert "loc_elevate_medspa_002" in content
        assert "loc_summit_roofing_003" in content
        assert "100.0%" in content


def test_cli_exit_code_0_when_subaccount_is_compliant(
    compliant_subaccount_state: Dict[str, Any],
) -> None:
    """CLI must return exit code 0 when all sub-account checks pass."""
    client = GHLAuditClient(
        api_key="mock-key",
        location_id="loc_compliant_001",
        mock=True,
        mock_state=compliant_subaccount_state,
    )
    assert main(["--mock"], client=client) == 0


def test_cli_exit_code_0_when_fixable_drift_resolved_via_auto_fix(
    compliant_subaccount_state: Dict[str, Any],
) -> None:
    """
    CLI must return exit code 0 when discrepancies consist of fixable drift
    (missing tags, missing custom fields, missing custom values) and `--auto-fix` is passed.
    """
    fixable_state = copy.deepcopy(compliant_subaccount_state)
    fixable_state["tags"] = fixable_state["tags"][:2]
    fixable_state["customFields"] = fixable_state["customFields"][1:]
    fixable_state["customValues"] = fixable_state["customValues"][1:]

    client_no_fix = GHLAuditClient(
        api_key="mock-key",
        location_id="loc_fixable_001",
        mock=True,
        mock_state=fixable_state,
    )
    assert main(["--mock"], client=client_no_fix) == 1

    client_with_fix = GHLAuditClient(
        api_key="mock-key",
        location_id="loc_fixable_001",
        mock=True,
        mock_state=fixable_state,
    )
    assert main(["--mock", "--auto-fix"], client=client_with_fix) == 0


if not PYTEST_AVAILABLE:  # pragma: no cover

    class TestGHLValidatorFallbackSuite(unittest.TestCase):
        """Fallback unittest runner when pytest is not yet installed in environment."""

        def setUp(self) -> None:
            self.compliant = copy.deepcopy(COMPLIANT_MOCK_SUBACCOUNT_STATE)

        def test_01_custom_field_datatype_mismatch(self) -> None:
            test_custom_field_datatype_mismatch_detected()

        def test_02_dropdown_option_diffing(self) -> None:
            test_dropdown_option_diffing_detects_missing_choices()

        def test_03_custom_field_missing_and_model_mismatch(self) -> None:
            test_custom_field_missing_and_model_mismatch()

        def test_04_blank_and_placeholder_custom_values(self) -> None:
            test_blank_and_placeholder_custom_values_detected()

        def test_05_draft_and_missing_workflows(self) -> None:
            test_draft_and_missing_workflows_detected()

        def test_06_pipeline_stage_ordering_drift(self) -> None:
            test_pipeline_stage_ordering_drift_detected()

        def test_07_missing_tag_detection(self) -> None:
            test_missing_tag_detection()

        def test_08_auto_fix_triggers_post_requests(self) -> None:
            test_auto_fix_triggers_ghl_api_v2_post_requests()

        def test_09_ghl_client_retries_on_429(self) -> None:
            test_ghl_client_retries_on_429_rate_limit()

        def test_10_multi_location_batch_and_markdown_export(self) -> None:
            test_multi_location_batch_audit_and_markdown_export()

        def test_11_cli_exit_code_0_when_compliant(self) -> None:
            test_cli_exit_code_0_when_subaccount_is_compliant(self.compliant)

        def test_12_cli_exit_code_0_with_auto_fix(self) -> None:
            test_cli_exit_code_0_when_fixable_drift_resolved_via_auto_fix(
                self.compliant
            )


if __name__ == "__main__":  # pragma: no cover
    if PYTEST_AVAILABLE:
        sys.exit(pytest.main([__file__, "-v"]))
    else:
        unittest.main(verbosity=2)

