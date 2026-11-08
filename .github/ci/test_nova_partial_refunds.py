"""Synthetic refund migration and repeated-refund atomicity checks."""
import sqlite3
import sys
sys.path.insert(0,'pharmacy')
from hospital import finance
def run():
 c=sqlite3.connect(':memory:')
 c.row_factory=sqlite3.Row
 c.execute('PRAGMA foreign_keys=ON')
 c.executescript("""
 CREATE TABLE users(id INTEGER PRIMARY KEY);
 CREATE TABLE nova_invoices(id INTEGER PRIMARY KEY,status TEXT,lab_order_id INTEGER);
 CREATE TABLE nova_banks(id INTEGER PRIMARY KEY,name TEXT,active INTEGER,require_reference INTEGER);
 CREATE TABLE nova_cashier_shifts(id INTEGER PRIMARY KEY,cashier_id INTEGER,closed_at TEXT);
 CREATE TABLE nova_payments(id INTEGER PRIMARY KEY,invoice_id INTEGER,cash_amount INTEGER,bank_amount INTEGER);
 CREATE TABLE hospital_audit(user_id INTEGER,created_at TEXT,action TEXT,object_id INTEGER,details TEXT);
 CREATE TABLE nova_claims(invoice_id INTEGER PRIMARY KEY,received INTEGER,status TEXT);
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
 INSERT INTO users VALUES(1);
 INSERT INTO nova_invoices VALUES(1,'settled',NULL);
 INSERT INTO nova_payments VALUES(1,1,30000,0);
 INSERT INTO nova_refunds(refund_no,invoice_id,idempotency_key,cash_amount,note,created_by,created_at)
 VALUES('RF-OLD',1,'old-key-00001',1000,'original',1,'2026-11-08');
 """)
 c.commit()
 finance._nova_migrate_refund_ledger(c)
 c.commit()
 assert c.execute('SELECT COUNT(*) FROM nova_refunds').fetchone()[0]==1
 assert c.execute('SELECT cash_amount FROM nova_refunds').fetchone()[0]==1000
 actor={'id':1}
 def refund(key,amount):
  return finance.refund_invoice(c,actor,{'invoice_id':1,'idempotency_key':key,'cash_amount':amount,'bank_amount':0,'note':'سبب الاسترداد'})
 a=refund('refund-00000001',10000)
 assert a['status']=='settled'
 b=refund('refund-00000002',5000)
 assert b['status']=='settled'
 assert refund('refund-00000002',5000)['already_recorded']
 try:refund('refund-00000003',20000)
 except ValueError:pass
 else:raise AssertionError('Over-refund accepted')
 assert c.execute('SELECT COUNT(*) FROM nova_refunds').fetchone()[0]==3
 assert c.execute('SELECT SUM(cash_amount) FROM nova_refunds').fetchone()[0]==16000
 final=refund('refund-00000004',14000)
 assert final['status']=='void'
 assert c.execute('SELECT status FROM nova_invoices').fetchone()[0]=='void'
 assert c.execute('SELECT COUNT(*) FROM nova_refunds').fetchone()[0]==4
 assert not c.execute('PRAGMA foreign_key_check').fetchall()
 print('NOVA_REFUND_SYNTHETIC_MIGRATION_AND_REPEATED_PASS')
if __name__=='__main__':run()
