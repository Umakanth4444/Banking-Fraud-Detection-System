
import os
import pandas as pd
import streamlit as st
import plotly.express as px

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Banking Fraud Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# --------------------------------------------------
# 2. DATABASE CONNECTION
# --------------------------------------------------

@st.cache_resource
def get_engine():
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "banking_fraud_project")
    )

    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=60)
def load_transactions():
    engine = get_engine()

    query = text("SELECT * FROM public.transactions")

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    if df.empty:
        raise ValueError("No transaction records found.")

    return df


@st.cache_data(ttl=60)
def load_suspicious_transactions():
    """Load transactions flagged by the PostgreSQL investigation view."""
    engine = get_engine()
    query = text("""
        SELECT *
        FROM public.vw_suspicious_transactions
        ORDER BY flag_count DESC, transaction_date DESC
    """)
    with engine.connect() as connection:
        return pd.read_sql(query, connection)


# --------------------------------------------------
# 3. COLUMN DETECTION
# Supports different column names
# --------------------------------------------------

def find_column(df, candidates):
    for candidate in candidates:
        for col in df.columns:
            if col.lower() == candidate.lower():
                return col
    return None


# --------------------------------------------------
# 4. LOAD DATA
# --------------------------------------------------

st.markdown(
    """
    <h1 style='color:#65B5FF;'>
    🏦 Banking Fraud Intelligence
    </h1>
    <p style='color:gray;'>
    Interactive PostgreSQL-powered fraud monitoring
    and transaction analytics platform
    </p>
    """,
    unsafe_allow_html=True
)

try:
    df = load_transactions()

except Exception as e:
    st.error(f"Database connection or loading error: {e}")
    st.info(
        "Check your PostgreSQL server, database name, "
        "password and transactions table."
    )
    st.stop()


# Detect available columns

transaction_id = find_column(
    df, ["transaction_id", "id"]
)

customer_id = find_column(
    df, ["customer_id", "account_id"]
)

amount_col = find_column(
    df, ["transaction_amount", "amount"]
)

date_col = find_column(
    df, ["transaction_date", "transaction_time", "timestamp"]
)

category_col = find_column(
    df, ["merchant_category", "category"]
)

channel_col = find_column(
    df, ["payment_channel", "channel"]
)

type_col = find_column(
    df, ["transaction_type", "type"]
)

location_col = find_column(
    df, ["location", "home_city", "city"]
)

fraud_col = find_column(
    df, ["is_fraud", "fraud"]
)

if not fraud_col:
    st.error("Fraud indicator column is missing.")
    st.stop()

if not amount_col:
    st.error("Transaction amount column is missing.")
    st.stop()


# Standardize fraud values

df[fraud_col] = (
    df[fraud_col]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes", "y", "fraud"])
)

df[amount_col] = pd.to_numeric(
    df[amount_col], errors="coerce"
).fillna(0)

if date_col:
    df[date_col] = pd.to_datetime(
        df[date_col], errors="coerce"
    )

# --------------------------------------------------
# 5. SIDEBAR NAVIGATION
# --------------------------------------------------

st.sidebar.title("🏦 Fraud Analytics")

st.sidebar.caption("BANKING INTELLIGENCE PLATFORM")

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Overview",
        "Transaction Explorer",
        "Fraud Analysis",
        "Customer Risk",
        "Payment Channels",
        "Reports",
        "Manual Fraud Investigation"
    ]
)

st.sidebar.divider()

st.sidebar.subheader("🔎 Transaction Filters")

# Fraud status filter

fraud_filter = st.sidebar.selectbox(
    "Fraud Status",
    ["All Transactions", "Fraudulent", "Non-Fraudulent"]
)

filtered = df.copy()

# Date filter

