import streamlit as st
import urllib.parse as urlparse

st.title("VAT Sandbox OAuth Redirect")

query_params = st.experimental_get_query_params()

if "code" in query_params:
    code = query_params["code"][0]
    st.success("✅ Authorization code received!")
    st.code(code)
    st.write("Copy the above code and paste it back into ChatGPT.")
else:
    st.warning("No authorization code provided.")
