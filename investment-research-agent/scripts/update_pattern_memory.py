#!/usr/bin/env python3
"""
Update pattern memory with new observations from a research session.
This script applies validated changes to the pattern memory file.

Usage: python update_pattern_memory.py <pattern_memory_path> <changes_json_path>

The changes JSON should follow this structure:
{
  "session_id": "session_003",
  "topic": "NVIDIA AI infrastructure",
  "type": "company_deep_dive",
  "changes": [
    {
      "type": "add_dimension",
      "framework": "company_deep_dive",
      "dimension": {
        "name": "Supply Chain Dependencies",
        "priority": "medium",
        "description": "Key suppliers and supply chain risks",
        "typical_sources": ["10-K filings", "Industry reports"],
        "notes": "Added after NVIDIA research"
      }
    },
    {
      "type": "add_rule",
      "rule": {
        "name": "Capex Intensity Check",
        "condition": "capex_to_revenue > 25% for 3+ years",
        "action": "flag_for_deeper_analysis",
        "category": "capital_allocation",
        "confidence": "medium",
        "notes": "Observed from user's NVIDIA analysis"
      }
    },
    {
      "type": "update_sequence",
      "framework": "company_deep_dive",
      "new_sequence": ["Market Size & TAM", "Unit Economics", "Competitive Landscape"]
    },
    {
      "type": "add_exclusion",
      "exclusion_type": "never_include",
      "item": "Technical chart patterns",
      "reason": "User is fundamentals-only"
    },
    {
      "type": "update_preference",
      "key": "metric_definitions.EBITDA",
      "value": "adjusted_ebitda",
      "notes": "User prefers adjusted EBITDA"
    }
  ]
}
"""

import json
import sys
import os
from datetime import datetime, timezone
from copy import deepcopy


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_rule_id(existing_rules):
    """Generate the next rule ID."""
    existing_ids = [r.get("id", "") for r in existing_rules]
    max_num = 0
    for rid in existing_ids:
        if rid.startswith("rule_"):
            try:
                num = int(rid.split("_")[1])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return f"rule_{max_num + 1:03d}"


