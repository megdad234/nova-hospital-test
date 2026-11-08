"""NOVA refund ledger migration safety tests: dry-run only, no production schema edits.
The original refund table has UNIQUE(invoice_id); repeated refunds require a transactional
table rebuild preserving existing rows, foreign keys, bank reference uniqueness and indexes.
"""
import sqlite3
def inspect_refund_constraints(connection):
    indexes=connection.execute("PRAGMA index_list('nova_refunds')").fetchall()
    return [(i[1],bool(i[2]),[x[2] for x in connection.execute('PRAGMA index_info("'+i[1]+'")')]) for i in indexes]
def validate_migration_prerequisites(connection):
    columns={r[1] for r in connection.execute("PRAGMA table_info(nova_refunds)")}
    required={'id','refund_no','invoice_id','idempotency_key','cash_amount','bank_amount','bank_id','bank_name','bank_reference','note','created_by','created_at','shift_id'}
    if not required.issubset(columns):raise RuntimeError('Unknown refund schema; migration blocked')
    unique=inspect_refund_constraints(connection)
    if not any(u and fields==['invoice_id'] for _,u,fields in unique):
        raise RuntimeError('Unexpected refund uniqueness; migration blocked')
    if connection.execute("PRAGMA foreign_key_check").fetchall():raise RuntimeError('Existing foreign key issues; migration blocked')
    return unique
if __name__=='__main__':
    db=sqlite3.connect(':memory:')
    db.executescript("""
      CREATE TABLE nova_invoices(id INTEGER PRIMARY KEY);
      CREATE TABLE users(id INTEGER PRIMARY KEY);
      CREATE TABLE nova_banks(id INTEGER PRIMARY KEY);
      CREATE TABLE nova_cashier_shifts(id INTEGER PRIMARY KEY);
      CREATE TABLE nova_refunds(
       id INTEGER PRIMARY KEY,refund_no TEXT NOT NULL UNIQUE,
       invoice_id INTEGER NOT NULL UNIQUE REFERENCES nova_invoices(id),
       idempotency_key TEXT NOT NULL UNIQUE,
       cash_amount INTEGER NOT NULL DEFAULT 0 CHECK(cash_amount>=0),
       bank_amount INTEGER NOT NULL DEFAULT 0 CHECK(bank_amount>=0),
       bank_id INTEGER REFERENCES nova_banks(id),bank_name TEXT NOT NULL DEFAULT '',
       bank_reference TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',
       created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
       shift_id INTEGER REFERENCES nova_cashier_shifts(id),
       CHECK(cash_amount+bank_amount>0),CHECK(bank_amount>0 OR bank_id IS NULL));
      CREATE UNIQUE INDEX nova_unique_refund_bank_ref ON nova_refunds(bank_id,bank_reference)
       WHERE bank_id IS NOT NULL AND bank_reference!='';
      INSERT INTO nova_invoices VALUES(1);
      INSERT INTO users VALUES(1);
      INSERT INTO nova_refunds(refund_no,invoice_id,idempotency_key,cash_amount,created_by,created_at)
       VALUES('RF-OLD',1,'old-key-unique',100,1,'2026-11-08');
    """)
    validate_migration_prerequisites(db)
    assert db.execute('SELECT COUNT(*) FROM nova_refunds').fetchone()[0]==1
    print('NOVA_REFUND_MIGRATION_PREREQUISITES_PASS (dry run only)')
