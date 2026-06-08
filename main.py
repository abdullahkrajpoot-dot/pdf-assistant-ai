"""Compatibility entrypoint for Streamlit Cloud.

The real app lives in streamlit_app.py. Some deployments are configured to
launch main.py, so importing streamlit_app keeps both entrypoints working.
"""

import streamlit_app  # noqa: F401