def apply_changes(memory, changes_data):
    """Apply a set of changes to the pattern memory. Returns (updated_memory, changelog)."""
    memory = deepcopy(memory)
    changelog = []
    now = datetime.now(timezone.utc).isoformat()
    session_id = changes_data.get("session_id", "unknown")

    for change in changes_data.get("changes", []):
        change_type = change["type"]

        if change_type == "add_dimension":
            framework = change["framework"]
            dimension = change["dimension"]
            if framework in memory["research_frameworks"]:
                # Check if dimension already exists
                existing_names = [d["name"] for d in memory["research_frameworks"][framework]["dimensions"]]
                if dimension["name"] not in existing_names:
                    memory["research_frameworks"][framework]["dimensions"].append(dimension)
                    changelog.append({
                        "date": now,
                        "type": "dimension_added",
                        "detail": f"Added '{dimension['name']}' to {framework}",
                        "context": f"Session: {session_id}"
                    })

        elif change_type == "add_rule":
            rule = change["rule"]
            rule["id"] = generate_rule_id(memory["judgment_rules"])
            rule["source_session"] = session_id
            rule["active"] = True
            memory["judgment_rules"].append(rule)
            changelog.append({
                "date": now,
                "type": "rule_added",
                "detail": f"Added rule: {rule['name']} ({rule['condition']})",
                "context": f"Session: {session_id}"
            })

        elif change_type == "modify_rule":
            rule_id = change["rule_id"]
            updates = change["updates"]
            for rule in memory["judgment_rules"]:
                if rule["id"] == rule_id:
                    old_values = {k: rule.get(k) for k in updates}
                    rule.update(updates)
                    changelog.append({
                        "date": now,
                        "type": "rule_modified",
                        "detail": f"Modified rule {rule_id}: {old_values} → {updates}",
                        "context": f"Session: {session_id}"
                    })
                    break

        elif change_type == "deactivate_rule":
            rule_id = change["rule_id"]
            for rule in memory["judgment_rules"]:
                if rule["id"] == rule_id:
                    rule["active"] = False
                    changelog.append({
                        "date": now,
                        "type": "rule_deactivated",
                        "detail": f"Deactivated rule: {rule['name']}",
                        "context": f"Session: {session_id}, reason: {change.get('reason', 'not specified')}"
                    })
                    break

        elif change_type == "update_sequence":
            framework = change["framework"]
            if framework in memory["research_frameworks"]:
                old_seq = memory["research_frameworks"][framework]["sequence"]
                memory["research_frameworks"][framework]["sequence"] = change["new_sequence"]
                changelog.append({
                    "date": now,
                    "type": "sequence_updated",
                    "detail": f"Updated {framework} sequence: {old_seq} → {change['new_sequence']}",
                    "context": f"Session: {session_id}"
                })

        elif change_type == "add_exclusion":
            exc_type = change["exclusion_type"]
            if exc_type in memory["exclusions"]:
                existing = [e["item"] for e in memory["exclusions"][exc_type]]
                if change["item"] not in existing:
                    memory["exclusions"][exc_type].append({
                        "item": change["item"],
                        "reason": change.get("reason", "")
                    })
                    changelog.append({
                        "date": now,
                        "type": "exclusion_added",
                        "detail": f"Added to {exc_type}: {change['item']}",
                        "context": f"Session: {session_id}"
                    })

        elif change_type == "update_preference":
            keys = change["key"].split(".")
            target = memory["data_preferences"]
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            old_value = target.get(keys[-1])
            target[keys[-1]] = change["value"]
            if change.get("notes"):
                target["notes"] = change["notes"]
            changelog.append({
                "date": now,
                "type": "preference_updated",
                "detail": f"Updated {change['key']}: {old_value} → {change['value']}",
                "context": f"Session: {session_id}"
            })

        elif change_type == "add_source":
            source = change["source"]
            existing_names = [s["name"] for s in memory["data_preferences"]["preferred_sources"]]
            if source["name"] not in existing_names:
                memory["data_preferences"]["preferred_sources"].append(source)
                changelog.append({
                    "date": now,
                    "type": "source_added",
                    "detail": f"Added preferred source: {source['name']}",
                    "context": f"Session: {session_id}"
                })

        elif change_type == "exclude_source":
            source_info = {"name": change["name"], "reason": change.get("reason", "")}
            existing = [s["name"] for s in memory["data_preferences"]["excluded_sources"]]
            if change["name"] not in existing:
                memory["data_preferences"]["excluded_sources"].append(source_info)
                changelog.append({
                    "date": now,
                    "type": "source_excluded",
                    "detail": f"Excluded source: {change['name']}",
                    "context": f"Session: {session_id}"
                })

    # Add session to history
    session_entry = {
        "session_id": session_id,
        "date": now[:10],
        "topic": changes_data.get("topic", ""),
        "type": changes_data.get("type", ""),
        "dimensions_used": changes_data.get("dimensions_used", []),
        "rules_applied": changes_data.get("rules_applied", []),
        "rules_added": [c["rule"].get("name", "") for c in changes_data.get("changes", []) if c["type"] == "add_rule"],
        "rules_modified": [c.get("rule_id", "") for c in changes_data.get("changes", []) if c["type"] == "modify_rule"],
        "user_feedback": changes_data.get("user_feedback", ""),
        "duration_minutes": changes_data.get("duration_minutes", 0)
    }
    memory["session_history"].append(session_entry)

    # Add changelog entries
    memory["pattern_evolution"]["changes"].extend(changelog)

    # Update timestamp
    memory["owner"]["last_updated"] = now

    return memory, changelog


def preview_changes(changelog):
    """Print a human-readable preview of changes."""
    if not changelog:
        print("No changes to apply.")
        return

    print("\n📝 Proposed pattern memory updates:\n")
    for i, entry in enumerate(changelog, 1):
        icon = {
            "dimension_added": "📊",
            "rule_added": "⚖️",
            "rule_modified": "✏️",
            "rule_deactivated": "🚫",
            "sequence_updated": "🔄",
            "exclusion_added": "❌",
            "preference_updated": "⚙️",
            "source_added": "📡",
            "source_excluded": "🚫"
        }.get(entry["type"], "•")
        print(f"  {icon} {entry['detail']}")

    print(f"\nTotal: {len(changelog)} change(s)")


def main():
    if len(sys.argv) < 3:
        print("Usage: python update_pattern_memory.py <pattern_memory_path> <changes_json_path>")
        print("\nDry run (preview only):")
        print("  python update_pattern_memory.py <pattern_memory_path> <changes_json_path> --dry-run")
        sys.exit(1)

    memory_path = sys.argv[1]
    changes_path = sys.argv[2]
    dry_run = "--dry-run" in sys.argv

    if not os.path.exists(memory_path):
        print(f"❌ Pattern memory not found: {memory_path}")
        print("Run init_pattern_memory.py first.")
        sys.exit(1)

    memory = load_json(memory_path)
    changes = load_json(changes_path)

    updated_memory, changelog = apply_changes(memory, changes)

    preview_changes(changelog)

    if dry_run:
        print("\n(Dry run — no changes saved)")
    else:
        # Backup existing file
        backup_path = memory_path + ".bak"
        save_json(backup_path, memory)
        print(f"\n💾 Backed up existing memory to {backup_path}")

        # Save updated memory
        save_json(memory_path, updated_memory)
        print(f"✅ Updated pattern memory saved to {memory_path}")


if __name__ == "__main__":
    main()
