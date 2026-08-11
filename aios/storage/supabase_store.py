import os

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseStore:
    def __init__(self):
        load_dotenv()

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")

        if not url:
            raise RuntimeError("SUPABASE_URL is not set")

        if not key:
            raise RuntimeError("SUPABASE_SECRET_KEY is not set")

        self.client: Client = create_client(url, key)

    def health_check(self) -> dict:
        result = (
            self.client
            .table("projects")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "connected": True,
            "rows_returned": len(result.data or []),
        }