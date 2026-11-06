"""Integration regression for the actual patched NOVA price-list API."""
import ast
import importlib.util
import sqlite3
from pathlib import Path

source=Path("pharmacy/app.py").read_text(encoding="utf-8")
tree=ast.parse(source)
names={"nova_price_list_preview","nova_price_list_approve","nova_price_list_history","nova_price_list_rollback","nova_price_signature","nova_price_list_file_rows"}
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
assert {node.name for node in functions}==names
# Extract functions so the test cannot start the pharmacy server or alter its production DB.
namespace={"Decimal":__import__("decimal").Decimal,"json":__import__("json"),"_nova_hmac":__import__("hmac"),"_nova_hashlib":__import__("hashlib"),"_nova_price_preview_secret":b"test-only-secret"}
exec(compile(ast.Module(body=functions,type_ignores=[]),"pharmacy/app.py","exec"),namespace)
c=sqlite3.connect(":memory:",isolation_level=None)
c.row_factory=sqlite3.Row
c.executescript("""
CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT,strength TEXT,form TEXT,manufacturer TEXT,active INTEGER);
CREATE TABLE packages(id INTEGER PRIMARY KEY,product_id INTEGER,factor INTEGER,sale_price INTEGER,barcode TEXT,unit_name TEXT);
CREATE TABLE purchase_lines(id INTEGER PRIMARY KEY,package_id INTEGER,amount INTEGER,qty INTEGER,bonus INTEGER,received INTEGER);
CREATE TABLE lots(id INTEGER PRIMARY KEY,product_id INTEGER,status TEXT,qty_base INTEGER,expiry TEXT);
INSERT INTO lots VALUES(1,1,'sellable',20,'');
CREATE TABLE audit(id INTEGER PRIMARY KEY,created_at TEXT,user_id INTEGER,action TEXT,details TEXT);
INSERT INTO products VALUES(1,'Paracetamol','500mg','tablet','Acme',1);
INSERT INTO packages VALUES(1,1,10,6000,'ABC','box');
INSERT INTO purchase_lines VALUES(1,1,5000,1,0,1);
""")
def begin(c):c.execute("BEGIN IMMEDIATE")
def finish(c):c.execute("COMMIT")
def rollback(c):c.execute("ROLLBACK")
def audit(c,uid,action,details):
 c.execute("INSERT INTO audit(created_at,user_id,action,details) VALUES('now',?,?,?)",(uid,action,__import__("json").dumps(details)))
namespace.update(begin=begin,finish=finish,rollback=rollback,audit=audit)
preview=namespace["nova_price_list_preview"]
approve=namespace["nova_price_list_approve"]
history=namespace["nova_price_list_history"]
undo=namespace["nova_price_list_rollback"]
row={"name":"Paracetamol","strength":"500mg","pack":"box","barcode":"ABC","purchase_price":"7000"}
# A registered medicine without available stock must not be repriced.
c.execute("UPDATE lots SET qty_base=0 WHERE id=1")
without_stock=preview(c,{"rows":[row]})["rows"][0]
assert without_stock["status"]=="review" and not without_stock["candidates"] and not without_stock["suggestions"],without_stock
c.execute("UPDATE lots SET qty_base=20 WHERE id=1")
result=preview(c,{"rows":[row]})["rows"][0]
assert result["status"]=="matched" and result["proposed_sale_price"]==8400,result
assert c.execute("SELECT sale_price FROM packages").fetchone()[0]==6000
# Human-confirmed spelling variation: preview only, no price/stock write.
suggested=preview(c,{"rows":[{"name":"Paracetmol","strength":"500mg","pack":"box","purchase_price":"7000","line":17}]})["rows"][0]
assert suggested["status"]=="review" and suggested["suggestions"],suggested
confirmed=preview(c,{"rows":[{"name":"Paracetmol","strength":"500mg","pack":"box","purchase_price":"7000","line":17}],"confirmed_matches":{"17":1}})["rows"][0]
assert confirmed["status"]=="matched" and confirmed["confirmed_manually"] and confirmed["package_id"]==1,confirmed
assert c.execute("SELECT sale_price FROM packages").fetchone()[0]==6000
try:
 preview(c,{"rows":[{"name":"Paracetmol","strength":"1000mg","pack":"box","purchase_price":"7000","line":18}],"confirmed_matches":{"18":1}})
 raise AssertionError("different strength was accepted")
except ValueError:pass
approved=approve(c,{"items":[{"package_id":1,"old_sale_price":6000,"proposed_sale_price":8400,"approval_token":result["approval_token"]}]},1)
assert approved["updated"]==1
assert c.execute("SELECT sale_price FROM packages").fetchone()[0]==8400
try:
 approve(c,{"items":[{"package_id":1,"old_sale_price":6000,"proposed_sale_price":9000,"approval_token":result["approval_token"]}]},1)
 raise AssertionError("stale update was allowed")
except ValueError:pass
assert c.execute("SELECT sale_price FROM packages").fetchone()[0]==8400
events=history(c)
assert len(events)==1 and events[0]["action"]=="bulk_supplier_price_list_approved"
assert undo(c,{"audit_id":events[0]["id"]},1)["restored"]==1
assert c.execute("SELECT sale_price FROM packages").fetchone()[0]==6000
try:
 undo(c,{"audit_id":events[0]["id"]},1)
 raise AssertionError("duplicate rollback was allowed")
except ValueError:pass
assert c.execute("SELECT COUNT(*) FROM purchase_lines").fetchone()[0]==1
# Verify the actual integrated XLSX and CSV import entry point.
import io,base64,csv
from openpyxl import Workbook
wb=Workbook();ws=wb.active
ws.append(["الاسم التجاري","السعر","التركيز","العبوة","باركود"])
ws.append(["Paracetamol",7000,"500mg","box","ABC"])
stream=io.BytesIO();wb.save(stream)
parse=namespace["nova_price_list_file_rows"]
xlsx=parse({"filename":"supplier.xlsx","content_base64":base64.b64encode(stream.getvalue()).decode("ascii")})
assert xlsx["count"]==1 and xlsx["rows"][0]["name"]=="Paracetamol",xlsx
assert xlsx["rows"][0]["purchase_price"]=="7000"
csv_bytes="name,purchase_price\nParacetamol,7000\n".encode("utf-8")
csv_result=parse({"filename":"supplier.csv","content_base64":base64.b64encode(csv_bytes).decode("ascii")})
assert csv_result["count"]==1
try:
 parse({"filename":"supplier.pdf","content_base64":base64.b64encode(b"fake").decode("ascii")})
 raise AssertionError("unsupported PDF accepted")
except ValueError:pass
print("NOVA_BULK_PRICE_INTEGRATION_TEST_PASSED")
