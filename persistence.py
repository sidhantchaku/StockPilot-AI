import hashlib
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, desc, select


def _default_sqlite_url() -> str:
    db_path = Path(tempfile.gettempdir()) / "stockpilot.db"
    return f"sqlite:///{db_path.as_posix()}"


DEFAULT_DB_URL = _default_sqlite_url()

metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(80), nullable=False, unique=True),
    Column("password_hash", String(256), nullable=False),
    Column("role", String(20), nullable=False),
    Column("workspace", String(120), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

datasets_table = Table(
    "datasets",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("workspace", String(120), nullable=False),
    Column("source_type", String(80), nullable=False),
    Column("source_name", String(255), nullable=False),
    Column("data_json", Text, nullable=False),
    Column("created_by", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

mappings_table = Table(
    "column_mappings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("workspace", String(120), nullable=False),
    Column("dataset_id", Integer, nullable=True),
    Column("mapping_json", Text, nullable=False),
    Column("created_by", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

plans_table = Table(
    "plans",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("workspace", String(120), nullable=False),
    Column("plan_type", String(80), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("created_by", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

feedback_table = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("workspace", String(120), nullable=False),
    Column("page", String(80), nullable=False),
    Column("choice", String(40), nullable=False),
    Column("comment", Text, nullable=False),
    Column("created_by", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)


def get_engine(db_url: str | None = None):
    return create_engine(_resolve_db_url(db_url), future=True)


def _resolve_db_url(db_url: str | None = None) -> str:
    if db_url:
        return db_url
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Streamlit Community Cloud keeps app secrets in st.secrets.
    try:
        import streamlit as st  # type: ignore

        secrets_url = st.secrets.get("DATABASE_URL")
        if secrets_url:
            return str(secrets_url)
    except Exception:
        pass
    return DEFAULT_DB_URL


def init_db(engine) -> None:
    metadata.create_all(engine)


def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
    return f"{salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if "$" not in stored_hash:
        return False
    salt, digest = stored_hash.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
    return check == digest


def seed_default_users(engine) -> None:
    defaults = [
        ("admin", "admin123", "admin", "global"),
        ("manager", "manager123", "manager", "global"),
        ("ops", "ops123", "ops", "global"),
    ]
    with engine.begin() as conn:
        for username, password, role, workspace in defaults:
            row = conn.execute(
                select(users_table.c.id).where(users_table.c.username == username)
            ).first()
            if row is None:
                conn.execute(
                    users_table.insert().values(
                        username=username,
                        password_hash=_hash_password(password),
                        role=role,
                        workspace=workspace,
                        created_at=datetime.utcnow(),
                    )
                )


def authenticate_user(engine, username: str, password: str) -> dict | None:
    with engine.begin() as conn:
        row = conn.execute(
            select(users_table).where(users_table.c.username == username)
        ).mappings().first()
    if row is None:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "workspace": row["workspace"],
    }


def create_user(engine, username: str, password: str, role: str, workspace: str) -> tuple[bool, str]:
    if role not in {"ops", "manager", "admin"}:
        return False, "Invalid role."
    if not username.strip() or not password:
        return False, "Username and password are required."

    with engine.begin() as conn:
        exists = conn.execute(
            select(users_table.c.id).where(users_table.c.username == username.strip())
        ).first()
        if exists:
            return False, "Username already exists."
        conn.execute(
            users_table.insert().values(
                username=username.strip(),
                password_hash=_hash_password(password),
                role=role,
                workspace=workspace.strip() or "global",
                created_at=datetime.utcnow(),
            )
        )
    return True, "User created."


def list_workspaces(engine) -> list[str]:
    with engine.begin() as conn:
        rows = conn.execute(select(users_table.c.workspace).distinct()).all()
    workspaces = sorted({r[0] for r in rows if r[0]})
    return workspaces or ["global"]


def save_dataset_snapshot(
    engine,
    workspace: str,
    source_type: str,
    source_name: str,
    dataframe: pd.DataFrame,
    created_by: str,
) -> int:
    payload = dataframe.to_json(orient="split", date_format="iso")
    with engine.begin() as conn:
        result = conn.execute(
            datasets_table.insert().values(
                workspace=workspace,
                source_type=source_type,
                source_name=source_name,
                data_json=payload,
                created_by=created_by,
                created_at=datetime.utcnow(),
            )
        )
    return int(result.inserted_primary_key[0])


def load_latest_dataset(engine, workspace: str) -> tuple[pd.DataFrame | None, dict | None]:
    with engine.begin() as conn:
        row = conn.execute(
            select(datasets_table)
            .where(datasets_table.c.workspace == workspace)
            .order_by(desc(datasets_table.c.created_at))
            .limit(1)
        ).mappings().first()
    if row is None:
        return None, None
    data = pd.read_json(row["data_json"], orient="split")
    meta = {
        "id": row["id"],
        "workspace": row["workspace"],
        "source_type": row["source_type"],
        "source_name": row["source_name"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
    }
    return data, meta


def save_column_mapping(
    engine,
    workspace: str,
    dataset_id: int | None,
    mapping_json: str,
    created_by: str,
) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            mappings_table.insert().values(
                workspace=workspace,
                dataset_id=dataset_id,
                mapping_json=mapping_json,
                created_by=created_by,
                created_at=datetime.utcnow(),
            )
        )
    return int(result.inserted_primary_key[0])


def load_latest_mapping(engine, workspace: str) -> dict | None:
    with engine.begin() as conn:
        row = conn.execute(
            select(mappings_table.c.mapping_json)
            .where(mappings_table.c.workspace == workspace)
            .order_by(desc(mappings_table.c.created_at))
            .limit(1)
        ).first()
    if row is None:
        return None
    return row[0]


def save_plan(engine, workspace: str, plan_type: str, payload_json: str, created_by: str) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            plans_table.insert().values(
                workspace=workspace,
                plan_type=plan_type,
                payload_json=payload_json,
                created_by=created_by,
                created_at=datetime.utcnow(),
            )
        )
    return int(result.inserted_primary_key[0])


def save_feedback(
    engine,
    workspace: str,
    page: str,
    choice: str,
    comment: str,
    created_by: str,
) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            feedback_table.insert().values(
                workspace=workspace,
                page=page,
                choice=choice,
                comment=comment,
                created_by=created_by,
                created_at=datetime.utcnow(),
            )
        )
    return int(result.inserted_primary_key[0])
