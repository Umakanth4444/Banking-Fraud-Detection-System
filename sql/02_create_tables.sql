-- Run this while connected to banking_fraud.
CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT PRIMARY KEY,
    customer_segment VARCHAR(30),
    account_age_months INTEGER CHECK (account_age_months >= 0),
    home_city VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    transaction_amount NUMERIC(14,2) NOT NULL CHECK (transaction_amount >= 0),
    transaction_date TIMESTAMP NOT NULL,
    merchant_category VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    location VARCHAR(100),
    payment_channel VARCHAR(30),
    device_type VARCHAR(30),
    is_international BOOLEAN NOT NULL DEFAULT FALSE,
    is_fraud BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_fraud ON transactions(is_fraud);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(merchant_category);
CREATE INDEX IF NOT EXISTS idx_transactions_location ON transactions(location);

CREATE OR REPLACE VIEW vw_fraud_overview AS
SELECT COUNT(*) AS total_transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fraud) / NULLIF(COUNT(*), 0), 2) AS fraud_rate_pct,
       ROUND(COALESCE(SUM(transaction_amount), 0), 2) AS total_transaction_value,
       ROUND(COALESCE(SUM(transaction_amount) FILTER (WHERE is_fraud), 0), 2) AS fraud_value,
       ROUND(AVG(transaction_amount), 2) AS average_transaction_value
FROM transactions;

CREATE OR REPLACE VIEW vw_customer_risk AS
SELECT c.customer_id, c.customer_segment, c.home_city,
       COUNT(t.transaction_id) AS transaction_count,
       COUNT(*) FILTER (WHERE t.is_fraud) AS fraud_count,
       ROUND(COALESCE(SUM(t.transaction_amount), 0), 2) AS total_amount,
       ROUND(COALESCE(SUM(t.transaction_amount) FILTER (WHERE t.is_fraud), 0), 2) AS fraud_amount,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.is_fraud) / NULLIF(COUNT(t.transaction_id), 0), 2) AS customer_fraud_rate_pct
FROM customers c LEFT JOIN transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_id, c.customer_segment, c.home_city;
