# vat-sandbox
# vat-sandbox — HMRC MTD VAT (Sandbox) with Streamlit

A demo Streamlit app that authenticates with **HMRC Sandbox** (Authorization Code Flow) and:
- Fetches VAT **obligations**
- Submits a **VAT return** (9 boxes)
- Fetches **liabilities**

## 1) HMRC Developer Hub
- Create a developer account and **register an app**
- Enable **VAT (MTD)** API
- Scopes: `read:vat write:vat`
- OAuth Redirect URI: `https://vat-sandbox.streamlit.app/callback`
- Note your **CLIENT_ID** and **CLIENT_SECRET**

## 2) Deploy on Streamlit Cloud
- Create a new app from your GitHub repo
- In Streamlit **Secrets** add:
  - `HMRC_CLIENT_ID = "your_client_id"`
  - `HMRC_CLIENT_SECRET = "your_client_secret"`

## 3) Use the App
- Click **Sign in with HMRC Sandbox**
- Use a **Sandbox Government Gateway** test user
- Get **Obligations** → copy a `periodKey`
- Fill the 9 VAT boxes → **Submit Return**
- Works only against Sandbox base URL: `https://test-api.service.hmrc.gov.uk/`

## Notes
- Includes lightweight **Fraud-Prevention Headers** suitable for sandbox.
- For production you must collect real device/browser metadata per HMRC guidance.
