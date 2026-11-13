"""
Workflow Publication Status Validator for GoHighLevel Sub-Account Audits.

Queries `GET /workflows/?locationId={locationId}` (via `GHLAuditClient`) and
compares sub-account workflows against `master_agency_blueprint.json` to flag:
  - Missing core workflows (`MISSING_WORKFLOW`)
  - Workflows left in `"draft"` status instead of `"published"` (`WORKFLOW_STATUS_DRIFT`)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from src.validators.field_validator import AuditResult


class WorkflowValidator:
    """
    Validates GoHighLevel Workflows against the master agency blueprint schema
    to ensure all required automations exist and are published (`status == "published"`).
    """

    def __init__(self, blueprint: Optional[Dict[str, Any]] = None) -> None:
        self.blueprint = blueprint or {}

    def validate_workflows(
        self,
        expected_workflows: Optional[Sequence[Dict[str, Any]]] = None,
        actual_workflows: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[AuditResult]:
        """
        Compare expected blueprint workflows against live sub-account workflows.
        Flags missing workflows and workflows stuck in `draft` status.
        """
        exp_list = (
            list(expected_workflows)
            if expected_workflows is not None
            else list(self.blueprint.get("workflows", []))
        )
        act_list = list(actual_workflows or [])

        actual_by_name: Dict[str, Dict[str, Any]] = {
            str(wf.get("name", "")).strip().lower(): wf
            for wf in act_list
            if str(wf.get("name", "")).strip()
        }

        results: List[AuditResult] = []

        for exp_wf in exp_list:
            wf_name = str(exp_wf.get("name", "Unnamed Workflow")).strip()
            exp_status = str(exp_wf.get("expectedStatus", "published")).strip().lower()
            expected_desc = f"status={exp_status}"

            matched = actual_by_name.get(wf_name.lower())
            if matched is None:
                results.append(
                    AuditResult(
                        resource_type="Workflow",
                        resource_name=wf_name,
                        expected=expected_desc,
                        actual="Missing Workflow",
                        status="FAIL",
                        fixable=False,
                        issue_type="MISSING_WORKFLOW",
                        metadata=dict(exp_wf),
                    )
                )
                continue

            act_status = str(matched.get("status", "draft")).strip().lower()
            if act_status != exp_status:
                results.append(
                    AuditResult(
                        resource_type="Workflow",
                        resource_name=wf_name,
                        expected=expected_desc,
                        actual=f"status={act_status} [DRAFT / UNPUBLISHED]",
                        status="FAIL",
                        fixable=False,
                        issue_type="WORKFLOW_STATUS_DRIFT",
                        metadata={
                            **dict(exp_wf),
                            "actual_status": act_status,
                        },
                    )
                )
            else:
                results.append(
                    AuditResult(
                        resource_type="Workflow",
                        resource_name=wf_name,
                        expected=expected_desc,
                        actual=f"status={act_status}",
                        status="PASS",
                        fixable=False,
                        issue_type=None,
                        metadata=dict(exp_wf),
                    )
                )

        return results


def validate_workflows(
    expected_workflows: Sequence[Dict[str, Any]],
    actual_workflows: Sequence[Dict[str, Any]],
) -> List[AuditResult]:
    """Module-level convenience wrapper for workflow validation."""
    return WorkflowValidator().validate_workflows(expected_workflows, actual_workflows)
