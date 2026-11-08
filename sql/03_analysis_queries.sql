-- 1. Executive KPI overview
SELECT * FROM vw_fraud_overview;

-- 2. Fraud vs legitimate distribution
SELECT CASE WHEN is_fraud THEN 'Fraud' ELSE 'Legitimate' END AS status,
       COUNT(*) AS transactions,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM transactions GROUP BY is_fraud ORDER BY transactions DESC;

-- 3. Merchant category risk
SELECT merchant_category, COUNT(*) AS total_transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fraud) / NULLIF(COUNT(*),0), 2) AS fraud_rate_pct,
       ROUND(COALESCE(SUM(transaction_amount) FILTER (WHERE is_fraud),0),2) AS fraud_value
FROM transactions GROUP BY merchant_category ORDER BY fraud_value DESC;

-- 4. Payment channel risk
SELECT payment_channel, COUNT(*) AS total_transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fraud) / NULLIF(COUNT(*),0),2) AS fraud_rate_pct
FROM transactions GROUP BY payment_channel ORDER BY fraud_rate_pct DESC NULLS LAST;

-- 5. International vs domestic transactions
SELECT is_international, COUNT(*) AS total_transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fraud) / NULLIF(COUNT(*),0),2) AS fraud_rate_pct,
       ROUND(SUM(transaction_amount) FILTER (WHERE is_fraud),2) AS fraud_value
FROM transactions GROUP BY is_international;

-- 6. Daily fraud trend
SELECT DATE(transaction_date) AS transaction_day, COUNT(*) AS total_transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(SUM(transaction_amount) FILTER (WHERE is_fraud),2) AS fraud_value
FROM transactions GROUP BY DATE(transaction_date) ORDER BY transaction_day;

-- 7. Fraud by hour of day
SELECT EXTRACT(HOUR FROM transaction_date)::INT AS transaction_hour,
       COUNT(*) AS total_transactions, COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fraud) / NULLIF(COUNT(*),0),2) AS fraud_rate_pct
FROM transactions GROUP BY transaction_hour ORDER BY transaction_hour;

-- 8. Customers with the highest fraud exposure
SELECT * FROM vw_customer_risk WHERE fraud_count > 0
ORDER BY fraud_amount DESC, fraud_count DESC LIMIT 20;

-- 9. High-value transactions (95th percentile and above)
SELECT * FROM transactions
WHERE transaction_amount >= (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY transaction_amount) FROM transactions)
ORDER BY transaction_amount DESC LIMIT 100;

-- 10. Potential rapid transaction bursts
WITH hourly AS (
  SELECT customer_id, DATE_TRUNC('hour', transaction_date) AS hour_bucket,
         COUNT(*) AS transaction_count, SUM(transaction_amount) AS total_amount,
         BOOL_OR(is_fraud) AS any_known_fraud
  FROM transactions GROUP BY customer_id, DATE_TRUNC('hour', transaction_date)
)
SELECT * FROM hourly WHERE transaction_count >= 3
ORDER BY transaction_count DESC, total_amount DESC LIMIT 100;

-- 11. Location-level fraud exposure
SELECT location, COUNT(*) AS total_transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(SUM(transaction_amount) FILTER (WHERE is_fraud),2) AS fraud_value
FROM transactions GROUP BY location ORDER BY fraud_value DESC NULLS LAST;

-- 12. Monthly performance
SELECT DATE_TRUNC('month', transaction_date)::DATE AS month, COUNT(*) AS total_transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fraud) / NULLIF(COUNT(*),0),2) AS fraud_rate_pct,
       ROUND(SUM(transaction_amount),2) AS total_value,
       ROUND(SUM(transaction_amount) FILTER (WHERE is_fraud),2) AS fraud_value
FROM transactions GROUP BY DATE_TRUNC('month', transaction_date) ORDER BY month;

-- 13. Repeated fraud incidents per customer
SELECT customer_id, COUNT(*) AS fraud_incidents,
       ROUND(SUM(transaction_amount),2) AS fraud_amount,
       MIN(transaction_date) AS first_fraud_date, MAX(transaction_date) AS latest_fraud_date
FROM transactions WHERE is_fraud GROUP BY customer_id
HAVING COUNT(*) >= 2 ORDER BY fraud_incidents DESC, fraud_amount DESC;

-- 14. Data quality checks
SELECT COUNT(*) AS total_rows,
       COUNT(*) FILTER (WHERE transaction_amount < 0) AS negative_amount_rows,
       COUNT(*) FILTER (WHERE transaction_date IS NULL) AS missing_date_rows,
       COUNT(*) FILTER (WHERE customer_id IS NULL) AS missing_customer_rows
FROM transactions;
