from __future__ import annotations

from typing import Any
import requests


class NotionTaskMirrorTitleWriter:
    VERSION = "notion-task-mirror-title-writer-v1"

    def __init__(self, *, headers: dict[str, str]):
        self.headers = headers

    def update_title(
        self,
        *,
        notion_page_id: str,
        authoritative_title: str,
    ) -> dict[str, Any]:
        page_id = str(notion_page_id or "").strip()
        title = str(authoritative_title or "").strip()

        if not page_id:
            raise ValueError("notion_page_id is required")
        if not title:
            raise ValueError("authoritative_title is required")

        payload = {
            "properties": {
                "Task Name": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title},
                        }
                    ]
                }
            }
        }

        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                "Notion task mirror title update failed: "
                f"HTTP {response.status_code} {response.text[:500]}"
            )

        print(f"[Task Mirror Title] Notion mirror updated → {title}")
        return response.json()
