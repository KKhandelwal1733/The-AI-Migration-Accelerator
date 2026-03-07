from ai_migration_accelerator.connectors.oracle.introspection import _parse_ddl_tables


def test_parse_ddl_tables_handles_type_parentheses():
    ddl = """
    CREATE TABLE customers (
        cust_id NUMBER PRIMARY KEY,
        name VARCHAR2(100),
        tier VARCHAR2(20)
    );

    CREATE TABLE product_feedback (
        feedback_id NUMBER PRIMARY KEY,
        cust_id NUMBER REFERENCES customers(cust_id),
        product_name VARCHAR2(100),
        comments VARCHAR2(4000),
        status VARCHAR2(20),
        rating NUMBER
    );
    """

    parsed = _parse_ddl_tables(ddl)
    table_by_name = {table["name"].lower(): table for table in parsed}

    assert "customers" in table_by_name
    assert "product_feedback" in table_by_name

    customer_columns = {column["name"].lower() for column in table_by_name["customers"]["columns"]}
    feedback_columns = {
        column["name"].lower() for column in table_by_name["product_feedback"]["columns"]
    }

    assert {"cust_id", "name", "tier"}.issubset(customer_columns)
    assert {"feedback_id", "cust_id", "product_name", "comments", "status", "rating"}.issubset(
        feedback_columns
    )
