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

-- Defense in depth: the trusted staging repair executor can observe a synthetic
-- production fingerprint, but must have no production write privileges.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'production_observer') THEN
    CREATE ROLE production_observer LOGIN PASSWORD 'synthetic-production-readonly-password';
  END IF;
END $$;
GRANT CONNECT ON DATABASE orderdesk TO production_observer;
GRANT USAGE ON SCHEMA public TO production_observer;
GRANT SELECT ON orders TO production_observer;
