"""
GitHub Sync module.
Auto-pushes pattern_memory.json to a GitHub repo after each update.

Requires:
  - GITHUB_TOKEN: Personal Access Token with 'repo' scope
  - GITHUB_REPO: Format "owner/repo-name"
  - GITHUB_PATTERN_PATH (optional): File path in repo, default "pattern_memory.json"
  - GITHUB_BRANCH (optional): Branch name, default "main"

These can be set via environment variables, .env file, or Streamlit sidebar.
"""

import os
import json
import base64
import traceback
from datetime import datetime, timezone
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class GitHubSync:
    """Handles pushing pattern_memory.json to GitHub via the GitHub Contents API."""

    def __init__(self):
        self.token = ""
        self.repo = ""
        self.branch = "main"
        self.file_path = "pattern_memory.json"
        self._load_config()

    def _load_config(self):
        """Load GitHub config from env vars or .env file."""
        # 1. Check environment variables
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.repo = os.environ.get("GITHUB_REPO", "")
        self.branch = os.environ.get("GITHUB_BRANCH", "main")
        self.file_path = os.environ.get("GITHUB_PATTERN_PATH", "pattern_memory.json")

        # 2. Fallback: read from .env file
        if not self.token or not self.repo:
            self._read_env_file()

    def _read_env_file(self):
        """Read missing config from .env file."""
        env_paths = [".env", os.path.join(os.path.dirname(__file__), ".env")]
        for path in env_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if "=" in line:
                                key, val = line.split("=", 1)
                                key = key.strip()
                                val = val.strip().strip("'\"")
                                if key == "GITHUB_TOKEN" and not self.token:
                                    self.token = val
                                elif key == "GITHUB_REPO" and not self.repo:
                                    self.repo = val
                                elif key == "GITHUB_BRANCH":
                                    self.branch = val
                                elif key == "GITHUB_PATTERN_PATH":
                                    self.file_path = val
                except Exception:
                    pass
                break

    def is_configured(self) -> bool:
        """Check if GitHub sync has the minimum required config."""
        return bool(self.token and self.repo)

    def configure(self, token: str, repo: str, branch: str = "main", file_path: str = "pattern_memory.json"):
        """Set config programmatically (e.g., from Streamlit sidebar)."""
        self.token = token.strip()
        self.repo = repo.strip()
        self.branch = branch.strip() or "main"
        self.file_path = file_path.strip() or "pattern_memory.json"

    def save_config_to_env(self):
        """Persist current config to .env file."""
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        existing_lines = []
        github_keys = {"GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_BRANCH", "GITHUB_PATTERN_PATH"}

        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    key = line.strip().split("=", 1)[0].strip() if "=" in line else ""
                    if key not in github_keys:
                        existing_lines.append(line.rstrip("\n"))

        # Append GitHub config
        existing_lines.append(f"GITHUB_TOKEN={self.token}")
        existing_lines.append(f"GITHUB_REPO={self.repo}")
        existing_lines.append(f"GITHUB_BRANCH={self.branch}")
        existing_lines.append(f"GITHUB_PATTERN_PATH={self.file_path}")

        with open(env_path, "w") as f:
            f.write("\n".join(existing_lines) + "\n")

    def _get_file_sha(self) -> Optional[str]:
        """Get the current SHA of the file in the repo (needed for updates)."""
        if not HAS_REQUESTS:
            return None
        url = f"https://api.github.com/repos/{self.repo}/contents/{self.file_path}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        params = {"ref": self.branch}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("sha")
        except Exception:
            pass
        return None

    def push(self, content: str, message: str = "") -> dict:
        """
        Push content to GitHub.

        Args:
            content: The JSON string to push.
            message: Commit message. Auto-generated if empty.

        Returns:
            {"ok": True/False, "message": str, "url": str (if ok)}
        """
        if not HAS_REQUESTS:
            return {"ok": False, "message": "requests 库未安装，请运行 pip install requests"}

        if not self.is_configured():
            return {"ok": False, "message": "GitHub 未配置（需要 GITHUB_TOKEN 和 GITHUB_REPO）"}

        if not message:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            message = f"Update pattern_memory.json — {now}"

        url = f"https://api.github.com/repos/{self.repo}/contents/{self.file_path}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Encode content to base64
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")

        payload = {
            "message": message,
            "content": content_b64,
            "branch": self.branch,
        }

        # If file already exists, we need its SHA to update it
        sha = self._get_file_sha()
        if sha:
            payload["sha"] = sha

        try:
            resp = requests.put(url, headers=headers, json=payload, timeout=30)

            if resp.status_code in (200, 201):
                result = resp.json()
                file_url = result.get("content", {}).get("html_url", "")
                return {
                    "ok": True,
                    "message": "Pattern 已同步到 GitHub",
                    "url": file_url,
                    "sha": result.get("content", {}).get("sha", ""),
                }
            else:
                error_msg = resp.json().get("message", resp.text[:200])
                return {"ok": False, "message": f"GitHub API 错误 ({resp.status_code}): {error_msg}"}

        except requests.exceptions.Timeout:
            return {"ok": False, "message": "GitHub API 请求超时，请检查网络"}
        except Exception as e:
            return {"ok": False, "message": f"推送失败: {str(e)}"}

    def push_pattern(self, pattern_data: dict, session_topic: str = "") -> dict:
        """
        Convenience method: push a pattern dict to GitHub.

        Args:
            pattern_data: The pattern memory dict.
            session_topic: Optional topic name for the commit message.
        """
        content = json.dumps(pattern_data, indent=2, ensure_ascii=False)
        if session_topic:
            message = f"Pattern update: {session_topic}"
        else:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            message = f"Pattern update — {now}"
        return self.push(content, message)


# Singleton instance
github_sync = GitHubSync()
