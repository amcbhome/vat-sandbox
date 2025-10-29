import os
import json
import uuid
import time
import urllib.parse as urlparse
from urllib.parse import parse_qs

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────
# CONFIG — set your Streamlit Cloud Secrets (see README below)
# ─────────────────────────────────────────────────────────────
HMRC_BASE = "https://test-api.service.hmrc.gov.uk"  # Sandbox
CLIENT_ID = st.secrets.get("HMRC_CLIENT_ID", "")
CLIENT_SECRET = st.secrets.get("HMRC_CLIENT_SECRET", "")
APP_URL = "https://vat-sandbox.streamlit.app"       # Your Streamlit Cloud URL
REDIRECT_URI = f"{APP_URL}/callback"
SCOPES = "read:vat write:vat"

# ─────────────────────────────────────────────────────────────
# Streamlit page setup
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="MTD VAT Sandbox", page_icon="💼", layout="centered")
st.title("💼 HMRC MTD VAT — Sandbox (Streamlit)")

# ─────────────────────────────────────────────────────────────
# Simple in-session token store
# ─────────────────────────────────────────────────────────────
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "token_expiry" not in st.session_state:
    st.session_state.token_expiry = 0

# ─────────────────────────────────────────────────────────────
# Utility: OAuth URLs
# ─────────────────────────────────────────────────────────────
def authorization_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": str(uuid.uuid4()),
    }
    return f"{HMRC_BASE}/oauth/authorize?{urlparse.urlencode(params)}"

def exchange_code_for_token(code: str):
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    r = requests.post(f"{HMRC_BASE}/oauth/token", data=data, timeout=30)
    r.raise_for_status()
    return r.json()

def refresh_access_token(refresh_token: str):
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    r = requests.post(f"{HMRC_BASE}/oauth/token", data=data, timeout=30)
    r.raise_for_status()
    return r.json()

def ensure_token():
    # refresh if expiring in < 60s
    if st.session_state.access_token and time.time() < st.session_state.token_expiry - 60:
        return st.session_state.access_token
    if st.session_state.refresh_token:
        tokens = refresh_access_token(st.session_state.refresh_token)
        st.session_state.access_token = tokens["access_token"]
        st.session_state.refresh_token = tokens.get("refresh_token", st.session_state.refresh_token)
        st.session_state.token_expiry = time.time() + tokens.get("expires_in", 3600)
        return st.session_state.access_token
    return None

# ─────────────────────────────────────────────────────────────
# Fraud Prevention Headers (lightweight sandbox demo)
# HMRC requires these; sandbox is lenient but include sensible values.
# ─────────────────────────────────────────────────────────────
def fraud_prevention_headers():
    # NOTE: For production you must collect real device/browser details.
    # These sample values are acceptable for *sandbox testing only*.
    return {
        "Gov-Client-Public-IP": "203.0.113.42",
        "Gov-Client-Public-Port": "443",
        "Gov-Client-User-Agent": "vat-sandbox/0.1.0 (Streamlit)",
        "Gov-Client-Device-Id": str(uuid.uuid4()),
        "Gov-Vendor-Product-Name": "vat-sandbox",
        "Gov-Vendor-Version": "vat-sandbox=0.1.0",
        "Gov-Vendor-License-IDs": "default",
        # Optional but helpful:
        "Gov-Client-Timezone": "UTC",
    }

# ─────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────
def api_get(path: str, params=None):
    token = ensure_token()
    if not token:
        raise RuntimeError("No access token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        **fraud_prevention_headers(),
    }
    r = requests.get(f"{HMRC_BASE}{path}", headers=headers, params=params or {}, timeout=30)
    return r

def api_post(path: str, payload: dict):
    token = ensure_token()
    if not token:
        raise RuntimeError("No access token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        **fraud_prevention_headers(),
    }
    r = requests.post(f"{HMRC_BASE}{path}", headers=headers, json=payload, timeout=30)
    return r

# ─────────────────────────────────────────────────────────────
# ROUTING: detect /callback
# ─────────────────────────────────────────────────────────────
query_params = st.query_params  # Streamlit v1.32+
if "code" in query_params:
    st.subheader("🔐 Completing OAuth Sign-in…")
    try:
        tokens = exchange_code_for_token(query_params.get("code"))
        st.session_state.access_token = tokens["access_token"]
        st.session_state.refresh_token = tokens.get("refresh_token")
        st.session_state.token_expiry = time.time() + tokens.get("expires_in", 3600)
        st.success("Signed in with HMRC Sandbox ✅")
        st.markdown("You can now access VAT API endpoints below.")
    except Exception as e:
        st.error(f"Token exchange failed: {e}")

