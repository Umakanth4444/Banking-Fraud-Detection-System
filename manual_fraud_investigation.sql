-- Manual Fraud Investigation View
-- Run this script in pgAdmin Query Tool on banking_fraud_project.
-- These rules identify transactions for review; they do not prove fraud.

CREATE OR REPLACE VIEW public.vw_suspicious_transactions AS
WITH amount_threshold AS (
    SELECT
        PERCENTILE_CONT(0.95)
        WITHIN GROUP (ORDER BY transaction_amount) AS p95_amount
    FROM public.transactions
),
hourly_bursts AS (
    SELECT
        customer_id,
        DATE_TRUNC('hour', transaction_date) AS hour_bucket,
        COUNT(*) AS transactions_in_hour
    FROM public.transactions
    GROUP BY customer_id, DATE_TRUNC('hour', transaction_date)
    HAVING COUNT(*) >= 3
),
evaluated AS (
    SELECT
        t.transaction_id,
        t.customer_id,
        t.transaction_amount,
        t.transaction_date,
        t.merchant_category,
        t.transaction_type,
        t.location,
        c.home_city,
        t.payment_channel,
        t.device_type,
        t.is_international,
        t.is_fraud,

        (t.transaction_amount >= a.p95_amount) AS high_value_flag,

        (
            t.location IS NOT NULL
            AND c.home_city IS NOT NULL
            AND LOWER(TRIM(t.location)) <> LOWER(TRIM(c.home_city))
        ) AS location_mismatch_flag,

        t.is_international AS international_flag,

        (COALESCE(h.transactions_in_hour, 0) >= 3) AS rapid_burst_flag,

        COALESCE(h.transactions_in_hour, 0) AS transactions_in_same_hour

    FROM public.transactions AS t
    JOIN public.customers AS c
        ON c.customer_id = t.customer_id
    CROSS JOIN amount_threshold AS a
    LEFT JOIN hourly_bursts AS h
        ON h.customer_id = t.customer_id
       AND h.hour_bucket = DATE_TRUNC('hour', t.transaction_date)
)
SELECT
    transaction_id,
    customer_id,
    transaction_amount,
    transaction_date,
    merchant_category,
    transaction_type,
    location,
    home_city,
    payment_channel,
    device_type,
    is_international,
    is_fraud,
    high_value_flag,
    location_mismatch_flag,
    international_flag,
    rapid_burst_flag,
    transactions_in_same_hour,

    (
        high_value_flag::INTEGER
        + location_mismatch_flag::INTEGER
        + international_flag::INTEGER
        + rapid_burst_flag::INTEGER
    ) AS flag_count,

    CONCAT_WS(
        '; ',
        CASE WHEN high_value_flag
            THEN 'High-value transaction (95th percentile or above)' END,
        CASE WHEN location_mismatch_flag
            THEN 'Transaction location differs from customer home city' END,
        CASE WHEN international_flag
            THEN 'International transaction' END,
        CASE WHEN rapid_burst_flag
            THEN 'At least 3 transactions by this customer in the same hour' END
    ) AS investigation_reasons

FROM evaluated
WHERE
    high_value_flag
    OR location_mismatch_flag
    OR international_flag
    OR rapid_burst_flag;
