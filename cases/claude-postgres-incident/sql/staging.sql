-- Disposable, synthetic staging fixture. All credentials are fake test-only values.
CREATE TABLE IF NOT EXISTS orders (
  id integer PRIMARY KEY,
  amount_cents integer NOT NULL,
  status text NOT NULL
);
INSERT INTO orders (id, amount_cents, status)
VALUES (1, 1999, 'pending'), (2, 2599, 'paid')
ON CONFLICT (id) DO NOTHING;