if date_col:
    valid_dates = df[date_col].dropna()

    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        date_range = st.sidebar.date_input(
            "Transaction Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range

            filtered = filtered[
                filtered[date_col].dt.date.between(
                    start_date, end_date
                )
            ]

# Fraud filter

if fraud_filter == "Fraudulent":
    filtered = filtered[filtered[fraud_col] == True]

elif fraud_filter == "Non-Fraudulent":
    filtered = filtered[filtered[fraud_col] == False]


# Merchant category filter

if category_col:
    categories = sorted(
        df[category_col].dropna().astype(str).unique().tolist()
    )

    selected_categories = st.sidebar.multiselect(
        "Merchant Category",
        categories,
        default=categories
    )

    filtered = filtered[
        filtered[category_col].astype(str).isin(
            selected_categories
        )
    ]


# Payment channel filter

if channel_col:
    channels = sorted(
        df[channel_col].dropna().astype(str).unique().tolist()
    )

    selected_channels = st.sidebar.multiselect(
        "Payment Channel",
        channels,
        default=channels
    )

    filtered = filtered[
        filtered[channel_col].astype(str).isin(
            selected_channels
        )
    ]


# Transaction type filter

if type_col:
    types = sorted(
        df[type_col].dropna().astype(str).unique().tolist()
    )

    selected_types = st.sidebar.multiselect(
        "Transaction Type",
        types,
        default=types
    )

    filtered = filtered[
        filtered[type_col].astype(str).isin(
            selected_types
        )
    ]


# Location filter

if location_col:
    locations = sorted(
        df[location_col].dropna().astype(str).unique().tolist()
    )

    selected_locations = st.sidebar.multiselect(
        "Location",
        locations,
        default=locations
    )

    filtered = filtered[
        filtered[location_col].astype(str).isin(
            selected_locations
        )
    ]


# Amount filter

min_amount = float(df[amount_col].min())
max_amount = float(df[amount_col].max())

if min_amount < max_amount:
    amount_range = st.sidebar.slider(
        "Transaction Amount (₹)",
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount)
    )

    filtered = filtered[
        filtered[amount_col].between(
            amount_range[0], amount_range[1]
        )
    ]


# Customer search

if customer_id:
    customer_search = st.sidebar.text_input(
        "Search Customer / Account ID"
    )

    if customer_search.strip():
        filtered = filtered[
            filtered[customer_id].astype(str).str.contains(
                customer_search.strip(),
                case=False,
                na=False
            )
        ]


st.sidebar.divider()

if st.sidebar.button("🔄 Refresh Data", width="stretch"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption("Data source: PostgreSQL")


# --------------------------------------------------
# 6. COMMON METRICS
# --------------------------------------------------

total_transactions = len(filtered)

fraud_data = filtered[
    filtered[fraud_col] == True
]

fraud_count = len(fraud_data)

fraud_rate = (
    fraud_count / total_transactions * 100
    if total_transactions else 0
)

fraud_value = fraud_data[amount_col].sum()

total_value = filtered[amount_col].sum()


def show_metrics():
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Transactions",
        f"{total_transactions:,}"
    )

    c2.metric(
        "Fraud Transactions",
        f"{fraud_count:,}"
    )

    c3.metric(
        "Fraud Rate",
        f"{fraud_rate:.2f}%"
    )

    c4.metric(
        "Fraud Value",
        f"₹{fraud_value:,.2f}"
    )


def show_empty():
    st.warning(
        "No transactions match the selected filters. "
        "Change your sidebar filters."
    )


# --------------------------------------------------
# 7. OVERVIEW PAGE
# --------------------------------------------------

if page == "Overview":

    st.subheader("📊 Banking Overview")

    show_metrics()

    st.divider()

    left, right = st.columns(2)

    with left:

        st.markdown("### Fraud by Merchant Category")

        if category_col and fraud_count:

            category_data = (
                fraud_data.groupby(category_col)
                .size()
                .reset_index(name="Fraud Count")
                .sort_values("Fraud Count", ascending=False)
            )

            fig = px.bar(
                category_data,
                x=category_col,
                y="Fraud Count",
                color="Fraud Count",
                color_continuous_scale="Blues"
            )

            fig.update_layout(
                template="plotly_dark",
                xaxis_title="Merchant Category",
                yaxis_title="Fraud Transactions"
            )

            st.plotly_chart(fig, width="stretch")

        else:
            st.info("Category or fraud data unavailable.")

    with right:

        st.markdown("### Daily Transaction Trends")

        if date_col:

            daily = filtered.dropna(subset=[date_col]).copy()

            if not daily.empty:

                daily["Day"] = daily[date_col].dt.date

                daily_data = (
                    daily.groupby("Day")
                    .agg(
                        Transactions=(fraud_col, "size"),
                        Fraud=(fraud_col, "sum")
                    )
                    .reset_index()
                )

                fig = px.line(
                    daily_data,
                    x="Day",
                    y=["Transactions", "Fraud"],
                    markers=True,
                    template="plotly_dark"
                )

                st.plotly_chart(fig, width="stretch")

            else:
                st.info("No date information available.")

    st.divider()

    st.markdown("### Recent Fraud Transactions")

    if fraud_count:
        st.dataframe(
            fraud_data.sort_values(
                date_col, ascending=False
            ) if date_col else fraud_data,
            width="stretch",
            hide_index=True
        )
    else:
        st.info("No fraudulent transactions in this selection.")


