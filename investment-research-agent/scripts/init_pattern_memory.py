#!/usr/bin/env python3
"""
Initialize an empty pattern memory file for the Investment Research Agent.
Usage: python init_pattern_memory.py <output_path> [--owner <name>]
"""

import json
import sys
import os
from datetime import datetime, timezone


def create_empty_pattern_memory(owner_name="Anonymous"):
    """Create a fresh pattern memory structure."""
    return {
        "version": "1.0",
        "owner": {
            "name": owner_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        "research_frameworks": {
            "company_deep_dive": {
                "description": "Framework for analyzing an individual company",
                "dimensions": [],
                "sequence": [],
                "notes": ""
            },
            "industry_landscape": {
                "description": "Framework for analyzing an industry or sector",
                "dimensions": [],
                "sequence": [],
                "notes": ""
            },
            "macro_theme": {
                "description": "Framework for analyzing a macroeconomic theme",
                "dimensions": [],
                "sequence": [],
                "notes": ""
            },
            "comparative_analysis": {
                "description": "Framework for comparing multiple companies",
                "dimensions": [],
                "sequence": [],
                "notes": ""
            },
            "event_driven": {
                "description": "Framework for analyzing specific events (earnings, M&A, regulatory)",
                "dimensions": [],
                "sequence": [],
                "notes": ""
            }
        },
        "data_preferences": {
            "lookback_period": {
                "default": "trailing_12_months",
                "financial_statements": "5_years",
                "stock_price": "3_years",
                "notes": ""
            },
            "preferred_sources": [
                {
                    "name": "SEC EDGAR",
                    "type": "primary",
                    "use_for": ["Financial statements", "Risk factors", "Management discussion"],
                    "priority": 1
                },
                {
                    "name": "Yahoo Finance",
                    "type": "secondary",
                    "use_for": ["Quick financial overview", "Analyst estimates", "Stock data"],
                    "priority": 2
                },
                {
                    "name": "FRED",
                    "type": "primary",
                    "use_for": ["Macro data", "Interest rates", "Economic indicators"],
                    "priority": 1
                }
            ],
            "excluded_sources": [],
            "metric_definitions": {
                "notes": ""
            },
            "market_cap_filter": {
                "min": None,
                "max": None,
                "notes": ""
            },
            "currency": "USD",
            "notes": ""
        },
        "judgment_rules": [],
        "workflow_preferences": {
            "approval_granularity": "per_dimension",
            "output_format": "structured_markdown",
            "verbosity": "concise_with_full_citations",
            "language": "auto",
            "notes": ""
        },
        "exclusions": {
            "never_include": [],
            "never_recommend": [
                {
                    "item": "Buy/sell/hold recommendations",
                    "reason": "Agent should never make investment recommendations — only present data and apply rules"
                }
            ]
        },
        "session_history": [],
        "pattern_evolution": {
            "description": "Track how patterns change over time",
            "changes": []
        }
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python init_pattern_memory.py <output_path> [--owner <name>]")
        print("Example: python init_pattern_memory.py ./pattern_memory.json --owner Sharon")
        sys.exit(1)

    output_path = sys.argv[1]
    owner_name = "Anonymous"

    if "--owner" in sys.argv:
        idx = sys.argv.index("--owner")
        if idx + 1 < len(sys.argv):
            owner_name = sys.argv[idx + 1]

    # Create directory if needed
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Don't overwrite existing file
    if os.path.exists(output_path):
        print(f"Pattern memory already exists at {output_path}")
        print("To reset, delete the file first.")
        sys.exit(1)

    memory = create_empty_pattern_memory(owner_name)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

    print(f"✅ Initialized empty pattern memory at {output_path}")
    print(f"   Owner: {owner_name}")
    print(f"   Created: {memory['owner']['created_at']}")


if __name__ == "__main__":
    main()
