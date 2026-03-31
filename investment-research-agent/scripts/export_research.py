#!/usr/bin/env python3
"""
Export a completed research session to a structured Markdown document.
Generates a well-formatted research report with all citations and rule applications.

Usage: python export_research.py <session_data_json> <output_path>

The session_data JSON should contain:
{
  "topic": "NVIDIA AI Infrastructure",
  "date": "2026-03-29",
  "researcher": "Sharon",
  "type": "company_deep_dive",
  "dimensions": [
    {
      "name": "Market Size & TAM",
      "data_points": [
        {
          "content": "Global AI accelerator market expected to reach $X by 2028",
          "source": "Source Name",
          "url": "https://...",
          "accessed": "2026-03-29"
        }
      ],
      "quality": {
        "completeness": "full",
        "freshness": "2026-Q1",
        "reliability": "primary"
      },
      "issues": ["Some issue noted"],
      "user_notes": "User's commentary on this dimension"
    }
  ],
  "rule_results": [
    {
      "rule_name": "FCF Yield Threshold",
      "condition": "FCF_yield > 8%",
      "result": "FCF yield = 4.2% — does NOT meet threshold",
      "status": "not_met",
      "data_sources": ["Source 1", "Source 2"]
    }
  ],
  "extensions_explored": ["Supply chain analysis", "Peer comparison"],
  "open_questions": ["What is the depreciation impact?"],
  "user_decision": "Optional: user's final notes"
}
"""

import json
import sys
from datetime import datetime


def generate_report(session):
    """Generate a structured Markdown research report."""
    lines = []

    # Header
    lines.append(f"# Investment Research: {session['topic']}")
    lines.append("")
    lines.append(f"**Date:** {session.get('date', 'N/A')}")
    lines.append(f"**Researcher:** {session.get('researcher', 'N/A')}")
    lines.append(f"**Type:** {session.get('type', 'N/A')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    if session.get("executive_summary"):
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(session["executive_summary"])
        lines.append("")

    # Data by Dimension
    lines.append("## Research Findings")
    lines.append("")

    for dim in session.get("dimensions", []):
        lines.append(f"### {dim['name']}")
        lines.append("")

        # Data points
        if dim.get("data_points"):
            lines.append("**Key Data:**")
            lines.append("")
            for dp in dim["data_points"]:
                citation = f"[Source: {dp.get('source', 'N/A')}, {dp.get('url', 'N/A')}, accessed {dp.get('accessed', 'N/A')}]"
                lines.append(f"- {dp['content']}")
                lines.append(f"  {citation}")
                lines.append("")

        # Quality assessment
        quality = dim.get("quality", {})
        if quality:
            completeness_icon = {"full": "✅", "partial": "⚠️", "unavailable": "❌"}.get(
                quality.get("completeness", ""), "•"
            )
            lines.append(f"**Data Quality:** {completeness_icon} Completeness: {quality.get('completeness', 'N/A')} | "
                         f"Freshness: {quality.get('freshness', 'N/A')} | "
                         f"Reliability: {quality.get('reliability', 'N/A')}")
            lines.append("")

        # Issues
        if dim.get("issues"):
            lines.append("**Issues/Caveats:**")
            lines.append("")
            for issue in dim["issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")

        # User notes
        if dim.get("user_notes"):
            lines.append(f"**Notes:** {dim['user_notes']}")
            lines.append("")

    # Rule Results
    if session.get("rule_results"):
        lines.append("## Pattern Rule Applications")
        lines.append("")
        for rule in session["rule_results"]:
            status_icon = {"met": "✅", "not_met": "❌", "warning": "⚠️"}.get(rule.get("status", ""), "•")
            lines.append(f"{status_icon} **{rule.get('rule_name', 'N/A')}**")
            lines.append(f"   Condition: `{rule.get('condition', 'N/A')}`")
            lines.append(f"   Result: {rule.get('result', 'N/A')}")
            if rule.get("data_sources"):
                lines.append(f"   Sources: {', '.join(rule['data_sources'])}")
            lines.append("")

    # Extensions explored
    if session.get("extensions_explored"):
        lines.append("## Additional Analysis (Pattern-Based Extensions)")
        lines.append("")
        for ext in session["extensions_explored"]:
            lines.append(f"- {ext}")
        lines.append("")

    # Open Questions
    if session.get("open_questions"):
        lines.append("## Open Questions")
        lines.append("")
        for q in session["open_questions"]:
            lines.append(f"- ❓ {q}")
        lines.append("")

    # User Decision
    if session.get("user_decision"):
        lines.append("## Decision / Notes")
        lines.append("")
        lines.append(session["user_decision"])
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Investment Research Agent on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"*All data points include source citations. Verify critical numbers against primary sources.*")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python export_research.py <session_data.json> <output.md>")
        sys.exit(1)

    session_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(session_path, 'r', encoding='utf-8') as f:
        session = json.load(f)

    report = generate_report(session)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Research report exported to {output_path}")
    print(f"   Topic: {session.get('topic', 'N/A')}")
    print(f"   Dimensions: {len(session.get('dimensions', []))}")
    print(f"   Rules applied: {len(session.get('rule_results', []))}")


if __name__ == "__main__":
    main()
