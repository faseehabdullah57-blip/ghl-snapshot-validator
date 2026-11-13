"""
Pipeline & Stage Ordering Validator for GoHighLevel Sub-Account Audits.

Compares live (or mock) opportunity pipelines against the canonical
`master_agency_blueprint.json` schema to detect:
  - Missing pipelines
  - Missing pipeline stages
  - Stage sequence / position order drift
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from src.validators.field_validator import AuditResult


class PipelineValidator:
    """
    Validates GoHighLevel Opportunity Pipelines and their ordered stages
    against the master agency blueprint schema.
    """

    def __init__(self, blueprint: Optional[Dict[str, Any]] = None) -> None:
        self.blueprint = blueprint or {}

    def validate_pipelines(
        self,
        expected_pipelines: Optional[Sequence[Dict[str, Any]]] = None,
        actual_pipelines: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[AuditResult]:
        """
        Validate expected pipelines and ordered stage definitions against actual
        sub-account pipeline configurations.
        """
        exp_list = (
            list(expected_pipelines)
            if expected_pipelines is not None
            else list(self.blueprint.get("pipelines", []))
        )
        act_list = list(actual_pipelines or [])

        actual_by_name: Dict[str, Dict[str, Any]] = {
            str(p.get("name", "")).strip().lower(): p
            for p in act_list
            if str(p.get("name", "")).strip()
        }

        results: List[AuditResult] = []

        for exp_pipe in exp_list:
            pipe_name = str(exp_pipe.get("name", "Unnamed Pipeline")).strip()
            exp_stages = list(exp_pipe.get("stages", []))
            matched_pipe = actual_by_name.get(pipe_name.lower())

            if matched_pipe is None:
                results.append(
                    AuditResult(
                        resource_type="Pipeline",
                        resource_name=pipe_name,
                        expected=f"Present ({len(exp_stages)} stages)",
                        actual="Missing Pipeline",
                        status="FAIL",
                        fixable=False,
                        issue_type="MISSING_PIPELINE",
                        metadata=dict(exp_pipe),
                    )
                )
                continue

            act_stages = list(matched_pipe.get("stages", []))
            results.append(
                AuditResult(
                    resource_type="Pipeline",
                    resource_name=pipe_name,
                    expected=f"Present ({len(exp_stages)} stages)",
                    actual=f"Present ({len(act_stages)} stages)",
                    status="PASS",
                    fixable=False,
                    issue_type=None,
                    metadata={"name": pipe_name},
                )
            )

            # Build lookup of actual stages by normalized stage name
            actual_stage_map: Dict[str, tuple[int, Dict[str, Any]]] = {}
            for idx, stg in enumerate(act_stages):
                stg_name = str(stg.get("name", "")).strip()
                if stg_name:
                    actual_stage_map[stg_name.lower()] = (idx, stg)

            for exp_idx, exp_stage in enumerate(exp_stages):
                stg_name = str(exp_stage.get("name", f"Stage {exp_idx}")).strip()
                exp_pos = int(exp_stage.get("position", exp_idx))
                resource_label = f"{pipe_name} -> {stg_name}"
                expected_desc = f"position={exp_pos}"

                found = actual_stage_map.get(stg_name.lower())
                if found is None:
                    results.append(
                        AuditResult(
                            resource_type="Pipeline Stage",
                            resource_name=resource_label,
                            expected=expected_desc,
                            actual="Missing Stage",
                            status="FAIL",
                            fixable=False,
                            issue_type="MISSING_STAGE",
                            metadata={"pipeline": pipe_name, **dict(exp_stage)},
                        )
                    )
                    continue

                act_idx, act_stage = found
                act_pos = int(act_stage.get("position", act_idx))

                if act_pos != exp_pos or act_idx != exp_idx:
                    drift_pos = act_pos if act_pos != exp_pos else act_idx
                    results.append(
                        AuditResult(
                            resource_type="Pipeline Stage",
                            resource_name=resource_label,
                            expected=expected_desc,
                            actual=f"position={drift_pos} [OUT OF ORDER]",
                            status="FAIL",
                            fixable=False,
                            issue_type="STAGE_ORDER_DRIFT",
                            metadata={
                                "pipeline": pipe_name,
                                "expected_position": exp_pos,
                                "actual_position": drift_pos,
                            },
                        )
                    )
                else:
                    results.append(
                        AuditResult(
                            resource_type="Pipeline Stage",
                            resource_name=resource_label,
                            expected=expected_desc,
                            actual=f"position={act_pos}",
                            status="PASS",
                            fixable=False,
                            issue_type=None,
                            metadata={"pipeline": pipe_name, **dict(exp_stage)},
                        )
                    )

        return results


def validate_pipelines(
    expected_pipelines: Sequence[Dict[str, Any]],
    actual_pipelines: Sequence[Dict[str, Any]],
) -> List[AuditResult]:
    """Module-level convenience wrapper for pipeline and stage ordering validation."""
    return PipelineValidator().validate_pipelines(expected_pipelines, actual_pipelines)
