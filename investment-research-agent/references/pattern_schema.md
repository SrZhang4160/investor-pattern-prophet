# Pattern Memory Schema

This document defines the JSON schema for `pattern_memory.json` — the file that stores the user's learned investment research patterns.

## File Location

The pattern memory file should be stored in the user's persistent workspace directory so it survives across sessions. Recommended path:

```
<user-workspace>/.investment-agent/pattern_memory.json
```

## Full Schema

```json
{
  "version": "1.0",
  "owner": {
    "name": "User's name",
    "created_at": "2026-03-29T00:00:00Z",
    "last_updated": "2026-03-29T00:00:00Z"
  },

  "research_frameworks": {
    "company_deep_dive": {
      "description": "Framework for analyzing an individual company",
      "dimensions": [
        {
          "name": "Market Size & TAM",
          "priority": "high",
          "description": "Total addressable market sizing and growth trajectory",
          "typical_sources": ["Industry reports", "Company IR presentations", "Third-party research"],
          "notes": "User prefers bottom-up TAM calculation over top-down"
        },
        {
          "name": "Competitive Landscape",
          "priority": "high",
          "description": "Key competitors, market share, differentiation",
          "typical_sources": ["SEC filings (competition section)", "Industry reports"],
          "notes": ""
        }
      ],
      "sequence": ["Market Size & TAM", "Competitive Landscape", "Unit Economics", "Financial Metrics", "Catalysts"],
      "notes": "User typically spends most time on unit economics"
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
      "notes": "User prefers TTM for quick screens, 5Y for deep dives"
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
    "excluded_sources": [
      {
        "name": "Example: Seeking Alpha comments",
        "reason": "User considers unreliable for data"
      }
    ],
    "metric_definitions": {
      "EBITDA": "adjusted_ebitda",
      "FCF": "operating_cf_minus_capex",
      "notes": "User prefers adjusted EBITDA but wants to see the adjustment bridge"
    },
    "market_cap_filter": {
      "min": null,
      "max": null,
      "notes": "No default filter — varies by research type"
    },
    "currency": "USD",
    "notes": ""
  },

  "judgment_rules": [
    {
      "id": "rule_001",
      "name": "FCF Yield Deep Dive Threshold",
      "condition": "FCF_yield > 8%",
      "action": "flag_for_deeper_analysis",
      "category": "valuation",
      "confidence": "high",
      "source_session": "session_001",
      "notes": "User stated this explicitly",
      "active": true
    },
    {
      "id": "rule_002",
      "name": "Leverage Risk Flag",
      "condition": "debt_to_EBITDA > 3.0",
      "action": "flag_as_risk",
      "category": "balance_sheet",
      "confidence": "high",
      "source_session": "session_001",
      "notes": "Hard stop — user considers this a dealbreaker for most situations",
      "active": true
    },
    {
      "id": "rule_003",
      "name": "Pricing Power Signal",
      "condition": "gross_margin_expanding AND revenue_growth > 20%",
      "action": "flag_as_positive_signal",
      "category": "quality",
      "confidence": "medium",
      "source_session": "session_002",
      "notes": "User uses this as a heuristic, not a hard rule",
      "active": true
    }
  ],

  "workflow_preferences": {
    "approval_granularity": "per_dimension",
    "output_format": "structured_markdown",
    "verbosity": "concise_with_full_citations",
    "language": "zh-CN",
    "notes": "User prefers Chinese for analysis, English for raw data citations"
  },

  "exclusions": {
    "never_include": [
      {
        "item": "Example: technical chart patterns",
        "reason": "User is fundamentals-only"
      }
    ],
    "never_recommend": [
      {
        "item": "Example: buy/sell recommendations",
        "reason": "Agent should never make investment recommendations"
      }
    ]
  },

  "session_history": [
    {
      "session_id": "session_001",
      "date": "2026-03-29",
      "topic": "Example: NVIDIA AI infrastructure analysis",
      "type": "company_deep_dive",
      "dimensions_used": ["Market Size & TAM", "Competitive Landscape", "Unit Economics"],
      "rules_applied": ["rule_001", "rule_002"],
      "rules_added": ["rule_001"],
      "rules_modified": [],
      "user_feedback": "Good depth on TAM, need more on supply chain next time",
      "duration_minutes": 45
    }
  ],

  "pattern_evolution": {
    "description": "Track how patterns change over time to understand user's evolving research style",
    "changes": [
      {
        "date": "2026-03-29",
        "type": "rule_added",
        "detail": "Added FCF yield > 8% threshold rule",
        "context": "User screening semiconductor companies"
      }
    ]
  }
}
```

## Schema Notes

### research_frameworks

Each framework type contains:
- **dimensions**: The data categories to investigate, each with priority, description, typical sources, and notes
- **sequence**: The order in which dimensions should be investigated (learned from user behavior)
- **notes**: Free-text observations about how the user approaches this type of research

Frameworks are populated gradually. Start empty and fill in as the user does research. After 3-5 sessions of the same type, the framework should be fairly complete.

### judgment_rules

Rules are the "if A and B then C" logic the user applies:
- **condition**: A human-readable condition string. Keep it simple and parseable.
- **action**: What to do when the condition is met (flag_for_deeper_analysis, flag_as_risk, flag_as_positive_signal, skip, escalate)
- **confidence**: How confident we are this is a real pattern (high = user stated explicitly, medium = observed multiple times, low = observed once)
- **active**: Rules can be deactivated without deletion

### Updating Rules

When updating pattern memory:
1. Always show the user what changed
2. Never auto-save — require explicit approval
3. For rules observed from behavior (not stated explicitly), set confidence to "medium" or "low"
4. Keep a changelog in pattern_evolution

### Phase 2 Considerations

When someone else uses the patterns:
- `owner` field identifies whose patterns these are
- `judgment_rules` with confidence "low" should be presented as tentative
- `exclusions` should always be respected
- Session history from other users should NOT be written to this file
