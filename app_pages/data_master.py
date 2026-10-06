from collections.abc import Mapping
from typing import Any

import psycopg2
import streamlit as st

from database import (
    MASTER_TABLES,
    create_master_record,
    create_tahun_anggaran,
    delete_master_record,
    delete_tahun_anggaran,
    get_tahun_anggaran,
    get_master_records,
    update_tahun_anggaran,
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
YEAR_BUDGET_LABEL = "Tahun anggaran"


def render_year_budget(mode: str) -> None:
    if mode == "Tambah data":
        with st.form("create_tahun_anggaran", clear_on_submit=True):
            nama_tahun = st.text_input(
                "Nama tahun", key="create_tahun_anggaran_nama"
            )
            keterangan = st.text_area(
                "Keterangan", key="create_tahun_anggaran_keterangan"
            )
            submitted = st.form_submit_button(
                "Simpan data", type="primary", icon=":material/save:"
            )

        if submitted:
            try:
                record = create_tahun_anggaran(nama_tahun, keterangan)
            except (ValueError, psycopg2.Error) as error:
                show_database_error(error)
            else:
                st.success(
                    f"Tahun anggaran {record['nama_tahun']} berhasil ditambahkan."
                )
                st.rerun()
        return

    try:
        records = get_tahun_anggaran()
    except psycopg2.Error as error:
        show_database_error(error)
        return

    if mode == "Lihat data":
        st.subheader("Daftar tahun anggaran")
        if records:
            st.dataframe(
                records,
                hide_index=True,
                alt="Daftar tahun anggaran beserta keterangan",
            )
            st.caption(f"Total: {len(records)} data")
        else:
            st.info("Belum ada data tahun anggaran.")
        return

    st.subheader("Ubah atau hapus tahun anggaran")
    if not records:
        st.info("Belum ada data tahun anggaran untuk dikelola.")
        return

    selected = st.selectbox(
        "Pilih tahun anggaran",
        records,
        format_func=lambda row: f"{row['nama_tahun']} (ID: {row['id']})",
        key="manage_tahun_anggaran",
    )
    with st.form("update_tahun_anggaran"):
        nama_tahun = st.text_input(
            "Nama tahun",
            value=selected["nama_tahun"],
            key=f"edit_tahun_anggaran_nama_{selected['id']}",
        )
        keterangan = st.text_area(
            "Keterangan",
            value=selected["keterangan"] or "",
            key=f"edit_tahun_anggaran_keterangan_{selected['id']}",
        )
        update_submitted = st.form_submit_button(
            "Simpan perubahan", type="primary", icon=":material/edit:"
        )

    if update_submitted:
        try:
            updated = update_tahun_anggaran(
                selected["id"], nama_tahun, keterangan
            )
        except (ValueError, LookupError, psycopg2.Error) as error:
            show_database_error(error)
        else:
            st.success(f"Tahun anggaran {updated['nama_tahun']} berhasil diperbarui.")
            st.rerun()

    confirmed = st.checkbox(
        "Saya yakin ingin menghapus tahun anggaran ini",
        key=f"confirm_delete_tahun_anggaran_{selected['id']}",
    )
    if st.button(
        "Hapus data",
        type="secondary",
        icon=":material/delete:",
        disabled=not confirmed,
        key=f"delete_tahun_anggaran_{selected['id']}",
    ):
        try:
            deleted = delete_tahun_anggaran(selected["id"])
        except psycopg2.Error as error:
            show_database_error(error)
        else:
            if deleted:
                st.success("Tahun anggaran berhasil dihapus.")
                st.rerun()
            st.warning("Tahun anggaran sudah tidak ditemukan.")


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


st.title("Data master")
st.caption("Kelola data master anggaran dan hierarki rincian objek.")

selected_label = st.selectbox(
    "Jenis data",
    [*TABLES, YEAR_BUDGET_LABEL],
    key="selected_master",
)
mode = st.segmented_control(
    "Aktivitas",
    ("Tambah data", "Kelola data", "Lihat data"),
    default="Tambah data",
    key="master_action",
)

if selected_label == YEAR_BUDGET_LABEL:
    render_year_budget(mode)
else:
    selected_table = TABLES[selected_label]
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
