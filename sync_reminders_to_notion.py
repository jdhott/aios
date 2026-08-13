#!/usr/bin/env python3

"""
Sync Apple Reminders items into the Notion Brain Dump synced block.

Expected .env values:
- NOTION_TOKEN
- NOTION_BRAIN_DUMP_SYNCED_BLOCK_ID
- REMINDERS_BRAIN_DUMP_LIST optional, defaults to "Brain Dump"

Recommended use:
    ./.venv/bin/python sync_reminders_to_notion.py --dry-run --debug-env
    ./.venv/bin/python sync_reminders_to_notion.py
"""

import os
import subprocess
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv


NOTION_VERSION_DEFAULT = "2022-06-28"
DEFAULT_REMINDERS_LIST_NAME = "Brain Dump"


def load_env():
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print(f"WARNING: .env not found at {env_path}")
        return

    # Match run_aios.py behaviour: .env wins over stale shell / cron / Shortcut env vars.
    load_dotenv(env_path, override=True)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required .env value: {name}")
    return value


def normalize_notion_id(raw_id: str) -> str:
    return str(raw_id or "").replace("-", "").strip()


def mask_token(token: str) -> str:
    token = str(token or "")
    if len(token) <= 12:
        return "***"
    return f"{token[:8]}...{token[-6:]}"


def notion_headers(notion_token: str) -> dict:
    return {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": os.getenv("NOTION_VERSION", NOTION_VERSION_DEFAULT),
        "Content-Type": "application/json",
    }


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def applescript_quote(text: str) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def fetch_incomplete_reminders(list_name: str):
    script = f"""
tell application "Reminders"
    set targetList to list {applescript_quote(list_name)}
    set outputText to ""
    repeat with r in reminders of targetList whose completed is false
        set reminderId to id of r
        set reminderName to name of r
        set outputText to outputText & reminderId & tab & reminderName & linefeed
    end repeat
    return outputText
end tell
"""

    raw = run_applescript(script)

    reminders = []
    for line in raw.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue

        reminder_id, title = parts
        title = title.strip()

        if title:
            reminders.append(
                {
                    "id": reminder_id.strip(),
                    "title": title,
                }
            )

    return reminders


def resolve_brain_dump_target_block() -> str:
    synced_block_id = get_required_env("NOTION_BRAIN_DUMP_SYNCED_BLOCK_ID")
    synced_block_id = normalize_notion_id(synced_block_id)

    if not synced_block_id:
        raise RuntimeError("NOTION_BRAIN_DUMP_SYNCED_BLOCK_ID is empty after normalization.")

    print(f"Using direct synced Brain Dump block: {synced_block_id}")
    return synced_block_id


def append_to_notion_brain_dump(notion_token: str, block_id: str, title: str):
    block_id = normalize_notion_id(block_id)
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    headers = notion_headers(notion_token)

    payload = {
        "children": [
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": title},
                        }
                    ],
                },
            }
        ]
    }

    response = requests.patch(url, headers=headers, json=payload, timeout=30)

    if not response.ok:
        raise RuntimeError(f"{response.status_code}: {response.text}")

    return response.json()


def complete_reminder(reminder_id: str):
    script = f"""
tell application "Reminders"
    set targetReminder to first reminder whose id is {applescript_quote(reminder_id)}
    set completed of targetReminder to true
end tell
"""
    run_applescript(script)


def print_debug_env(notion_token: str, reminders_list_name: str):
    print("\n--- DEBUG ENV ---")
    print(f"Script path: {Path(__file__).resolve()}")
    print(f".env path: {(Path(__file__).parent / '.env').resolve()}")
    print(f"NOTION_TOKEN: {mask_token(notion_token)}")
    print(f"NOTION_BRAIN_DUMP_SYNCED_BLOCK_ID: {os.getenv('NOTION_BRAIN_DUMP_SYNCED_BLOCK_ID', '')}")
    print(
        "Normalized NOTION_BRAIN_DUMP_SYNCED_BLOCK_ID: "
        f"{normalize_notion_id(os.getenv('NOTION_BRAIN_DUMP_SYNCED_BLOCK_ID', ''))}"
    )
    print(f"REMINDERS_BRAIN_DUMP_LIST: {reminders_list_name}")
    print(f"NOTION_VERSION: {os.getenv('NOTION_VERSION', NOTION_VERSION_DEFAULT)}")
    print("--- END DEBUG ENV ---\n")


def main():
    parser = argparse.ArgumentParser(
        description="Sync Apple Reminders Brain Dump items directly into the Notion synced block."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without changing Notion or Reminders.",
    )
    parser.add_argument(
        "--keep-reminders",
        action="store_true",
        help="Do not mark reminders complete after successful Notion import.",
    )
    parser.add_argument(
        "--debug-env",
        action="store_true",
        help="Print safe environment diagnostics without exposing the full token.",
    )
    args = parser.parse_args()

    load_env()

    notion_token = get_required_env("NOTION_TOKEN")
    reminders_list_name = os.getenv("REMINDERS_BRAIN_DUMP_LIST", DEFAULT_REMINDERS_LIST_NAME)

    if args.debug_env:
        print_debug_env(notion_token, reminders_list_name)

    reminders = fetch_incomplete_reminders(reminders_list_name)

    if not reminders:
        print("No incomplete Brain Dump reminders found.")
        return

    print(f"Found {len(reminders)} reminder(s) in Apple Reminders.")

    target_block_id = resolve_brain_dump_target_block()

    if args.dry_run:
        print("\n--- DRY RUN ---")
        print(f"Would append to Notion block: {target_block_id}")
        for reminder in reminders:
            print(f"- {reminder['title']}")
        return

    imported = 0
    failed = 0

    for reminder in reminders:
        title = reminder["title"]

        try:
            if not args.keep_reminders:
                complete_reminder(reminder["id"])

            print(f"Importing: {title}")

            append_to_notion_brain_dump(
                notion_token=notion_token,
                block_id=target_block_id,
                title=title,
            )

            imported += 1
            print(f"Imported: {title}")

        except Exception as e:
            failed += 1
            print(f"ERROR importing reminder: {title}")
            print(e)

    print(f"\nImported {imported} reminder(s) into Notion Brain Dump.")

    if failed:
        print(f"Failed: {failed} reminder(s).")


if __name__ == "__main__":
    main()
