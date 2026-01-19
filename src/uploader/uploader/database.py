"""PostgreSQL database operations."""

from datetime import datetime, timezone

import psycopg
from azure.identity import DefaultAzureCredential


class Database:
    """PostgreSQL database client for photo records."""

    def __init__(self, host: str, database: str, user: str):
        """Initialize database connection.

        Args:
            host: PostgreSQL host.
            database: Database name.
            user: Username (UPN for Entra auth).
        """
        self.host = host
        self.database = database
        self.user = user
        self._conn: psycopg.Connection | None = None

    def _get_token(self) -> str:
        """Get Entra access token for PostgreSQL."""
        credential = DefaultAzureCredential()
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token

    def connect(self) -> None:
        """Establish database connection."""
        token = self._get_token()
        self._conn = psycopg.connect(
            host=self.host,
            dbname=self.database,
            user=self.user,
            password=token,
            sslmode="require",
        )

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def photo_exists(self, photo_id: str) -> bool:
        """Check if a photo record exists.

        Args:
            photo_id: SHA-256 hash of the photo.

        Returns:
            True if photo exists in database.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM photos WHERE id = %s", (photo_id,))
            return cur.fetchone() is not None

    def create_photo(self, photo_id: str, original_filename: str) -> None:
        """Create a photo record.

        Args:
            photo_id: SHA-256 hash of the photo.
            original_filename: Original filename for reference.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        now = datetime.now(timezone.utc)

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO photos (id, original_filename, is_low_quality, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (photo_id, original_filename, False, now, now),
            )
        self._conn.commit()
