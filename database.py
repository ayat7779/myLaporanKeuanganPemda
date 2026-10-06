import os
from contextlib import closing
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as Connection


MASTER_TABLES = {
    "master_kelompok": (
        ("kode_kelompok", "nama_kelompok"),
        ("kode_kelompok",),
    ),
    "master_jenis": (
        ("kode_kelompok", "kode_jenis", "nama_jenis"),
        ("kode_kelompok", "kode_jenis"),
    ),
    "master_objek": (
        ("kode_kelompok", "kode_jenis", "kode_objek", "nama_objek"),
        ("kode_kelompok", "kode_jenis", "kode_objek"),
    ),
    "master_rincian_objek": (
        (
            "kode_kelompok",
            "kode_jenis",
            "kode_objek",
            "kode_rincian_objek",
            "nama_rincian_objek",
        ),
        (
            "kode_kelompok",
            "kode_jenis",
            "kode_objek",
            "kode_rincian_objek",
        ),
    ),
    "master_sub_rincian_objek": (
        (
            "kode_kelompok",
            "kode_jenis",
            "kode_objek",
            "kode_rincian_objek",
            "kode_sub_rincian_objek",
            "nama_sub_rincian_objek",
        ),
        (
            "kode_kelompok",
            "kode_jenis",
            "kode_objek",
            "kode_rincian_objek",
            "kode_sub_rincian_objek",
        ),
    ),
}


def get_connection() -> Connection:
    load_dotenv(Path(__file__).with_name(".env"))

    required_settings = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing_settings = [
        setting for setting in required_settings if not os.getenv(setting)
    ]
    if missing_settings:
        raise ValueError(
            "Konfigurasi database belum lengkap: " + ", ".join(missing_settings)
        )

    try:
        port = int(os.getenv("DB_PORT", "5432"))
    except ValueError as error:
        raise ValueError("DB_PORT harus berupa angka") from error
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT harus berada di antara 1 dan 65535")

    try:
        return psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=port,
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            connect_timeout=5,
        )
    except UnicodeDecodeError:
        raise psycopg2.OperationalError(
            "Autentikasi PostgreSQL ditolak. Periksa DB_USER dan DB_PASSWORD "
            "di .env; server mengirim pesan error dengan encoding non-UTF-8."
        ) from None


def create_master_tables() -> None:
    schema_path = Path(__file__).with_name("master_data.sql")
    schema = schema_path.read_text(encoding="utf-8")

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(schema)


def _table_definition(
    table: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        return MASTER_TABLES[table]
    except KeyError:
        raise ValueError(f"Tabel master tidak dikenal: {table}") from None


def _validate_fields(
    table: str,
    values: Mapping[str, Any],
    allowed_columns: Sequence[str],
    required_columns: Sequence[str] = (),
) -> dict[str, str]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError("Data harus berupa mapping yang tidak kosong")

    unknown = set(values) - set(allowed_columns)
    missing = set(required_columns) - set(values)
    if unknown or missing:
        details = []
        if unknown:
            details.append("kolom tidak dikenal: " + ", ".join(sorted(unknown)))
        if missing:
            details.append("kolom wajib: " + ", ".join(sorted(missing)))
        raise ValueError(f"Data {table} tidak valid ({'; '.join(details)})")

    cleaned = {}
    for column, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{column} harus berupa teks yang tidak kosong")
        cleaned[column] = value.strip()
    return cleaned


def _validate_key(
    table: str,
    key: Mapping[str, Any],
    primary_key: Sequence[str],
) -> dict[str, str]:
    return _validate_fields(table, key, primary_key, primary_key)


def _where_clause(key: Mapping[str, str]) -> tuple[sql.Composed, list[str]]:
    conditions = [
        sql.SQL("{} = %s").format(sql.Identifier(column)) for column in key
    ]
    return sql.SQL(" AND ").join(conditions), list(key.values())


def create_master_record(table: str, values: Mapping[str, Any]) -> dict[str, Any]:
    """Insert a record into a master table and return the inserted row."""
    columns, _ = _table_definition(table)
    record = _validate_fields(table, values, columns, columns)
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, record)),
        sql.SQL(", ").join(sql.Placeholder() for _ in record),
    )

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, list(record.values()))
                return dict(cursor.fetchone())


def get_master_records(
    table: str, filters: Mapping[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Return records from a master table, optionally filtered by exact values."""
    columns, primary_key = _table_definition(table)
    conditions = _validate_fields(table, filters, columns) if filters else {}
    query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))
    params: list[str] = []
    if conditions:
        where, params = _where_clause(conditions)
        query += sql.SQL(" WHERE ") + where
    query += sql.SQL(" ORDER BY {}").format(
        sql.SQL(", ").join(map(sql.Identifier, primary_key))
    )

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]


def get_master_counts() -> dict[str, int]:
    """Return the row count for each master table in one database query."""
    query = sql.SQL("SELECT {}").format(
        sql.SQL(", ").join(
            sql.SQL("(SELECT count(*) FROM {}) AS {}").format(
                sql.Identifier(table),
                sql.Identifier(table),
            )
            for table in MASTER_TABLES
        )
    )
    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return dict(zip(MASTER_TABLES, cursor.fetchone(), strict=True))


def update_master_record(
    table: str,
    key: Mapping[str, Any],
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Update non-key fields for one record and return the updated row."""
    columns, primary_key = _table_definition(table)
    record_key = _validate_key(table, key, primary_key)
    changes = _validate_fields(
        table,
        values,
        tuple(column for column in columns if column not in primary_key),
    )
    where, key_params = _where_clause(record_key)
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(column)) for column in changes
    )
    query = sql.SQL("UPDATE {} SET {} WHERE {} RETURNING *").format(
        sql.Identifier(table), assignments, where
    )

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, list(changes.values()) + key_params)
                row = cursor.fetchone()
                if row is None:
                    raise LookupError(f"Data tidak ditemukan di tabel {table}")
                return dict(row)


def delete_master_record(table: str, key: Mapping[str, Any]) -> bool:
    """Delete one record by its complete primary key; return whether it existed."""
    _, primary_key = _table_definition(table)
    record_key = _validate_key(table, key, primary_key)
    where, params = _where_clause(record_key)
    query = sql.SQL("DELETE FROM {} WHERE {} RETURNING 1").format(
        sql.Identifier(table), where
    )

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone() is not None
