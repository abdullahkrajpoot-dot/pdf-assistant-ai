"""Compatibility entrypoint for Streamlit Cloud.

The real app lives in streamlit_app.py. Some deployments are configured to
launch main.py, so this delegates to the production Streamlit app.
"""

from streamlit_app import main


main()
