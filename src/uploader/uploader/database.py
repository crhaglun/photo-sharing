"""PostgreSQL database operations."""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from azure.identity import DefaultAzureCredential

from .image_processing import ExifData


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
        """Check if a photo record exists."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM photos WHERE id = %s", (photo_id,))
            return cur.fetchone() is not None

    def has_manual_edits(self, photo_id: str, field_type: str) -> bool:
        """Check if a photo has manual edits for a field type.

        Args:
            photo_id: Photo ID.
            field_type: Field type to check ('date' or 'place').

        Returns:
            True if there are manual edits for this field.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM edit_history WHERE photo_id = %s AND field_type = %s LIMIT 1",
                (photo_id, field_type),
            )
            return cur.fetchone() is not None

    def create_photo(
        self,
        photo_id: str,
        original_filename: str,
        date_not_earlier_than: datetime | None = None,
        date_not_later_than: datetime | None = None,
        place_id: UUID | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Create or update a photo record.

        If the photo exists and has manual edits for date or place,
        those fields will not be overwritten.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        now = datetime.now(timezone.utc)

        # Check for existing manual edits
        if self.photo_exists(photo_id):
            if self.has_manual_edits(photo_id, "date"):
                date_not_earlier_than = None
                date_not_later_than = None
            if self.has_manual_edits(photo_id, "place"):
                place_id = None

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO photos (id, original_filename, date_not_earlier_than, date_not_later_than,
                                    place_id, width, height, is_low_quality, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    date_not_earlier_than = COALESCE(EXCLUDED.date_not_earlier_than, photos.date_not_earlier_than),
                    date_not_later_than = COALESCE(EXCLUDED.date_not_later_than, photos.date_not_later_than),
                    place_id = COALESCE(EXCLUDED.place_id, photos.place_id),
                    width = COALESCE(EXCLUDED.width, photos.width),
                    height = COALESCE(EXCLUDED.height, photos.height),
                    updated_at = EXCLUDED.updated_at
                """,
                (photo_id, original_filename, date_not_earlier_than, date_not_later_than,
                 place_id, width, height, False, now, now),
            )
        self._conn.commit()

    def create_exif_metadata(self, photo_id: str, exif: ExifData) -> None:
        """Create or update EXIF metadata record."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        raw_json = json.dumps(exif.raw_exif) if exif.raw_exif else None

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exif_metadata (photo_id, camera_make, camera_model, lens, focal_length,
                                           aperture, shutter_speed, iso, taken_at, raw_exif)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (photo_id) DO UPDATE SET
                    camera_make = EXCLUDED.camera_make,
                    camera_model = EXCLUDED.camera_model,
                    lens = EXCLUDED.lens,
                    focal_length = EXCLUDED.focal_length,
                    aperture = EXCLUDED.aperture,
                    shutter_speed = EXCLUDED.shutter_speed,
                    iso = EXCLUDED.iso,
                    taken_at = EXCLUDED.taken_at,
                    raw_exif = EXCLUDED.raw_exif
                """,
                (photo_id, exif.camera_make, exif.camera_model, exif.lens, exif.focal_length,
                 exif.aperture, exif.shutter_speed, exif.iso, exif.taken_at, raw_json),
            )
        self._conn.commit()

    def get_or_create_place(
        self,
        name_sv: str,
        name_en: str,
        place_type: str,
        parent_id: UUID | None = None,
    ) -> UUID:
        """Get existing place or create new one.

        Args:
            name_sv: Swedish name.
            name_en: English name.
            place_type: Type (country, state, city, street).
            parent_id: Parent place ID.

        Returns:
            UUID of the place.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            # Try to find existing place
            if parent_id:
                cur.execute(
                    "SELECT id FROM places WHERE name_sv = %s AND parent_id = %s",
                    (name_sv, parent_id),
                )
            else:
                cur.execute(
                    "SELECT id FROM places WHERE name_sv = %s AND parent_id IS NULL",
                    (name_sv,),
                )

            row = cur.fetchone()
            if row:
                return row[0]

            # Create new place
            place_id = uuid4()
            cur.execute(
                """
                INSERT INTO places (id, name_sv, name_en, type, parent_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (place_id, name_sv, name_en, place_type, parent_id),
            )
            self._conn.commit()
            return place_id

    def create_place_hierarchy(
        self,
        country: tuple[str, str] | None = None,
        state: tuple[str, str] | None = None,
        city: tuple[str, str] | None = None,
        street: tuple[str, str] | None = None,
    ) -> UUID | None:
        """Create place hierarchy and return the most specific place ID.

        Each argument is a tuple of (name_sv, name_en).

        Returns:
            UUID of the most specific place, or None if no place data.
        """
        parent_id: UUID | None = None
        result_id: UUID | None = None

        if country:
            result_id = self.get_or_create_place(country[0], country[1], "country", None)
            parent_id = result_id

        if state:
            result_id = self.get_or_create_place(state[0], state[1], "state", parent_id)
            parent_id = result_id

        if city:
            result_id = self.get_or_create_place(city[0], city[1], "city", parent_id)
            parent_id = result_id

        if street:
            result_id = self.get_or_create_place(street[0], street[1], "street", parent_id)

        return result_id

    def embedding_exists(self, photo_id: str) -> bool:
        """Check if an image embedding exists for a photo."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM image_embeddings WHERE photo_id = %s", (photo_id,))
            return cur.fetchone() is not None

    def create_image_embedding(self, photo_id: str, embedding: list[float]) -> None:
        """Create or update image embedding record.

        Args:
            photo_id: Photo ID (SHA-256 hash).
            embedding: List of floats (768 dimensions for DINOv2-base).
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        # Convert list to pgvector format string: [1.0, 2.0, 3.0] -> '[1.0,2.0,3.0]'
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO image_embeddings (photo_id, embedding)
                VALUES (%s, %s::vector)
                ON CONFLICT (photo_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding
                """,
                (photo_id, vector_str),
            )
        self._conn.commit()

    def faces_exist(self, photo_id: str) -> bool:
        """Check if faces have been processed for a photo."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM faces WHERE photo_id = %s LIMIT 1", (photo_id,))
            return cur.fetchone() is not None

    def create_face(
        self,
        photo_id: str,
        bbox_x: int,
        bbox_y: int,
        bbox_width: int,
        bbox_height: int,
        embedding: list[float],
    ) -> UUID:
        """Create a face record.

        Args:
            photo_id: Photo ID (SHA-256 hash).
            bbox_x: Bounding box X coordinate.
            bbox_y: Bounding box Y coordinate.
            bbox_width: Bounding box width.
            bbox_height: Bounding box height.
            embedding: List of floats (512 dimensions for InsightFace).

        Returns:
            UUID of the created face.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        face_id = uuid4()
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO faces (id, photo_id, bbox_x, bbox_y, bbox_width, bbox_height, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                """,
                (face_id, photo_id, bbox_x, bbox_y, bbox_width, bbox_height, vector_str),
            )
        self._conn.commit()
        return face_id

    def get_face_count(self, photo_id: str) -> int:
        """Get the number of faces for a photo."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM faces WHERE photo_id = %s", (photo_id,))
            row = cur.fetchone()
            return row[0] if row else 0

    def get_all_face_embeddings(self) -> list[tuple[UUID, list[float]]]:
        """Get all face embeddings for clustering.

        Returns:
            List of (face_id, embedding) tuples.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT id, embedding::text FROM faces")
            results = []
            for row in cur.fetchall():
                face_id = row[0]
                # Parse pgvector format: '[1.0,2.0,3.0]' -> [1.0, 2.0, 3.0]
                embedding_str = row[1].strip("[]")
                embedding = [float(v) for v in embedding_str.split(",")]
                results.append((face_id, embedding))
            return results

    def update_face_cluster(self, face_id: UUID, cluster_id: str) -> None:
        """Update the cluster_id for a face.

        Args:
            face_id: Face UUID.
            cluster_id: Cluster identifier string.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE faces SET cluster_id = %s WHERE id = %s",
                (cluster_id, face_id),
            )
        self._conn.commit()

    def update_face_clusters_batch(self, updates: list[tuple[UUID, str]]) -> None:
        """Batch update cluster_ids for faces.

        Args:
            updates: List of (face_id, cluster_id) tuples.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.executemany(
                "UPDATE faces SET cluster_id = %s WHERE id = %s",
                [(cluster_id, face_id) for face_id, cluster_id in updates],
            )
        self._conn.commit()

    def get_unclustered_face_count(self) -> int:
        """Get count of faces without cluster assignment."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM faces WHERE cluster_id IS NULL")
            row = cur.fetchone()
            return row[0] if row else 0

    def get_cluster_count(self) -> int:
        """Get count of unique clusters."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT cluster_id) FROM faces WHERE cluster_id IS NOT NULL")
            row = cur.fetchone()
            return row[0] if row else 0

    def get_all_photo_ids(self) -> set[str]:
        """Get all existing photo IDs in the database.

        Returns:
            Set of photo IDs (SHA-256 hashes).
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT id FROM photos")
            return {row[0] for row in cur.fetchall()}

    def get_all_embedding_photo_ids(self) -> set[str]:
        """Get all photo IDs that have embeddings.

        Returns:
            Set of photo IDs with existing embeddings.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT photo_id FROM image_embeddings")
            return {row[0] for row in cur.fetchall()}

    def get_all_face_photo_ids(self) -> set[str]:
        """Get all photo IDs that have at least one face detected.

        Returns:
            Set of photo IDs with existing face records.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT DISTINCT photo_id FROM faces")
            return {row[0] for row in cur.fetchall()}

    def get_all_photo_places(self) -> dict[str, UUID]:
        """Get all photo IDs with their assigned place_id.

        Returns:
            Dictionary mapping photo_id to place_id (only includes photos with non-null place_id).
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        with self._conn.cursor() as cur:
            cur.execute("SELECT id, place_id FROM photos WHERE place_id IS NOT NULL")
            return {row[0]: row[1] for row in cur.fetchall()}
