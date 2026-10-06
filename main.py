from collections.abc import Mapping
from typing import Any

import psycopg2
import streamlit as st

from database import (
    MASTER_TABLES,
    create_master_record,
    create_master_tables,
    delete_master_record,
    get_master_records,
    update_master_record,
)


TABLES = {
    "Kelompok": "master_kelompok",
    "Jenis": "master_jenis",
    "Objek": "master_objek",
    "Rincian objek": "master_rincian_objek",
    "Sub rincian objek": "master_sub_rincian_objek",
}
FIELD_LABELS = {
    "kode_kelompok": "Kode kelompok",
    "nama_kelompok": "Nama kelompok",
    "kode_jenis": "Kode jenis",
    "nama_jenis": "Nama jenis",
    "kode_objek": "Kode objek",
    "nama_objek": "Nama objek",
    "kode_rincian_objek": "Kode rincian objek",
    "nama_rincian_objek": "Nama rincian objek",
    "kode_sub_rincian_objek": "Kode sub rincian objek",
    "nama_sub_rincian_objek": "Nama sub rincian objek",
}
PARENT_TABLES = {
    "master_jenis": ("master_kelompok",),
    "master_objek": ("master_kelompok", "master_jenis"),
    "master_rincian_objek": (
        "master_kelompok",
        "master_jenis",
        "master_objek",
    ),
    "master_sub_rincian_objek": (
        "master_kelompok",
        "master_jenis",
        "master_objek",
        "master_rincian_objek",
    ),
}
TABLE_LABELS = {table: label for label, table in TABLES.items()}


@st.cache_resource
def initialize_database() -> None:
    create_master_tables()


def record_label(table: str, row: Mapping[str, Any]) -> str:
    columns, _ = MASTER_TABLES[table]
    code_columns = [column for column in columns if column.startswith("kode_")]
    name_column = next(column for column in columns if column.startswith("nama_"))
    code = ".".join(str(row[column]) for column in code_columns)
    return f"{code} - {row[name_column]}"


def parent_filters(
    table: str, parent_rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, str]:
    columns, _ = MASTER_TABLES[table]
    return {
        column: str(row[column])
        for parent_table, row in parent_rows.items()
        for column in MASTER_TABLES[parent_table][1]
        if column in columns
    }


def select_parent_records(table: str) -> dict[str, Mapping[str, Any]] | None:
    selected: dict[str, Mapping[str, Any]] = {}
    for parent_table in PARENT_TABLES.get(table, ()):
        filters = parent_filters(parent_table, selected) if selected else None
        records = get_master_records(parent_table, filters)
        parent_label = TABLE_LABELS[parent_table]
        if not records:
            st.warning(f"Tambahkan data {parent_label.lower()} terlebih dahulu.")
            return None
        row = st.selectbox(
            parent_label,
            records,
            format_func=lambda item, source=parent_table: record_label(source, item),
            key=f"parent_{table}_{parent_table}",
        )
        selected[parent_table] = row
    return selected


def show_database_error(error: Exception) -> None:
    st.error(f"Operasi database gagal: {error}")


def render_create(table: str) -> None:
    st.subheader("Tambah data")
    parents = select_parent_records(table)
    if parents is None:
        return

    columns, _ = MASTER_TABLES[table]
    parent_columns = {
        column
        for parent_table in parents
        for column in MASTER_TABLES[parent_table][1]
    }
    values: dict[str, str] = {
        column: str(row[column])
        for parent_table, row in parents.items()
        for column in MASTER_TABLES[parent_table][1]
    }
    editable_columns = [column for column in columns if column not in parent_columns]
    with st.form(f"create_{table}", clear_on_submit=True):
        for column in editable_columns:
            values[column] = st.text_input(
                FIELD_LABELS[column], key=f"create_{table}_{column}"
            )
        submitted = st.form_submit_button(
            "Simpan data", type="primary", icon=":material/save:"
        )

    if submitted:
        try:
            record = create_master_record(table, values)
        except (ValueError, psycopg2.Error) as error:
            show_database_error(error)
        else:
            st.success(f"Data berhasil ditambahkan: {record_label(table, record)}")
            st.rerun()


def render_manage(table: str) -> None:
    st.subheader("Ubah atau hapus data")
    records = get_master_records(table)
    if not records:
        st.info("Belum ada data untuk dikelola.")
        return

    selected = st.selectbox(
        "Pilih data",
        records,
        format_func=lambda row: record_label(table, row),
        key=f"manage_{table}",
    )
    _, primary_key = MASTER_TABLES[table]
    key = {column: selected[column] for column in primary_key}
    record_key = "_".join(str(key[column]) for column in primary_key)
    name_column = next(
        column for column in MASTER_TABLES[table][0] if column.startswith("nama_")
    )

    with st.form(f"update_{table}"):
        new_name = st.text_input(
            FIELD_LABELS[name_column],
            value=selected[name_column],
            key=f"edit_name_{table}_{record_key}",
        )
        update_submitted = st.form_submit_button(
            "Simpan perubahan", type="primary", icon=":material/edit:"
        )

    if update_submitted:
        try:
            updated = update_master_record(table, key, {name_column: new_name})
        except (ValueError, LookupError, psycopg2.Error) as error:
            show_database_error(error)
        else:
            st.success(f"Data berhasil diperbarui: {record_label(table, updated)}")
            st.rerun()

    confirmed = st.checkbox(
        "Saya yakin ingin menghapus data ini",
        key=f"confirm_delete_{table}_{record_key}",
    )
    delete_submitted = st.button(
        "Hapus data",
        type="secondary",
        icon=":material/delete:",
        disabled=not confirmed,
        key=f"delete_{table}_{record_key}",
    )

    if delete_submitted:
        try:
            deleted = delete_master_record(table, key)
        except psycopg2.Error as error:
            show_database_error(error)
        else:
            if deleted:
                st.success("Data berhasil dihapus.")
                st.rerun()
            st.warning("Data sudah tidak ditemukan.")


def render_browse(table: str) -> None:
    st.subheader("Daftar data")
    records = get_master_records(table)
    if records:
        st.dataframe(
            records,
            hide_index=True,
            alt=f"Daftar data master {TABLE_LABELS[table].lower()}",
        )
        st.caption(f"Total: {len(records)} data")
    else:
        st.info("Belum ada data pada tabel ini.")


st.set_page_config(page_title="Data master", page_icon=":material/database:")
st.title("Data master")
st.caption("Kelola hierarki data Kelompok sampai Sub rincian objek.")

try:
    initialize_database()
except (ValueError, psycopg2.Error, OSError) as error:
    st.error(f"Tidak dapat menyiapkan database: {error}")
    st.stop()

selected_label = st.selectbox("Jenis data", list(TABLES), key="selected_master")
selected_table = TABLES[selected_label]
mode = st.segmented_control(
    "Aktivitas",
    ("Tambah data", "Kelola data", "Lihat data"),
    default="Tambah data",
    key="master_action",
)

if mode == "Tambah data":
    try:
        render_create(selected_table)
    except psycopg2.Error as error:
        show_database_error(error)
elif mode == "Kelola data":
    try:
        render_manage(selected_table)
    except psycopg2.Error as error:
        show_database_error(error)
elif mode == "Lihat data":
    try:
        render_browse(selected_table)
    except psycopg2.Error as error:
        show_database_error(error)