# ─────────────────────────────────────────────────────────────
# Login card
# ─────────────────────────────────────────────────────────────
if not st.session_state.access_token:
    st.info("Connect to HMRC Sandbox with OAuth 2.0 (Authorization Code Flow).")
    if CLIENT_ID and CLIENT_SECRET:
        st.link_button("🔑 Sign in with HMRC Sandbox", authorization_url(), type="primary")
    else:
        st.error("Missing CLIENT_ID / CLIENT_SECRET in Streamlit secrets.")
    st.stop()

st.success("Connected to HMRC Sandbox ✅")
with st.expander("Show token details (debug)"):
    st.write({
        "access_token_present": bool(st.session_state.access_token),
        "refresh_token_present": bool(st.session_state.refresh_token),
        "expires_at": st.session_state.token_expiry,
    })

# ─────────────────────────────────────────────────────────────
# VAT: Obligations (useful to find a valid periodKey)
# ─────────────────────────────────────────────────────────────
st.header("📅 VAT Obligations (Sandbox)")
vrn = st.text_input("VAT Registration Number (VRN)", value="666666666")
date_from = st.text_input("From (YYYY-MM-DD)", value="2021-01-01")
date_to = st.text_input("To (YYYY-MM-DD)", value="2025-12-31")
if st.button("Fetch Obligations"):
    r = api_get(f"/organisations/vat/{vrn}/obligations", params={"from": date_from, "to": date_to})
    try:
        r.raise_for_status()
        st.json(r.json())
        st.caption("Use an open obligation’s periodKey for the submission below.")
    except Exception:
        st.error(f"Error {r.status_code}: {r.text}")

# ─────────────────────────────────────────────────────────────
# VAT: Submit Return (9 boxes)
# ─────────────────────────────────────────────────────────────
st.header("📤 Submit VAT Return (Sandbox)")
with st.form("vat_form"):
    period_key = st.text_input("periodKey (e.g., 21A1)")
    vat_fields = {
        "vatDueSales": ("VAT due on sales (Box 1)", 0.0),
        "vatDueAcquisitions": ("VAT due on EU acquisitions (Box 2)", 0.0),
        "totalVatDue": ("Total VAT due (Box 3)", 0.0),
        "vatReclaimedCurrPeriod": ("VAT reclaimed (Box 4)", 0.0),
        "netVatDue": ("Net VAT due (Box 5)", 0.0),
        "totalValueSalesExVAT": ("Value of sales excl. VAT (Box 6)", 0),
        "totalValuePurchasesExVAT": ("Value of purchases excl. VAT (Box 7)", 0),
        "totalValueGoodsSuppliedExVAT": ("Goods supplied to EU excl. VAT (Box 8)", 0),
        "totalAcquisitionsExVAT": ("Acquisitions from EU excl. VAT (Box 9)", 0),
    }
    inputs = {}
    for key, (label, default) in vat_fields.items():
        if isinstance(default, float):
            inputs[key] = st.number_input(label, min_value=0.0, value=float(default), step=0.01)
        else:
            inputs[key] = st.number_input(label, min_value=0, value=int(default), step=1)
    finalised = st.checkbox("Declaration: figures are complete and accurate", value=True)
    submit = st.form_submit_button("Submit VAT Return")

if submit:
    payload = {
        "periodKey": period_key.strip(),
        **inputs,
        "finalised": bool(finalised),
    }
    st.subheader("Outgoing JSON")
    st.code(json.dumps(payload, indent=2), language="json")

    r = api_post(f"/organisations/vat/{vrn}/returns", payload)
    if r.status_code in (200, 201):
        st.success("Return accepted ✅")
        st.json(r.json())
    else:
        st.error(f"Error {r.status_code}")
        st.code(r.text)

# ─────────────────────────────────────────────────────────────
# VAT: Liabilities (optional)
# ─────────────────────────────────────────────────────────────
st.header("💳 VAT Liabilities (Sandbox)")
if st.button("Fetch Liabilities"):
    r = api_get(f"/organisations/vat/{vrn}/liabilities")
    try:
        r.raise_for_status()
        st.json(r.json())
    except Exception:
        st.error(f"Error {r.status_code}: {r.text}")
