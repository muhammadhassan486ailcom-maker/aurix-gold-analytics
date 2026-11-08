
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import altair as alt
import streamlit as st
from dotenv import load_dotenv


# =====================================================
# 1. AURIX PROJECT CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "gold_prices.csv"
ENV_FILE = BASE_DIR / ".env"

API_URL = "https://api.gold-api.com/history"

load_dotenv(ENV_FILE)

st.set_page_config(
    page_title="AURIX | Gold Analytics",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================
# 2. PROFESSIONAL DASHBOARD DESIGN
# =====================================================

st.markdown("""
<style>

    .stApp {
        background-color: #0e1117;
        color: #f8fafc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .aurix-header {
        background: linear-gradient(
            120deg,
            #17202e,
            #302819
        );
        padding: 30px;
        border: 1px solid #66532e;
        border-radius: 15px;
        margin-bottom: 25px;
    }

    .aurix-header h1 {
        color: #f2c66d !important;
        font-size: 36px;
        margin-bottom: 8px;
    }

    .aurix-header p {
        color: #d1d5db !important;
        font-size: 15px;
        margin-bottom: 0;
    }

    .section-title {
        color: #f2c66d !important;
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 15px;
    }

    [data-testid="stMetric"] {
        background: #171e29;
        border: 1px solid #364152;
        border-radius: 12px;
        padding: 18px;
    }

    [data-testid="stMetricLabel"] {
        color: #d1d5db !important;
    }

    [data-testid="stMetricValue"] {
        color: #f9fafb !important;
    }

    [data-testid="stMetricDelta"] {
        font-weight: 600;
    }

    [data-testid="stSidebar"] {
        background-color: #141a23;
    }

    .footer {
        text-align: center;
        color: #9ca3af;
        padding: 20px;
        font-size: 12px;
    }

</style>
""", unsafe_allow_html=True)


# =====================================================
# 3. API KEY MANAGEMENT
# =====================================================

def get_api_key():

    # First check Streamlit Cloud secrets
    try:
        key = st.secrets.get("GOLD_API_KEY", "")
    except Exception:
        key = ""

    # Then check local .env file
    if not key:
        key = os.getenv("GOLD_API_KEY", "")

    return key.strip() if key else ""


# =====================================================
# 4. DATA CLEANING
# =====================================================

def clean_gold_data(df):

    required_columns = [
        "date",
        "price_usd"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Missing required column: {column}"
            )

    df = df[required_columns].copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["price_usd"] = pd.to_numeric(
        df["price_usd"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["date", "price_usd"]
    )

    df = df[df["price_usd"] > 0]

    df = df.sort_values("date")

    df = df.drop_duplicates(
        subset=["date"],
        keep="last"
    )

    if df.empty:
        raise ValueError(
            "No valid gold-price records available."
        )

    return df.reset_index(drop=True)


# =====================================================
# 5. DOWNLOAD GOLD DATA FROM GOLDAPI
# =====================================================

def download_gold_data():

    api_key = get_api_key()

    if not api_key:
        raise ValueError(
            "API key not found. Please check your .env file."
        )

    today = datetime.now(timezone.utc).date()

    last_complete_day = today - timedelta(days=1)

    start_date = datetime.combine(
        last_complete_day - timedelta(days=29),
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    end_date = (
        datetime.combine(
            last_complete_day + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc
        ) - timedelta(seconds=1)
    )

    params = {
        "symbol": "XAU",
        "startTimestamp": int(start_date.timestamp()),
        "endTimestamp": int(end_date.timestamp()),
        "groupBy": "day",
        "aggregation": "avg",
        "orderBy": "asc"
    }

    headers = {
        "x-api-key": api_key
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=headers,
        timeout=30
    )

    if response.status_code == 401:
        raise ValueError("Invalid GoldAPI API key.")

    if response.status_code == 403:
        raise ValueError("GoldAPI access forbidden.")

    if response.status_code == 429:
        raise ValueError("GoldAPI request limit reached.")

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError(
            "Unexpected response received from GoldAPI."
        )

    records = []

    for item in data:

        if not isinstance(item, dict):
            continue

        if "day" not in item or "avg_price" not in item:
            continue

        try:
            records.append({
                "date": item["day"],
                "price_usd": float(item["avg_price"])
            })
        except (ValueError, TypeError):
            continue

    if not records:
        raise ValueError(
            "GoldAPI returned no valid gold-price records."
        )

    df = pd.DataFrame(records)

    df = clean_gold_data(df)

    # Save newly downloaded data locally
    df.to_csv(
        CSV_FILE,
        index=False,
        date_format="%Y-%m-%d"
    )

    return df


# =====================================================
# 6. LOAD SAVED GOLD PRICE DATA
# =====================================================

def load_saved_data():

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            "gold_prices.csv was not found."
        )

    df = pd.read_csv(CSV_FILE)

    return clean_gold_data(df)



# =========================================
# 7. AURIX DASHBOARD HEADER
# =========================================

st.markdown(
    '<div class="aurix-header">'
    '<h1>🥇 AURIX | GOLD ANALYTICS</h1>'
    '<p>Intelligent Gold Price Monitoring, '
    'Historical Trend Analysis and Moving Average Insights.</p>'
    '</div>',
    unsafe_allow_html=True
)


# =====================================================
# 8. SIDEBAR CONTROLS
# =====================================================

with st.sidebar:

    st.title("🥇 AURIX")

    st.caption("GOLD ANALYTICS PLATFORM")

    st.divider()

    st.subheader("Dashboard Controls")

    refresh_clicked = st.button(
        "🔄 Refresh Gold Data",
        type="primary",
        width="stretch"
    )

    st.divider()

    st.subheader("Market Information")

    st.write("**Asset:** Gold (XAU)")

    st.write("**Currency:** USD")

    st.write("**Data Source:** GoldAPI")

    st.write("**Moving Average:** 7 Days")

    st.divider()

    st.caption(
        "AURIX Gold Analytics Platform"
    )


# =====================================================
# 9. LOAD AND REFRESH DATA
# =====================================================

data_source = "Saved local CSV"

if refresh_clicked:

    with st.spinner(
        "Connecting to GoldAPI and downloading data..."
    ):

        try:

            df = download_gold_data()

            data_source = "Fresh GoldAPI download"

            st.success(
                f"Successfully downloaded {len(df)} records."
            )

        except Exception as error:

            st.error(
                f"Data refresh failed: {error}"
            )

            try:
                df = load_saved_data()

                st.warning(
                    "Showing previously saved gold-price data."
                )

            except Exception as local_error:

                st.error(str(local_error))

                st.stop()

else:

    try:

        df = load_saved_data()

    except Exception as error:

        st.error(str(error))

        st.info(
            "Please check gold_prices.csv or use the refresh button."
        )

        st.stop()


# =====================================================
# 10. CALCULATE GOLD PRICE INDICATORS
# =====================================================

df = df.copy()

df["moving_average_7d_usd"] = (
    df["price_usd"].rolling(
        window=7,
        min_periods=7
    ).mean()
)

latest_price = float(
    df["price_usd"].iloc[-1]
)

latest_date = df["date"].iloc[-1]

previous_price = None

if len(df) >= 2:

    previous_price = float(
        df["price_usd"].iloc[-2]
    )

if previous_price is not None:

    price_change = latest_price - previous_price

    price_change_pct = (
        price_change / previous_price
    ) * 100

else:

    price_change = None

    price_change_pct = None

latest_ma = df[
    "moving_average_7d_usd"
].iloc[-1]


# =====================================================
# 11. MARKET OVERVIEW - KPI CARDS
# =====================================================

st.markdown(
    '<p class="section-title">📊 Market Overview</p>',
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        label="Latest Gold Price",
        value=f"${latest_price:,.2f}"
    )

with col2:

    st.metric(
        label="Price Change",
        value=(
            f"${price_change:+,.2f}"
            if price_change is not None
            else "N/A"
        ),
        delta=(
            f"{price_change_pct:+.2f}%"
            if price_change_pct is not None
            else None
        )
    )

with col3:

    st.metric(
        label="7-Day Moving Average",
        value=(
            f"${latest_ma:,.2f}"
            if pd.notna(latest_ma)
            else "N/A"
        )
    )

with col4:

    st.metric(
        label="Available Records",
        value=f"{len(df)} Days"
    )


st.caption(
    f"Latest recorded date: {latest_date.date()} "
    f"| Price is in USD per troy ounce."
)


# =====================================================
# 12. CHART FILTER
# =====================================================

st.divider()

st.markdown(
    '<p class="section-title">📈 Gold Price Trend Analysis</p>',
    unsafe_allow_html=True
)

range_option = st.selectbox(
    "Select chart period",
    [
        "Last 7 Records",
        "Last 14 Records",
        "Last 30 Records",
        "All Available Data"
    ],
    index=2
)

if range_option == "Last 7 Records":

    chart_df = df.tail(7)

elif range_option == "Last 14 Records":

    chart_df = df.tail(14)

elif range_option == "Last 30 Records":

    chart_df = df.tail(30)

else:

    chart_df = df.copy()


# =====================================================
# 13. PREPARE INTERACTIVE CHART DATA
# =====================================================

chart_data = chart_df[
    [
        "date",
        "price_usd",
        "moving_average_7d_usd"
    ]
].copy()

chart_data = chart_data.melt(
    id_vars=["date"],
    value_vars=[
        "price_usd",
        "moving_average_7d_usd"
    ],
    var_name="indicator",
    value_name="price"
)

chart_data["indicator"] = (
    chart_data["indicator"].map({
        "price_usd": "Daily Average Gold Price",
        "moving_average_7d_usd": "7-Day Moving Average"
    })
)

chart_data = chart_data.dropna(
    subset=["price"]
)


# =====================================================
# 14. BUILD INTERACTIVE ALTAIR CHART
# =====================================================

chart = alt.Chart(
    chart_data
).mark_line(
    point=True,
    strokeWidth=3
).encode(

    x=alt.X(
        "date:T",
        title="Date",
        axis=alt.Axis(
            labelAngle=-35,
            format="%d %b"
        )
    ),

    y=alt.Y(
        "price:Q",
        title="Gold Price (USD)",
        scale=alt.Scale(
            zero=False,
            nice=True
        ),
        axis=alt.Axis(
            format=",.0f"
        )
    ),

    color=alt.Color(
        "indicator:N",
        title="Price Indicator",
        scale=alt.Scale(
            domain=[
                "Daily Average Gold Price",
                "7-Day Moving Average"
            ],
            range=[
                "#F2C66D",
                "#60A5FA"
            ]
        )
    ),

    tooltip=[
        alt.Tooltip(
            "date:T",
            title="Date",
            format="%Y-%m-%d"
        ),

        alt.Tooltip(
            "price:Q",
            title="Gold Price (USD)",
            format=",.2f"
        ),

        alt.Tooltip(
            "indicator:N",
            title="Indicator"
        )
    ]

).properties(
    height=430
).configure(

    background="#0e1117"

).configure_axis(

    labelColor="#D1D5DB",
    titleColor="#F2C66D",
    gridColor="#354052"

).configure_legend(

    labelColor="#D1D5DB",
    titleColor="#F2C66D",
    orient="bottom"

).configure_view(
    strokeOpacity=0
)


st.altair_chart(
    chart,
    width="stretch"
)


# =====================================================
# 15. TREND INSIGHT
# =====================================================

st.divider()

st.markdown(
    '<p class="section-title">💡 Trend Insight</p>',
    unsafe_allow_html=True
)

if pd.notna(latest_ma):

    difference = latest_price - latest_ma

    difference_pct = (
        difference / latest_ma
    ) * 100

    if latest_price > latest_ma:

        st.success(
            "The latest gold price is ABOVE "
            "its 7-day moving average."
        )

    elif latest_price < latest_ma:

        st.warning(
            "The latest gold price is BELOW "
            "its 7-day moving average."
        )

    else:

        st.info(
            "The latest gold price is equal "
            "to its 7-day moving average."
        )

    st.write(
        f"Price difference from moving average: "
        f"${difference:+,.2f} ({difference_pct:+.2f}%)."
    )

else:

    st.info(
        "At least seven price records are needed "
        "to calculate the moving average."
    )


# =====================================================
# 16. PRICE PERFORMANCE SUMMARY
# =====================================================

st.divider()

st.markdown(
    '<p class="section-title">📉 Price Performance</p>',
    unsafe_allow_html=True
)

first_price = float(
    df["price_usd"].iloc[0]
)

highest_price = float(
    df["price_usd"].max()
)

lowest_price = float(
    df["price_usd"].min()
)

period_change = latest_price - first_price

period_change_pct = (
    period_change / first_price
) * 100

p1, p2, p3 = st.columns(3)

with p1:

    st.metric(
        "Highest Recorded Price",
        f"${highest_price:,.2f}"
    )

with p2:

    st.metric(
        "Lowest Recorded Price",
        f"${lowest_price:,.2f}"
    )

with p3:

    st.metric(
        "Period Price Change",
        f"${period_change:+,.2f}",
        delta=f"{period_change_pct:+.2f}%"
    )


# =====================================================
# 17. HISTORICAL GOLD PRICE TABLE
# =====================================================

st.divider()

st.markdown(
    '<p class="section-title">📋 Historical Gold Price Records</p>',
    unsafe_allow_html=True
)

display_data = df.sort_values(
    "date",
    ascending=False
).copy()

display_data["date"] = (
    display_data["date"].dt.strftime("%Y-%m-%d")
)

display_data = display_data.rename(
    columns={
        "date": "Date",
        "price_usd": "Daily Average Price (USD)",
        "moving_average_7d_usd": "7-Day Moving Average (USD)"
    }
)

st.dataframe(
    display_data,
    width="stretch",
    hide_index=True,
    column_config={
        "Daily Average Price (USD)": st.column_config.NumberColumn(
            format="$%.2f"
        ),
        "7-Day Moving Average (USD)": st.column_config.NumberColumn(
            format="$%.2f"
        )
    }
)


# =====================================================
# 18. DOWNLOAD AURIX DATA
# =====================================================

st.divider()

st.markdown(
    '<p class="section-title">⬇️ Export Your Analysis</p>',
    unsafe_allow_html=True
)

download_df = df.copy()

csv_file = download_df.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download AURIX Gold Analysis CSV",
    data=csv_file,
    file_name="aurix_gold_analysis.csv",
    mime="text/csv",
    width="stretch"
)


# =====================================================
# 19. DATA SOURCE INFORMATION
# =====================================================

st.divider()

st.markdown(
    f"""
    **Data Source:** GoldAPI

    **Asset:** Gold (XAU/USD)

    **Last Recorded Date:** {latest_date.date()}

    **Number of Records:** {len(df)}

    **Data Status:** {data_source}
    """
)


# =====================================================
# 20. AURIX FOOTER
# =====================================================

st.markdown("""
<div class="footer">

    <strong>AURIX GOLD ANALYTICS</strong>

    <br><br>

    Historical Gold Price Monitoring
    | Moving Average Analysis
    | Financial Data Visualization

    <br><br>

    Educational analytical tool.
    Indicators are not financial advice or guaranteed
    trading recommendations.

</div>
""", unsafe_allow_html=True)
