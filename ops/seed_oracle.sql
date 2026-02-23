WHENEVER SQLERROR EXIT SQL.SQLCODE;

CREATE TABLE customers (
  id NUMBER PRIMARY KEY,
  full_name VARCHAR2(120),
  notes VARCHAR2(4000)
);

INSERT INTO customers (id, full_name, notes) VALUES (1, 'Ada Lovelace', 'First programmer');
INSERT INTO customers (id, full_name, notes) VALUES (2, 'Grace Hopper', 'COBOL pioneer');
COMMIT;

EXIT;
