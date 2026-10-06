import psycopg2
import streamlit as st

from database import COUNT_TABLES, get_master_counts


TABLE_LABELS = {
    "master_kelompok": "Kelompok",
    "master_jenis": "Jenis",
    "master_objek": "Objek",
    "master_rincian_objek": "Rincian objek",
    "master_sub_rincian_objek": "Sub rincian objek",
    "master_tahun_anggaran": "Tahun anggaran",
}


st.title("Dashboard")
st.caption("Ringkasan jumlah data master yang tersimpan.")

try:
    counts = get_master_counts()
except psycopg2.Error as error:
    st.error(f"Tidak dapat mengambil ringkasan data: {error}")
else:
    for start in range(0, len(COUNT_TABLES), 3):
        table_group = list(COUNT_TABLES)[start : start + 3]
        columns = st.columns(len(table_group))
        for column, table in zip(columns, table_group):
            with column.container(border=True):
                st.metric(TABLE_LABELS[table], counts[table])

    total = sum(counts.values())
    st.metric("Total seluruh data master", total)
