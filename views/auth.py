import os

import streamlit as st


def get_operator_password() -> str | None:
    """Site-operator password (create/manage campaigns). Reuses the ADMIN_PASSWORD
    secret from the single-tenant era; shared between admin_panel.py and
    super_admin.py so it isn't defined twice."""
    return st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD"))
