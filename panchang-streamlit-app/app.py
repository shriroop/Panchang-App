import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import streamlit as st

# -----------------------------
# Helper Functions
# -----------------------------
def clean(text):
    return ' '.join(text.strip().split())

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

def scrape_panchang_for_date(date_obj):
    formatted_date = date_obj.strftime("%d/%m/%Y")
    print(formatted_date)
    url = f"https://www.drikpanchang.com/panchang/day-panchang.html?date={formatted_date}"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    summary = extract_panchang_summary(soup)
    rahukalam_df = extract_named_table(soup, "Inauspicious Timings")
    choghadiya_df = extract_named_table(soup, "Choghadiya (Day)")

    summary_df = pd.DataFrame(list(summary.items()), columns=["Category", "Details"])

    return summary_df, rahukalam_df, choghadiya_df

# -----------------------------
# Streamlit Web App
# -----------------------------
st.set_page_config(page_title="Panchang Viewer", layout="wide")
st.title("📿 Daily Panchang Scraper")

selected_date = st.date_input("Select a Date")

if st.button("Get Panchang"):
    with st.spinner("Fetching Panchang data..."):
        try:
            summary_df, rahukalam_df, choghadiya_df = scrape_panchang_for_date(selected_date)

            st.success(f"Panchang for {selected_date.strftime('%d %B %Y')}")
            st.subheader("🧘 Panchang Summary")
            st.dataframe(summary_df, use_container_width=True)

            st.subheader("⛔ Inauspicious Timings")
            st.dataframe(rahukalam_df, use_container_width=True)

            st.subheader("🕒 Choghadiya (Day)")
            st.dataframe(choghadiya_df, use_container_width=True)

            with pd.ExcelWriter("panchang_data.xlsx") as writer:
                summary_df.to_excel(writer, sheet_name="Summary", index=False)
                rahukalam_df.to_excel(writer, sheet_name="Inauspicious Timings", index=False)
                choghadiya_df.to_excel(writer, sheet_name="Choghadiya Day", index=False)

            with open("panchang_data.xlsx", "rb") as f:
                st.download_button("📥 Download Excel", f, file_name="panchang_data.xlsx")

        except Exception as e:
            st.error(f"Failed to fetch Panchang data: {e}")
