import os
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID = os.getenv(
    "NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID"
)

TELEMETRY_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def run_topology_telemetry_write_test():

    if not NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID:
        print("ERROR: Missing NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID")
        return

    payload = {
        "parent": {
            "database_id": NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID
        },
        "properties": {
            "Seed Task": {
                "title": [
                    {
                        "text": {
                            "content": "Telemetry Integration Test"
                        }
                    }
                ]
            },
            "Event Type": {
                "select": {
                    "name": "telemetry_write_test"
                }
            },
            "Telemetry Version": {
                "select": {
                    "name": "B2_self_segmentation_v1"
                }
            },
            "Notes": {
                "rich_text": [
                    {
                        "text": {
                            "content": (
                                "Standalone telemetry write test."
                            )
                        }
                    }
                ]
            }
        }
    }

    print("Writing telemetry test event...")

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=TELEMETRY_HEADERS,
        json=payload,
        timeout=15,
    )

    print("Status Code:", response.status_code)
    print("Response:")
    print(response.text)


if __name__ == "__main__":
    run_topology_telemetry_write_test()
