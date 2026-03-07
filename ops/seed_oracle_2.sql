---------------------------------------------------------
-- CLEANUP (ignore errors if tables don't exist)
---------------------------------------------------------
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE SUPPORT_TICKETS CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE SHIPMENTS CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE CUSTOMERS CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

---------------------------------------------------------
-- TABLE 1: CUSTOMERS
---------------------------------------------------------
CREATE TABLE CUSTOMERS (
    CUST_UUID VARCHAR2(36) PRIMARY KEY,
    NAME VARCHAR2(100),
    ACCOUNT_TIER VARCHAR2(20)
);

---------------------------------------------------------
-- TABLE 2: SHIPMENTS
---------------------------------------------------------
CREATE TABLE SHIPMENTS (
    SHIPMENT_ID VARCHAR2(50) PRIMARY KEY,
    CUST_UUID VARCHAR2(36),
    STATUS VARCHAR2(20),
    DELIVERY_DATE DATE,
    DESTINATION_COUNTRY VARCHAR2(5),
    CONSTRAINT FK_SHIPMENT_CUSTOMER
        FOREIGN KEY (CUST_UUID)
        REFERENCES CUSTOMERS(CUST_UUID)
);

---------------------------------------------------------
-- TABLE 3: SUPPORT_TICKETS
---------------------------------------------------------
CREATE TABLE SUPPORT_TICKETS (
    TICKET_ID NUMBER PRIMARY KEY,
    SHIPMENT_ID VARCHAR2(50),
    COMMENT_TEXT CLOB,
    CREATED_AT TIMESTAMP,
    CONSTRAINT FK_TICKET_SHIPMENT
        FOREIGN KEY (SHIPMENT_ID)
        REFERENCES SHIPMENTS(SHIPMENT_ID)
);

---------------------------------------------------------
-- INSERT DATA INTO CUSTOMERS
---------------------------------------------------------
INSERT INTO CUSTOMERS VALUES
('a1b2c3d4-1111-4a2b-9c11-123456789001','Rahul Sharma','VIP');

INSERT INTO CUSTOMERS VALUES
('a1b2c3d4-2222-4a2b-9c11-123456789002','Anita Verma','Standard');

INSERT INTO CUSTOMERS VALUES
('a1b2c3d4-3333-4a2b-9c11-123456789003','Michael Brown','VIP');

INSERT INTO CUSTOMERS VALUES
('a1b2c3d4-4444-4a2b-9c11-123456789004','Sara Khan','Trial');

INSERT INTO CUSTOMERS VALUES
('a1b2c3d4-5555-4a2b-9c11-123456789005','David Lee','Standard');

---------------------------------------------------------
-- INSERT DATA INTO SHIPMENTS
---------------------------------------------------------
INSERT INTO SHIPMENTS VALUES
('SHIP001','a1b2c3d4-1111-4a2b-9c11-123456789001','Delivered',DATE '2025-02-01','IN');

INSERT INTO SHIPMENTS VALUES
('SHIP002','a1b2c3d4-2222-4a2b-9c11-123456789002','Delayed',DATE '2025-02-03','US');

INSERT INTO SHIPMENTS VALUES
('SHIP003','a1b2c3d4-3333-4a2b-9c11-123456789003','In-Transit',DATE '2025-02-05','DE');

INSERT INTO SHIPMENTS VALUES
('SHIP004','a1b2c3d4-1111-4a2b-9c11-123456789001','Delivered',DATE '2025-02-10','IN');

INSERT INTO SHIPMENTS VALUES
('SHIP005','a1b2c3d4-4444-4a2b-9c11-123456789004','Delayed',DATE '2025-02-12','US');

---------------------------------------------------------
-- INSERT DATA INTO SUPPORT_TICKETS
---------------------------------------------------------
INSERT INTO SUPPORT_TICKETS VALUES
(1,'SHIP002','Customer reported shipment delay due to customs clearance.',TIMESTAMP '2025-02-03 10:15:00');

INSERT INTO SUPPORT_TICKETS VALUES
(2,'SHIP002','Follow-up: logistics team investigating the delay.',TIMESTAMP '2025-02-03 12:45:00');

INSERT INTO SUPPORT_TICKETS VALUES
(3,'SHIP003','Customer requested delivery status update.',TIMESTAMP '2025-02-05 09:20:00');

INSERT INTO SUPPORT_TICKETS VALUES
(4,'SHIP005','Shipment delayed because of weather conditions.',TIMESTAMP '2025-02-12 14:10:00');

INSERT INTO SUPPORT_TICKETS VALUES
(5,'SHIP001','Customer confirmed successful delivery.',TIMESTAMP '2025-02-01 18:30:00');

---------------------------------------------------------
-- COMMIT
---------------------------------------------------------
COMMIT;