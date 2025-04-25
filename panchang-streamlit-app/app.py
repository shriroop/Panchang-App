import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import time
import socket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -----------------------------
# Helper Functions
# -----------------------------
def clean(text):
    return ' '.join(text.strip().split())

def is_connected(host="8.8.8.8", port=53, timeout=5):
    # -----------------------------
    # Check internet connectivity by attempting to connect to a DNS server.
    # -----------------------------
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except OSError:
        return False
        
def extract_panchang_summary(soup):
    summary_data = {}
    keys = soup.select("div#dpTable p strong")
    for key in keys:
        parent = key.find_parent("p")
        if parent:
            full_text = clean(parent.get_text())
            k = clean(key.get_text().replace(":", ""))
            v = clean(full_text.replace(key.get_text(), ''))
            summary_data[k] = v
    return summary_data

def extract_named_table(soup, heading_text):
    table = soup.find("h2", string=heading_text)
    if table:
        next_table = table.find_next("table")
        headers = [clean(th.get_text()) for th in next_table.select("th")]
        rows = []
        for tr in next_table.select("tr")[1:]:
            row = [clean(td.get_text()) for td in tr.select("td")]
            rows.append(row)
        return pd.DataFrame(rows, columns=headers)
    return pd.DataFrame()

def scrape_panchang_for_date(date_obj, max_retries=3, backoff_factor=2):
    formatted_date = date_obj.strftime("%d/%m/%Y")
    url = f"https://www.drikpanchang.com/panchang/day-panchang.html?date={formatted_date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    session = requests.Session()
    retries = Retry(total=max_retries, backoff_factor=backoff_factor,
                    status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    if not is_connected():
        return {"Error": "No internet connection. Please check your network."}

    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        #response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        summary = extract_panchang_summary(soup)
        rahukalam_df = extract_named_table(soup, "Inauspicious Timings")
        choghadiya_df = extract_named_table(soup, "Choghadiya (Day)")

        summary_df = pd.DataFrame(list(summary.items()), columns=["Category", "Details"])

        return summary_df, rahukalam_df, choghadiya_df, formatted_date
     
    except requests.RequestException as e:
        return {"Error": f"Failed to fetch data: {e}"}

# -----------------------------
# Streamlit Web App
# -----------------------------
st.set_page_config(page_title="Panchang Viewer", layout="wide")
st.title("📿 Daily Panchang Scraper")

selected_date = st.date_input("Select a Date")

if st.button("Get Panchang"):
    with st.spinner("Fetching Panchang data..."):
        try:
            summary_df, rahukalam_df, choghadiya_df, formatted_date = scrape_panchang_for_date(selected_date)

            st.success(f"Panchang for {selected_date.strftime('%d %B %Y')}")
            st.subheader("🧘 Panchang Summary")
            st.dataframe(summary_df, use_container_width=True)

            st.subheader("⛔ Inauspicious Timings")
            st.dataframe(rahukalam_df, use_container_width=True)

            st.subheader("🕒 Choghadiya (Day)")
            st.dataframe(choghadiya_df, use_container_width=True)

            st.subheader(formatted_date)
            
            with pd.ExcelWriter("panchang_data.xlsx") as writer:
                summary_df.to_excel(writer, sheet_name="Summary", index=False)
                rahukalam_df.to_excel(writer, sheet_name="Inauspicious Timings", index=False)
                choghadiya_df.to_excel(writer, sheet_name="Choghadiya Day", index=False)

            with open("panchang_data.xlsx", "rb") as f:
                st.download_button("📥 Download Excel", f, file_name="panchang_data.xlsx")

        except Exception as e:
            st.error(f"Failed to fetch Panchang data: {e}")
