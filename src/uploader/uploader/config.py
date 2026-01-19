"""Configuration for the uploader."""

from dataclasses import dataclass


@dataclass
class Config:
    """Uploader configuration."""

    storage_account_name: str = "stphotosharing"
    postgres_host: str = "psql-photosharing.postgres.database.azure.com"
    postgres_database: str = "photosharing"
    postgres_user: str = "christoffer.haglund_live.se#EXT#@christofferhaglundlive798.onmicrosoft.com"
