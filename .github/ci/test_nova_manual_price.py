"""NOVA isolated regression: price search and edits never touch stock or old invoices."""
import ast
import sqlite3
from pathlib import Path
src=Path('pharmacy/app.py').read_text(encoding='utf-8')
tree=ast.parse(src)
names={'nova_sale_price_catalog','nova_manual_sale_price','nova_manual_price_history'}
funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in funcs}==names
scope={}
exec(compile(ast.Module(body=funcs,type_ignores=[]),'pharmacy/app.py','exec'),scope)
c=sqlite3.connect(':memory:',isolation_level=None)
c.row_factory=sqlite3.Row
c.executescript("""
CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT,strength TEXT,active INTEGER);
CREATE TABLE packages(id INTEGER PRIMARY KEY,product_id INTEGER,unit_name TEXT,barcode TEXT,sale_price INTEGER);
CREATE TABLE stock_movements(id INTEGER PRIMARY KEY,package_id INTEGER,qty INTEGER);
CREATE TABLE sales(id INTEGER PRIMARY KEY,total INTEGER);
CREATE TABLE audit(id INTEGER PRIMARY KEY,created_at TEXT DEFAULT CURRENT_TIMESTAMP,user_id INTEGER,action TEXT,details TEXT);
INSERT INTO products VALUES(1,'Panadol','500mg',1);
INSERT INTO packages VALUES(1,1,'box','ABC123',6000);
INSERT INTO stock_movements VALUES(1,1,50);
INSERT INTO sales VALUES(1,6000);
""")
import json
scope.update(begin=lambda c:c.execute('BEGIN IMMEDIATE'),finish=lambda c:c.execute('COMMIT'),
             rollback=lambda c:c.execute('ROLLBACK'),
             audit=lambda c,uid,action,details:c.execute('INSERT INTO audit(user_id,action,details) VALUES(?,?,?)',(uid,action,json.dumps(details))))
find=scope['nova_sale_price_catalog'];edit=scope['nova_manual_sale_price']
assert find(c,{'q':'Pana'})['rows'][0]['sale_price']==6000
assert find(c,{'q':'ABC'})['rows'][0]['package_id']==1
assert find(c,{'q':'ZZZZ'})['count']==0
assert edit(c,{'package_id':1,'old_sale_price':6000,'new_sale_price':8500},7)['updated']
assert c.execute('SELECT sale_price FROM packages').fetchone()[0]==8500
assert c.execute('SELECT qty FROM stock_movements').fetchone()[0]==50
assert c.execute('SELECT total FROM sales').fetchone()[0]==6000
assert c.execute('SELECT action FROM audit').fetchone()[0]=='manual_sale_price_update'
assert scope['nova_manual_price_history'](c)['rows'][0]['new']==8500
assert scope['nova_manual_price_history'](c)['rows'][0]['old']==6000
assert scope['nova_manual_price_history'](c)['rows'][0]['user_id']==7
for payload in ({'package_id':1,'old_sale_price':6000,'new_sale_price':9000},
                {'package_id':1,'old_sale_price':8500,'new_sale_price':0},
                {'package_id':1,'old_sale_price':8500,'new_sale_price':-10},
                {'package_id':1,'old_sale_price':8500,'new_sale_price':8500}):
    try:edit(c,payload,7);raise AssertionError('Invalid update accepted')
    except ValueError:pass
assert c.execute('SELECT sale_price FROM packages').fetchone()[0]==8500
assert c.execute('SELECT COUNT(*) FROM audit').fetchone()[0]==1
print('NOVA_MANUAL_PRICE_REGRESSION_OK')
