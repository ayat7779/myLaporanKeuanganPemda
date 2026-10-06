from collections.abc import Mapping
from typing import Any, Literal

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
MasterAction = Literal["create", "update", "delete"]


def complete_action(message: str, clear_keys: tuple[str, ...] = ()) -> None:
    st.session_state["master_action_notice"] = message
    st.session_state["master_clear_keys"] = clear_keys
    st.rerun()


@st.dialog("Konfirmasi")
def confirm_master_action(
    action: MasterAction,
    table: str,
    values: Mapping[str, Any] | None = None,
    key: Mapping[str, Any] | None = None,
    clear_keys: tuple[str, ...] = (),
    description: str = "",
) -> None:
    prompts = {
        "create": "Tambahkan data ini?",
        "update": "Simpan perubahan ini?",
        "delete": "Hapus data ini? Tindakan ini tidak dapat dibatalkan.",
    }
    st.write(prompts[action])
    details = [description] if description else []
    if values:
        details.extend(
            f"{FIELD_LABELS.get(column, column)}: {value}"
            for column, value in values.items()
        )
    if details:
        st.caption(" · ".join(details))

    confirm_label = {
        "create": "Tambah",
        "update": "Simpan",
        "delete": "Hapus",
    }[action]
    confirm_column, cancel_column = st.columns(2)
    if confirm_column.button(
        confirm_label,
        type="primary",
        key=f"confirm_master_{action}_{table}",
    ):
        try:
            if action == "create":
                record = create_master_record(table, values or {})
                message = f"Data berhasil ditambahkan: {record_label(table, record)}"
            elif action == "update":
                record = update_master_record(table, key or {}, values or {})
                message = f"Data berhasil diperbarui: {record_label(table, record)}"
            else:
                deleted = delete_master_record(table, key or {})
                if not deleted:
                    st.warning("Data sudah tidak ditemukan.")
                    return
                message = "Data berhasil dihapus."
        except (ValueError, LookupError, psycopg2.Error) as error:
            show_database_error(error)
        else:
            complete_action(message, clear_keys)

    if cancel_column.button("Batal", key=f"cancel_master_{action}_{table}"):
        st.rerun()


@st.dialog("Konfirmasi")
def confirm_year_budget_action(
    action: MasterAction,
    nama_tahun: str = "",
    keterangan: str = "",
    id: int | None = None,
    clear_keys: tuple[str, ...] = (),
) -> None:
    prompts = {
        "create": "Tambahkan tahun anggaran ini?",
        "update": "Simpan perubahan ini?",
        "delete": "Hapus tahun anggaran ini? Tindakan ini tidak dapat dibatalkan.",
    }
    st.write(prompts[action])
    details = [nama_tahun]
    if keterangan:
        details.append(keterangan)
    st.caption(" · ".join(details))

    confirm_label = {
        "create": "Tambah",
        "update": "Simpan",
        "delete": "Hapus",
    }[action]
    confirm_column, cancel_column = st.columns(2)
    if confirm_column.button(
        confirm_label,
        type="primary",
        key=f"confirm_year_budget_{action}",
    ):
        try:
            if action == "create":
                record = create_tahun_anggaran(nama_tahun, keterangan)
                message = f"Tahun anggaran {record['nama_tahun']} berhasil ditambahkan."
            elif action == "update":
                if id is None:
                    raise ValueError("ID tahun anggaran wajib diisi")
                record = update_tahun_anggaran(id, nama_tahun, keterangan)
                message = f"Tahun anggaran {record['nama_tahun']} berhasil diperbarui."
            else:
                if id is None:
                    raise ValueError("ID tahun anggaran wajib diisi")
                deleted = delete_tahun_anggaran(id)
                if not deleted:
                    st.warning("Tahun anggaran sudah tidak ditemukan.")
                    return
                message = "Tahun anggaran berhasil dihapus."
        except (ValueError, LookupError, psycopg2.Error) as error:
            show_database_error(error)
        else:
            complete_action(message, clear_keys)

    if cancel_column.button("Batal", key=f"cancel_year_budget_{action}"):
        st.rerun()


def render_year_budget(mode: str) -> None:
    if mode == "Tambah data":
        with st.form("create_tahun_anggaran"):
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
            confirm_year_budget_action(
                "create",
                nama_tahun,
                keterangan,
                clear_keys=(
                    "create_tahun_anggaran_nama",
                    "create_tahun_anggaran_keterangan",
                ),
            )
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
        confirm_year_budget_action(
            "update",
            nama_tahun,
            keterangan,
            selected["id"],
            (
                f"edit_tahun_anggaran_nama_{selected['id']}",
                f"edit_tahun_anggaran_keterangan_{selected['id']}",
            ),
        )

    if st.button(
        "Hapus data",
        type="secondary",
        icon=":material/delete:",
        key=f"delete_tahun_anggaran_{selected['id']}",
    ):
        confirm_year_budget_action(
            "delete",
            selected["nama_tahun"],
            selected["keterangan"] or "",
            selected["id"],
        )


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
    with st.form(f"create_{table}"):
        for column in editable_columns:
            values[column] = st.text_input(
                FIELD_LABELS[column], key=f"create_{table}_{column}"
            )
        submitted = st.form_submit_button(
            "Simpan data", type="primary", icon=":material/save:"
        )

    if submitted:
        confirm_master_action(
            "create",
            table,
            values=values,
            clear_keys=tuple(
                f"create_{table}_{column}" for column in editable_columns
            ),
            description=f"Jenis data: {TABLE_LABELS[table]}",
        )


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
        confirm_master_action(
            "update",
            table,
            values={name_column: new_name},
            key=key,
            clear_keys=(f"edit_name_{table}_{record_key}",),
            description=record_label(
                table, {**selected, name_column: new_name}
            ),
        )

    delete_submitted = st.button(
        "Hapus data",
        type="secondary",
        icon=":material/delete:",
        key=f"delete_{table}_{record_key}",
    )

    if delete_submitted:
        confirm_master_action(
            "delete",
            table,
            key=key,
            description=record_label(table, selected),
        )


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
for widget_key in st.session_state.pop("master_clear_keys", ()):
    st.session_state.pop(widget_key, None)
notice = st.session_state.pop("master_action_notice", None)
if notice:
    st.success(notice)

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
