import psycopg2
import streamlit as st

from database import create_master_tables


@st.cache_resource
def initialize_database() -> None:
    create_master_tables()

try:
    initialize_database()
except (ValueError, psycopg2.Error, OSError) as error:
    st.error(f"Tidak dapat menyiapkan database: {error}")
    st.stop()

page = st.navigation(
    [
        st.Page(
            "app_pages/data_master.py",
            title="Data Master",
            icon=":material/database:",
        ),
        st.Page(
            "app_pages/dashboard.py",
            title="Dashboard",
            icon=":material/dashboard:",
        ),
    ],
    position="sidebar",
)
page.run()
