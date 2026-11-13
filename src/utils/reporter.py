"""
Rich Terminal Audit Reporter & Markdown QA Handoff Exporter for `ghl-snapshot-validator`.

Renders:
  - Color-coded per-location `rich` audit tables (`PASS` / `FAIL` / `FIXED`)
  - Multi-location **Agency Health Scoreboard** (`Location | Readiness % | Passed | Failed | Auto-Fixed`)
  - Client-ready Markdown QA handoff reports (`--report-out`)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from src.validators.field_validator import AuditResult

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    RICH_AVAILABLE = False
    Console = None  # type: ignore[assignment]


STATUS_STYLES: Dict[str, str] = {
    "PASS": "bold green",
    "FAIL": "bold red",
    "FIXED": "bold yellow",
}


class AuditReporter:
    """Renders GoHighLevel snapshot audit reports to the terminal and Markdown files."""

    def __init__(self, console: Optional[Any] = None) -> None:
        if console is not None:
            self.console = console
        elif RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

    @staticmethod
    def compute_summary(results: Sequence[AuditResult]) -> Dict[str, Any]:
        """Aggregate PASS, FAIL, FIXED, Readiness %, and exit code from audit results."""
        total = len(results)
        passed = sum(1 for r in results if r.status == "PASS")
        fixed = sum(1 for r in results if r.status == "FIXED")
        failed = sum(1 for r in results if r.status == "FAIL")
        readiness_pct = (
            round(((passed + fixed) / total) * 100.0, 1) if total > 0 else 100.0
        )
        exit_code = 0 if failed == 0 else 1
        return {
            "total": total,
            "passed": passed,
            "fixed": fixed,
            "failed": failed,
            "readiness_pct": readiness_pct,
            "exit_code": exit_code,
        }

    def render(
        self,
        results: Sequence[AuditResult],
        *,
        location_id: str = "N/A",
        location_name: Optional[str] = None,
        schema_name: str = "master_agency_blueprint.json",
        auto_fix: bool = False,
        mock: bool = False,
    ) -> Dict[str, Any]:
        """
        Render the color-coded audit table and overall summary panel for a sub-account.
        Returns the summary metrics dictionary including `readiness_pct` and `exit_code`.
        """
        summary = self.compute_summary(results)
        mode_str = "MOCK SIMULATION" if mock else "LIVE GHL API v2"
        remediation_str = "ENABLED (--auto-fix)" if auto_fix else "DISABLED (Read-Only)"
        loc_display = (
            f"{location_name} ({location_id})" if location_name else location_id
        )

        if not RICH_AVAILABLE or self.console is None:
            self._render_plain_fallback(
                results,
                summary=summary,
                location_display=loc_display,
                schema_name=schema_name,
                mode_str=mode_str,
                remediation_str=remediation_str,
            )
            return summary

        header_text = Text.from_markup(
            f"[bold cyan]GHL Snapshot Drift & Compliance Auditor[/bold cyan]\n"
            f"[dim]Location:[/dim] [bold]{loc_display}[/bold]  |  "
            f"[dim]Blueprint:[/dim] [bold]{schema_name}[/bold]  |  "
            f"[dim]Mode:[/dim] [bold magenta]{mode_str}[/bold magenta]  |  "
            f"[dim]Auto-Fix:[/dim] [bold]{remediation_str}[/bold]"
        )
        self.console.print(
            Panel(
                header_text,
                title="[bold white]ghl-snapshot-validator[/bold white]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

        table = Table(
            title=f"Sub-Account Snapshot Audit Report — {loc_display} (Expected vs Actual)",
            box=box.ROUNDED,
            show_lines=False,
            header_style="bold bright_white on dark_blue",
            expand=True,
        )
        table.add_column("Resource Type", style="cyan", no_wrap=True, ratio=15)
        table.add_column("Resource Name", style="bold white", ratio=28)
        table.add_column("Expected", style="green", ratio=22)
        table.add_column("Actual", style="white", ratio=25)
        table.add_column("Status", justify="center", no_wrap=True, ratio=10)

        for item in results:
            status = item.status.upper()
            badge_style = STATUS_STYLES.get(status, "bold white")
            actual_style = (
                "green"
                if status == "PASS"
                else ("yellow" if status == "FIXED" else "bold red")
            )
            table.add_row(
                item.resource_type,
                item.resource_name,
                item.expected,
                f"[{actual_style}]{item.actual}[/{actual_style}]",
                f"[{badge_style}]{status}[/{badge_style}]",
            )

        self.console.print(table)

        verdict_color = "green" if summary["exit_code"] == 0 else "red"
        verdict_label = (
            "COMPLIANT - ALL CHECKS PASSED / RESOLVED (EXIT CODE 0)"
            if summary["exit_code"] == 0
            else "DRIFT DETECTED - UNRESOLVED DISCREPANCIES REMAIN (EXIT CODE 1)"
        )

        summary_markup = (
            f"[bold]Readiness:[/bold] {summary['readiness_pct']:.1f}%    "
            f"[bold]Total Checks:[/bold] {summary['total']}    "
            f"[bold green]PASS:[/bold green] {summary['passed']}    "
            f"[bold yellow]FIXED:[/bold yellow] {summary['fixed']}    "
            f"[bold red]FAIL:[/bold red] {summary['failed']}\n"
            f"[bold {verdict_color}]Verdict: {verdict_label}[/bold {verdict_color}]"
        )
        self.console.print(
            Panel(
                summary_markup,
                title="[bold]Overall Audit Summary[/bold]",
                border_style=verdict_color,
                box=box.HEAVY,
            )
        )

        return summary

    def render_agency_scoreboard(
        self,
        location_reports: Sequence[Dict[str, Any]],
        *,
        schema_name: str = "master_agency_blueprint.json",
        auto_fix: bool = False,
        mock: bool = False,
    ) -> Dict[str, Any]:
        """
        Render the multi-location Agency Health Scoreboard:
        `Location | Readiness % | Passed | Failed | Auto-Fixed`
        """
        total_locations = len(location_reports)
        compliant_locations = sum(
            1 for rep in location_reports if rep["summary"]["failed"] == 0
        )
        total_failed = sum(rep["summary"]["failed"] for rep in location_reports)
        overall_exit_code = 0 if total_failed == 0 else 1

        if not RICH_AVAILABLE or self.console is None:
            print("=" * 95)
            print("AGENCY HEALTH SCOREBOARD")
            print(
                f"{'Location':<40} | {'Readiness %':<12} | "
                f"{'Passed':<8} | {'Failed':<8} | {'Auto-Fixed':<10}"
            )
            print("-" * 95)
            for rep in location_reports:
                loc_label = (
                    f"{rep.get('location_name')} ({rep['location_id']})"
                    if rep.get("location_name")
                    else rep["location_id"]
                )
                s = rep["summary"]
                print(
                    f"{loc_label[:40]:<40} | {s['readiness_pct']:>10.1f}% | "
                    f"{s['passed']:>8} | {s['failed']:>8} | {s['fixed']:>10}"
                )
            print("=" * 95)
            return {
                "total_locations": total_locations,
                "compliant_locations": compliant_locations,
                "total_failed": total_failed,
                "exit_code": overall_exit_code,
            }

        scoreboard = Table(
            title="Agency Health Scoreboard (Multi-Location Batch Audit)",
            box=box.DOUBLE_EDGE,
            header_style="bold bright_white on dark_blue",
            expand=True,
        )
        scoreboard.add_column("Location", style="bold white", ratio=38)
        scoreboard.add_column("Readiness %", justify="right", ratio=15)
        scoreboard.add_column("Passed", justify="right", style="green", ratio=12)
        scoreboard.add_column("Failed", justify="right", style="red", ratio=12)
        scoreboard.add_column("Auto-Fixed", justify="right", style="yellow", ratio=13)
        scoreboard.add_column("Status", justify="center", ratio=10)

        for rep in location_reports:
            loc_label = (
                f"{rep.get('location_name')} ({rep['location_id']})"
                if rep.get("location_name")
                else rep["location_id"]
            )
            s = rep["summary"]
            pct = s["readiness_pct"]
            pct_color = "green" if pct == 100.0 else ("yellow" if pct >= 80.0 else "red")
            status_badge = (
                "[bold green]READY[/bold green]"
                if s["failed"] == 0
                else "[bold red]DRIFT[/bold red]"
            )
            scoreboard.add_row(
                loc_label,
                f"[bold {pct_color}]{pct:.1f}%[/bold {pct_color}]",
                str(s["passed"]),
                str(s["failed"]),
                str(s["fixed"]),
                status_badge,
            )

        self.console.print(scoreboard)
        return {
            "total_locations": total_locations,
            "compliant_locations": compliant_locations,
            "total_failed": total_failed,
            "exit_code": overall_exit_code,
        }

    def export_markdown_report(
        self,
        output_path: Union[str, Path],
        location_reports: Sequence[Dict[str, Any]],
        *,
        schema_name: str = "master_agency_blueprint.json",
        auto_fix: bool = False,
        mock: bool = False,
    ) -> Path:
        """
        Export a clean, client-ready Markdown QA Handoff Report (`--report-out`).
        Includes the Agency Health Scoreboard and per-location detailed tables.
        """
        target = Path(output_path)
        if target.parent and str(target.parent) != ".":
            target.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        mode_str = "Mock Simulation" if mock else "Live GHL API v2"
        total_failed = sum(r["summary"]["failed"] for r in location_reports)
        overall_status = (
            "PASS - Ready for Client Onboarding"
            if total_failed == 0
            else "FAIL - Configuration Drift Requires Attention"
        )

        lines: List[str] = [
            "# GoHighLevel Snapshot QA & Onboarding Readiness Report",
            "",
            f"- **Generated At**: `{timestamp}`",
            f"- **Master Blueprint**: `{schema_name}`",
            f"- **Execution Mode**: `{mode_str}`",
            f"- **Auto-Fix Remediation**: `{'Enabled' if auto_fix else 'Disabled'}`",
            f"- **Overall Verdict**: **{overall_status}**",
            "",
            "---",
            "",
            "## Agency Health Scoreboard",
            "",
            "| Location | Readiness % | Passed | Failed | Auto-Fixed | Status |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]

        for rep in location_reports:
            loc_label = (
                f"{rep.get('location_name')} (`{rep['location_id']}`)"
                if rep.get("location_name")
                else f"`{rep['location_id']}`"
            )
            s = rep["summary"]
            status_str = "PASS" if s["failed"] == 0 else "FAIL"
            lines.append(
                f"| {loc_label} | **{s['readiness_pct']:.1f}%** | "
                f"{s['passed']} | {s['failed']} | {s['fixed']} | **{status_str}** |"
            )

        lines.extend(["", "---", ""])

        for rep in location_reports:
            loc_title = (
                f"{rep.get('location_name')} ({rep['location_id']})"
                if rep.get("location_name")
                else rep["location_id"]
            )
            s = rep["summary"]
            lines.extend(
                [
                    f"## Sub-Account Audit Details: {loc_title}",
                    "",
                    f"**Readiness**: `{s['readiness_pct']:.1f}%` | "
                    f"**Passed**: `{s['passed']}` | "
                    f"**Auto-Fixed**: `{s['fixed']}` | "
                    f"**Failed**: `{s['failed']}`",
                    "",
                    "| Resource Type | Resource Name | Expected | Actual | Status |",
                    "| :--- | :--- | :--- | :--- | :---: |",
                ]
            )
            for item in rep["results"]:
                exp_clean = str(item.expected).replace("|", "\\|")
                act_clean = str(item.actual).replace("|", "\\|")
                name_clean = str(item.resource_name).replace("|", "\\|")
                lines.append(
                    f"| {item.resource_type} | {name_clean} | `{exp_clean}` | "
                    f"`{act_clean}` | **{item.status}** |"
                )
            lines.append("")

        target.write_text("\n".join(lines), encoding="utf-8")
        return target

    @staticmethod
    def _render_plain_fallback(
        results: Sequence[AuditResult],
        *,
        summary: Dict[str, Any],
        location_display: str,
        schema_name: str,
        mode_str: str,
        remediation_str: str,
    ) -> None:  # pragma: no cover
        print("=" * 95)
        print("GHL Snapshot Drift & Compliance Auditor (Expected vs Actual)")
        print(
            f"Location: {location_display} | Blueprint: {schema_name} | "
            f"Mode: {mode_str} | Auto-Fix: {remediation_str}"
        )
        print("=" * 95)
        print(
            f"{'Resource Type':<16} | {'Resource Name':<32} | "
            f"{'Expected':<18} | {'Actual':<18} | {'Status':<6}"
        )
        print("-" * 95)
        for r in results:
            print(
                f"{r.resource_type:<16} | {r.resource_name[:32]:<32} | "
                f"{r.expected[:18]:<18} | {r.actual[:18]:<18} | {r.status:<6}"
            )
        print("=" * 95)
        print(
            f"Overall Summary -> Readiness: {summary['readiness_pct']:.1f}% | "
            f"Total: {summary['total']} | PASS: {summary['passed']} | "
            f"FIXED: {summary['fixed']} | FAIL: {summary['failed']} | "
            f"Exit Code: {summary['exit_code']}"
        )
        print("=" * 95)


def render_audit_report(
    results: Sequence[AuditResult],
    *,
    location_id: str = "N/A",
    location_name: Optional[str] = None,
    schema_name: str = "master_agency_blueprint.json",
    auto_fix: bool = False,
    mock: bool = False,
    console: Optional[Any] = None,
) -> Dict[str, Any]:
    """Convenience function to render an audit report and return summary metrics."""
    reporter = AuditReporter(console=console)
    return reporter.render(
        results,
        location_id=location_id,
        location_name=location_name,
        schema_name=schema_name,
        auto_fix=auto_fix,
        mock=mock,
    )