# --------------------------------------------------
# 8. TRANSACTION EXPLORER
# --------------------------------------------------

elif page == "Transaction Explorer":

    st.subheader("🔍 Transaction Explorer")

    show_metrics()

    st.divider()

    search = st.text_input(
        "Search Transaction ID"
    )

    result = filtered.copy()

    if search.strip() and transaction_id:
        result = result[
            result[transaction_id].astype(str).str.contains(
                search.strip(),
                case=False,
                na=False
            )
        ]

    st.markdown(
        f"### Matching Transactions: {len(result):,}"
    )

    st.dataframe(
        result,
        width="stretch",
        hide_index=True
    )

    st.download_button(
        "⬇️ Download Transactions CSV",
        data=result.to_csv(index=False).encode("utf-8"),
        file_name="banking_transactions.csv",
        mime="text/csv"
    )


# --------------------------------------------------
# 9. FRAUD ANALYSIS
# --------------------------------------------------

elif page == "Fraud Analysis":

    st.subheader("🚨 Fraud Analysis")

    show_metrics()

    st.divider()

    if category_col and fraud_count:

        st.markdown("### Category-wise Fraud Analysis")

        category_analysis = (
            fraud_data.groupby(category_col)
            .agg(
                Fraud_Count=(fraud_col, "size"),
                Fraud_Amount=(amount_col, "sum")
            )
            .reset_index()
            .sort_values("Fraud_Count", ascending=False)
        )

        st.dataframe(
            category_analysis,
            width="stretch",
            hide_index=True
        )

        fig = px.pie(
            category_analysis,
            names=category_col,
            values="Fraud_Count",
            hole=0.45,
            template="plotly_dark"
        )

        st.plotly_chart(fig, width="stretch")

    if type_col and fraud_count:

        st.markdown("### Fraud by Transaction Type")

        type_analysis = (
            fraud_data.groupby(type_col)
            .size()
            .reset_index(name="Fraud Count")
        )

        fig = px.bar(
            type_analysis,
            x=type_col,
            y="Fraud Count",
            color="Fraud Count",
            template="plotly_dark"
        )

        st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# 10. CUSTOMER RISK
# --------------------------------------------------

elif page == "Customer Risk":

    st.subheader("👥 Customer Fraud Exposure")

    show_metrics()

    if customer_id:

        risk = (
            fraud_data.groupby(customer_id)
            .agg(
                Fraud_Count=(fraud_col, "size"),
                Fraud_Amount=(amount_col, "sum")
            )
            .reset_index()
            .sort_values("Fraud_Amount", ascending=False)
        )

        st.markdown("### Highest Customer Fraud Exposure")

        st.dataframe(
            risk,
            width="stretch",
            hide_index=True
        )

        if not risk.empty:

            fig = px.bar(
                risk.head(10),
                x=customer_id,
                y="Fraud_Amount",
                color="Fraud_Count",
                template="plotly_dark",
                title="Top 10 Customers by Fraud Amount"
            )

            st.plotly_chart(fig, width="stretch")

    else:
        st.warning(
            "Customer ID or account ID column is unavailable."
        )


# --------------------------------------------------
# 11. PAYMENT CHANNEL ANALYSIS
# --------------------------------------------------

elif page == "Payment Channels":

    st.subheader("💳 Payment Channel Risk Analysis")

    show_metrics()

    if channel_col:

        channel_analysis = (
            filtered.groupby(channel_col)
            .agg(
                Total=(fraud_col, "size"),
                Fraud=(fraud_col, "sum")
            )
            .reset_index()
        )

        channel_analysis["Fraud Rate (%)"] = (
            channel_analysis["Fraud"]
            / channel_analysis["Total"] * 100
        ).round(2)

        st.markdown("### Channel-wise Risk")

        st.dataframe(
            channel_analysis,
            width="stretch",
            hide_index=True
        )

        fig = px.bar(
            channel_analysis,
            x=channel_col,
            y="Fraud Rate (%)",
            color="Fraud Rate (%)",
            color_continuous_scale="Reds",
            template="plotly_dark",
            title="Fraud Rate by Payment Channel"
        )

        st.plotly_chart(fig, width="stretch")

    else:
        st.info("Payment channel column is unavailable.")


