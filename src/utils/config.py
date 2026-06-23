"""
Configuration management for the Energy Analytics Pipeline.

Loads settings from environment variables with sensible defaults.
In production, these are set via Docker Compose or Kubernetes secrets.
In development, they're loaded from a .env file.

Design decisions:
- dataclass for type safety and IDE autocompletion
- Environment variables as the single source of truth (12-factor app)
- Defaults for local development so it works out of the box
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists (dev only — in Docker, env vars are set directly)
load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    """PostgreSQL connection configuration."""

    host: str = field(default_factory=lambda: os.getenv("ENERGY_DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("ENERGY_DB_PORT", "5432")))
    name: str = field(default_factory=lambda: os.getenv("ENERGY_DB_NAME", "energy_db"))
    user: str = field(default_factory=lambda: os.getenv("ENERGY_DB_USER", "energy_user"))
    password: str = field(default_factory=lambda: os.getenv("ENERGY_DB_PASSWORD", "energy_pass"))

    @property
    def connection_string(self) -> str:
        """Build a psycopg2-compatible connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def connection_dict(self) -> dict:
        """Return connection parameters as a dict for psycopg2.connect()."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.name,
            "user": self.user,
            "password": self.password,
        }


@dataclass(frozen=True)
class PipelineConfig:
    """Pipeline runtime configuration."""

    source_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("ENERGY_SOURCE_DIR", "/opt/airflow/data/source/meter_readings")
        )
    )
    sample_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("ENERGY_SAMPLE_DIR", "/opt/airflow/data/sample")
        )
    )
    batch_size: int = field(
        default_factory=lambda: int(os.getenv("ENERGY_BATCH_SIZE", "10000"))
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration — aggregates all sub-configs."""

    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)


def get_config() -> AppConfig:
    """
    Factory function to create the application configuration.

    Usage:
        config = get_config()
        conn_string = config.db.connection_string
        source_dir = config.pipeline.source_dir
    """
    return AppConfig()
