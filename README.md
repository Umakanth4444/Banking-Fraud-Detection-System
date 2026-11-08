# Banking Fraud Detection — SQL-Focused Project

A PostgreSQL-centered project with relational design, constraints, indexes, analytical views, 14 SQL analysis queries, a Streamlit dashboard, and an optional Random Forest baseline.

## Contents
- `customers` and `transactions` relational tables
- Primary keys, foreign keys, check constraints, indexes and views
- SQL analysis for fraud rate, category/channel risk, time patterns, customer exposure, suspicious bursts, monthly trends and data quality
- Streamlit/Plotly dashboard powered by PostgreSQL
- Optional Random Forest model evaluation
- Synthetic sample CSV with 600 rows for first-time testing

## Setup (Windows + VS Code)

1. Extract this folder and open it in VS Code.
2. In pgAdmin, connect to your PostgreSQL server.
3. If database `banking_fraud` does not exist, run `sql/01_create_database.sql` while connected to `postgres`. If it already exists, skip this file.
4. Connect to the `banking_fraud` database and run `sql/02_create_tables.sql`.
5. Copy `.env.example` to `.env`; enter your actual PostgreSQL password. Do not share `.env`.
6. Open the VS Code terminal at the project root and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py test-db
```

If you already have a `.venv`, activate it instead of creating a new one.

7. Load the included sample data:

```powershell
python app.py load-data
```

If you want to clear the project's current rows and reload the CSV:

```powershell
python app.py load-data --replace
```

Use `--replace` carefully; it deletes the current rows in the project's tables.

8. In pgAdmin, connected to `banking_fraud`, open `sql/03_analysis_queries.sql` and run the queries.
9. Start the dashboard:

```powershell
streamlit run dashboard.py
```

10. Optional machine-learning baseline:

```powershell
python app.py train
```

## Use your own CSV
The included CSV is synthetic demonstration data, not real customer data. The loader requires these columns: `transaction_id`, `customer_id`, `transaction_amount`, `transaction_date`, `merchant_category`, `transaction_type`, `location`, and `is_fraud`. Optional columns are `payment_channel`, `device_type`, `is_international`, `customer_segment`, `account_age_months`, and `home_city`. Common aliases are supported in `src/data.py`; update its mapping if your dataset uses different names.

## Project review discussion
Be prepared to explain relational normalization, primary and foreign keys, constraints, indexes, analytical views, conditional aggregation, window functions, percentile-based outlier exploration, and why fraud analysis should consider precision, recall, F1 and false negatives rather than accuracy alone. This is an educational demo, not a production fraud-decision system.