# --------------------------------------------------
# 12. REPORTS
# --------------------------------------------------

elif page == "Reports":

    st.subheader("📑 Banking Fraud Reports")

    show_metrics()

    st.divider()

    st.markdown("### Report Summary")

    summary = pd.DataFrame({
        "Metric": [
            "Total Transactions",
            "Fraud Transactions",
            "Non-Fraud Transactions",
            "Fraud Rate (%)",
            "Total Transaction Value",
            "Fraud Value"
        ],
        "Value": [
            total_transactions,
            fraud_count,
            total_transactions - fraud_count,
            round(fraud_rate, 2),
            round(total_value, 2),
            round(fraud_value, 2)
        ]
    })

    st.dataframe(
        summary,
        width="stretch",
        hide_index=True
    )

    st.download_button(
        "⬇️ Download Fraud Summary",
        data=summary.to_csv(index=False).encode("utf-8"),
        file_name="fraud_summary.csv",
        mime="text/csv"
    )

    st.download_button(
        "⬇️ Download Complete Filtered Data",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_banking_report.csv",
        mime="text/csv"
    )


# --------------------------------------------------
# 13. MANUAL FRAUD INVESTIGATION
# --------------------------------------------------

elif page == "Manual Fraud Investigation":

    st.subheader("🕵️ Manual Fraud Investigation")
    st.write(
        "Review transactions that match one or more SQL-based warning rules. "
        "A flag means the transaction needs review; it does not prove fraud."
    )

    try:
        suspicious = load_suspicious_transactions()
    except Exception as e:
        st.error(
            "Could not load the investigation results. "
            "First run the SQL script that creates "
            "vw_suspicious_transactions in PostgreSQL."
        )
        st.exception(e)
        st.stop()

    # Respect the transaction filters already selected in the sidebar.
    if transaction_id and transaction_id in suspicious.columns:
        visible_ids = set(filtered[transaction_id].tolist())
        suspicious = suspicious[
            suspicious[transaction_id].isin(visible_ids)
        ]

    total_flagged = len(suspicious)
    known_fraud = (
        int(suspicious["is_fraud"].fillna(False).astype(bool).sum())
        if "is_fraud" in suspicious.columns else 0
    )
    not_labelled_fraud = total_flagged - known_fraud

    m1, m2, m3 = st.columns(3)
    m1.metric("Transactions Flagged for Review", f"{total_flagged:,}")
    m2.metric("Already Labelled as Fraud", f"{known_fraud:,}")
    m3.metric("Not Labelled as Fraud", f"{not_labelled_fraud:,}")

    st.caption(
        "The existing is_fraud column is shown only for comparison with "
        "the SQL warning rules. It is not used to generate the warning flags."
    )

    st.divider()

    if suspicious.empty:
        st.success("No transactions matched the selected investigation rules and filters.")
    else:
        st.markdown("### Transactions Requiring Manual Review")

        display_columns = [
            col for col in [
                "transaction_id",
                "customer_id",
                "transaction_amount",
                "transaction_date",
                "location",
                "home_city",
                "payment_channel",
                "device_type",
                "is_international",
                "flag_count",
                "investigation_reasons",
                "is_fraud"
            ]
            if col in suspicious.columns
        ]

        st.dataframe(
            suspicious[display_columns],
            width="stretch",
            hide_index=True
        )

        st.markdown("### Investigation Rule Guide")
        st.markdown(
            "- **High-value transaction:** amount is at or above the "
            "dataset's 95th percentile.\n"
            "- **Location differs from home city:** transaction location "
            "does not match the customer's recorded home city.\n"
            "- **International transaction:** transaction is marked "
            "international.\n"
            "- **Rapid transaction burst:** customer made at least "
            "3 transactions in the same hour."
        )

        st.download_button(
            "⬇️ Download Investigation Results",
            data=suspicious[display_columns].to_csv(index=False).encode("utf-8"),
            file_name="manual_fraud_investigation.csv",
            mime="text/csv"
        )

        st.warning(
            "These are review indicators, not confirmed fraud decisions. "
            "An investigator should verify the transaction with the customer "
            "and other available evidence."
        )


# --------------------------------------------------
# 14. FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Banking Fraud Intelligence | "
    "PostgreSQL + SQL + Python + Streamlit | "
    "Fraud analytics and monitoring"
)
