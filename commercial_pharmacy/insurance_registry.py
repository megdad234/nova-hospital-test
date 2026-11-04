"""Independent commercial-pharmacy insurance customer registry.

The registry stores only pharmacy-specific customer and insurance membership
details. No hospital patient IDs or hospital API are required.
"""
from __future__ import annotations
import sqlite3
import uuid

DDL = """
CREATE TABLE IF NOT EXISTS commercial_customers (
 id TEXT PRIMARY KEY,
 full_name TEXT NOT NULL,
 phone TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS commercial_insurance_memberships (
 id TEXT PRIMARY KEY,
 customer_id TEXT NOT NULL REFERENCES commercial_customers(id) ON DELETE CASCADE,
 insurer_name TEXT NOT NULL,
 card_number TEXT NOT NULL,
 policy_number TEXT NOT NULL DEFAULT '',
 member_name TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'active'
   CHECK (status IN ('active','inactive','expired')),
 UNIQUE(insurer_name, card_number)
);
CREATE INDEX IF NOT EXISTS commercial_memberships_customer
 ON commercial_insurance_memberships(customer_id);
"""

def initialize_registry(conn: sqlite3.Connection):
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(DDL)

def register_customer(conn: sqlite3.Connection, full_name: str, phone: str = ""):
    full_name = full_name.strip()
    if not full_name or len(full_name) > 200:
        raise ValueError("Valid customer name is required")
    customer_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO commercial_customers(id,full_name,phone) VALUES(?,?,?)",
        (customer_id, full_name, phone.strip()[:60]))
    return customer_id

def add_membership(conn: sqlite3.Connection, customer_id: str,
                   insurer_name: str, card_number: str,
                   policy_number: str = "", member_name: str = ""):
    insurer_name = insurer_name.strip()
    card_number = card_number.strip()
    if not insurer_name or not card_number:
        raise ValueError("Insurer and card number are required")
    membership_id = str(uuid.uuid4())
    conn.execute("""INSERT INTO commercial_insurance_memberships
        (id,customer_id,insurer_name,card_number,policy_number,member_name)
        VALUES(?,?,?,?,?,?)""",
        (membership_id, customer_id, insurer_name, card_number,
         policy_number.strip(), member_name.strip()))
    return membership_id

def find_membership(conn: sqlite3.Connection, insurer_name: str, card_number: str):
    row = conn.execute("""SELECT m.id,m.customer_id,c.full_name,c.phone,
        m.insurer_name,m.card_number,m.policy_number,m.member_name,m.status
        FROM commercial_insurance_memberships m
        JOIN commercial_customers c ON c.id=m.customer_id
        WHERE m.insurer_name=? AND m.card_number=?""",
        (insurer_name.strip(), card_number.strip())).fetchone()
    if row is None:
        return None
    return dict(zip(("id","customer_id","full_name","phone","insurer_name",
                     "card_number","policy_number","member_name","status"), row))
