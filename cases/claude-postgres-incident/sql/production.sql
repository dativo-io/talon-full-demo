-- Disposable, synthetic "production" fixture. No real customer data.
CREATE TABLE IF NOT EXISTS orders (
  id integer PRIMARY KEY,
  amount_cents integer NOT NULL,
  status text NOT NULL
);
INSERT INTO orders (id, amount_cents, status)
SELECT n, n * 111, 'paid'
FROM generate_series(1, 1000) n
ON CONFLICT (id) DO NOTHING;
