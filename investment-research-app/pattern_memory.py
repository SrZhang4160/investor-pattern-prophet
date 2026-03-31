"""
Pattern Memory management module.
Handles loading, saving, updating, and querying the pattern memory store.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Optional


DEFAULT_PATTERN = {
    "version": "1.0",
    "owner": {
        "name": "",
        "created_at": "",
        "last_updated": ""
    },
    "research_frameworks": {
        "company_deep_dive": {
            "description": "个股深度分析",
            "dimensions": [],
            "sequence": [],
            "notes": ""
        },
        "industry_landscape": {
            "description": "行业/板块全景",
            "dimensions": [],
            "sequence": [],
            "notes": ""
        },
        "macro_theme": {
            "description": "宏观主题分析",
            "dimensions": [],
            "sequence": [],
            "notes": ""
        },
        "comparative_analysis": {
            "description": "多标的对比",
            "dimensions": [],
            "sequence": [],
            "notes": ""
        },
        "event_driven": {
            "description": "事件驱动分析（财报、并购、政策）",
            "dimensions": [],
            "sequence": [],
            "notes": ""
        }
    },
    "data_preferences": {
        "lookback_period": {"default": "trailing_12_months", "notes": ""},
        "preferred_sources": [
            {"name": "SEC EDGAR", "priority": 1, "use_for": ["财务报表", "风险因素"]},
            {"name": "Yahoo Finance", "priority": 2, "use_for": ["快速财务概览", "分析师预期"]},
            {"name": "FRED", "priority": 1, "use_for": ["宏观数据", "利率"]}
        ],
        "excluded_sources": [],
        "metric_definitions": {},
        "notes": ""
    },
    "judgment_rules": [],
    "workflow_preferences": {
        "language": "zh-CN",
        "output_format": "structured_markdown",
        "notes": ""
    },
    "exclusions": {
        "never_include": [],
        "never_recommend": [
            {"item": "买卖推荐", "reason": "Agent 不做投资建议"}
        ]
    },
    "session_history": [],
    "pattern_evolution": {"changes": []}
}

# Default dimensions to suggest when no pattern exists yet
DEFAULT_DIMENSIONS = {
    "company_deep_dive": [
        "市场规模 & TAM", "竞争格局", "单位经济/利润率", "营收拆分",
        "关键财务指标 (TTM)", "近期财报亮点", "分析师一致预期",
        "供应链依赖", "监管风险", "管理层评述"
    ],
    "industry_landscape": [
        "行业规模与增速", "主要玩家与市场份额", "产业链上下游",
        "政策环境", "技术趋势", "进入壁垒", "行业周期位置"
    ],
    "macro_theme": [
        "核心数据指标", "历史趋势", "驱动因素", "政策影响",
        "跨资产传导", "市场定价 vs 基本面", "风险情景"
    ],
    "comparative_analysis": [
        "估值对比", "增长对比", "盈利能力对比", "资产负债表健康度",
        "现金流质量", "竞争优势差异", "风险因素差异"
    ],
    "event_driven": [
        "事件概述", "市场反应", "财务影响测算", "历史可比案例",
        "后续催化剂", "风险因素"
    ]
}


class PatternMemory:
    def __init__(self, filepath: str = "pattern_memory.json"):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def exists(self) -> bool:
        return self.data is not None

    def initialize(self, owner_name: str):
        now = datetime.now(timezone.utc).isoformat()
        self.data = json.loads(json.dumps(DEFAULT_PATTERN))
        self.data["owner"]["name"] = owner_name
        self.data["owner"]["created_at"] = now
        self.data["owner"]["last_updated"] = now
        self._save()

    def _save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _backup(self):
        if os.path.exists(self.filepath):
            shutil.copy2(self.filepath, self.filepath + ".bak")

    def get_owner(self) -> str:
        if not self.data:
            return ""
        return self.data.get("owner", {}).get("name", "")

    def is_owner(self, name: str) -> bool:
        return self.get_owner().lower() == name.lower()

    # --- Frameworks ---

    def get_framework(self, research_type: str) -> dict:
        if not self.data:
            return {}
        return self.data.get("research_frameworks", {}).get(research_type, {})

    def get_dimensions(self, research_type: str) -> list:
        framework = self.get_framework(research_type)
        dims = framework.get("dimensions", [])
        if dims:
            return [d["name"] for d in dims]
        return DEFAULT_DIMENSIONS.get(research_type, [])

    def get_dimension_details(self, research_type: str) -> list:
        framework = self.get_framework(research_type)
        return framework.get("dimensions", [])

    def add_dimension(self, research_type: str, name: str, priority: str = "medium", notes: str = ""):
        if not self.data:
            return
        framework = self.data["research_frameworks"].get(research_type)
        if not framework:
            return
        existing = [d["name"] for d in framework["dimensions"]]
        if name not in existing:
            framework["dimensions"].append({
                "name": name,
                "priority": priority,
                "description": "",
                "typical_sources": [],
                "notes": notes
            })
            self._log_change("dimension_added", f"Added '{name}' to {research_type}")

    def update_sequence(self, research_type: str, sequence: list):
        if not self.data:
            return
        framework = self.data["research_frameworks"].get(research_type)
        if framework:
            framework["sequence"] = sequence
            self._log_change("sequence_updated", f"Updated {research_type} sequence")

    # --- Rules ---

    def get_active_rules(self) -> list:
        if not self.data:
            return []
        return [r for r in self.data.get("judgment_rules", []) if r.get("active", True)]

    def add_rule(self, name: str, condition: str, action: str, category: str = "",
                 confidence: str = "medium", notes: str = ""):
        if not self.data:
            return
        rule_id = f"rule_{len(self.data['judgment_rules']) + 1:03d}"
        rule = {
            "id": rule_id,
            "name": name,
            "condition": condition,
            "action": action,
            "category": category,
            "confidence": confidence,
            "notes": notes,
            "active": True
        }
        self.data["judgment_rules"].append(rule)
        self._log_change("rule_added", f"Added rule: {name} ({condition})")

    def deactivate_rule(self, rule_id: str):
        if not self.data:
            return
        for rule in self.data["judgment_rules"]:
            if rule["id"] == rule_id:
                rule["active"] = False
                self._log_change("rule_deactivated", f"Deactivated: {rule['name']}")

    # --- Preferences ---

    def get_preferences(self) -> dict:
        if not self.data:
            return {}
        return self.data.get("data_preferences", {})

    def get_exclusions(self) -> dict:
        if not self.data:
            return {"never_include": [], "never_recommend": []}
        return self.data.get("exclusions", {"never_include": [], "never_recommend": []})

    # --- Session History ---

    def add_session(self, topic: str, research_type: str, dimensions_used: list,
                    rules_applied: list, feedback: str = ""):
        if not self.data:
            return
        session = {
            "session_id": f"session_{len(self.data['session_history']) + 1:03d}",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "topic": topic,
            "type": research_type,
            "dimensions_used": dimensions_used,
            "rules_applied": rules_applied,
            "user_feedback": feedback
        }
        self.data["session_history"].append(session)

    def get_recent_sessions(self, n: int = 5) -> list:
        if not self.data:
            return []
        return self.data.get("session_history", [])[-n:]

    # --- Pattern Evolution ---

    def _log_change(self, change_type: str, detail: str):
        if not self.data:
            return
        self.data["pattern_evolution"]["changes"].append({
            "date": datetime.now(timezone.utc).isoformat(),
            "type": change_type,
            "detail": detail
        })

    def save_with_backup(self):
        self._backup()
        self.data["owner"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save()

    # --- Export / Import ---

    def export_json(self) -> str:
        return json.dumps(self.data, indent=2, ensure_ascii=False)

    def import_from_dict(self, imported: dict, merge: bool = False):
        if not merge or not self.data:
            self._backup()
            self.data = imported
            self._save()
            return

        # Merge mode: add new items, keep existing
        for ftype, framework in imported.get("research_frameworks", {}).items():
            if ftype in self.data["research_frameworks"]:
                existing_dims = [d["name"] for d in self.data["research_frameworks"][ftype]["dimensions"]]
                for dim in framework.get("dimensions", []):
                    if dim["name"] not in existing_dims:
                        self.data["research_frameworks"][ftype]["dimensions"].append(dim)

        existing_conditions = [r["condition"] for r in self.data["judgment_rules"]]
        for rule in imported.get("judgment_rules", []):
            if rule["condition"] not in existing_conditions:
                rule["id"] = f"rule_{len(self.data['judgment_rules']) + 1:03d}"
                self.data["judgment_rules"].append(rule)

        self._log_change("import_merged", f"Merged patterns from {imported.get('owner', {}).get('name', 'unknown')}")
        self.save_with_backup()

    # --- Summary ---

    def summary(self) -> dict:
        if not self.data:
            return {"exists": False}

        total_dims = sum(
            len(f.get("dimensions", []))
            for f in self.data.get("research_frameworks", {}).values()
        )
        active_rules = len(self.get_active_rules())
        sessions = len(self.data.get("session_history", []))

        return {
            "exists": True,
            "owner": self.get_owner(),
            "last_updated": self.data["owner"].get("last_updated", "")[:10],
            "total_dimensions": total_dims,
            "active_rules": active_rules,
            "total_sessions": sessions,
            "frameworks_with_data": [
                k for k, v in self.data.get("research_frameworks", {}).items()
                if v.get("dimensions")
            ]
        }
