# -*- coding: utf-8 -*-
"""NOVA13 purchase regression: synthetic database only, never hospital records."""
import tempfile
import unittest
import uuid
from pathlib import Path
from datetime import date, timedelta
import app


class NovaApprovedPurchaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data, self.old_db = app.DATA, app.DB
        app.DATA = Path(self.tmp.name)
        app.DB = app.DATA / 'purchase13.sqlite3'
        app.init_db()
        self.c = app.db_connect()
        app.bootstrap(self.c, {'username': 'nova13_owner', 'full_name': 'Synthetic Owner',
                               'password': 'TestPassword12345678'})
        self.uid = app.one(self.c, 'SELECT id FROM users')['id']
        self.supplier = app.create_party(self.c, {'name': 'NOVA13 Synthetic Supplier'},
                                         'supplier', self.uid)['id']
        self.expiry = (date.today() + timedelta(days=365)).isoformat()

    def tearDown(self):
        self.c.close()
        app.DATA, app.DB = self.old_data, self.old_db
        self.tmp.cleanup()

    def quick(self, name, strips=3, barcode=''):
        return app.nova_purchase_quick_product(
            self.c, {'name': name, 'generic_name': 'Synthetic generic',
                     'strips': str(strips), 'barcode': barcode}, self.uid)

    def test_strip_sale_price_and_barcode_persist_atomic_with_purchase(self):
        pkg = self.quick('NOVA13 Test A', 3)
        pack_id = pkg['package_id']
        response = app.purchase(self.c, {
            'supplier_id': self.supplier, 'invoice_ref': 'NOVA13-INV-1',
            'items': [{'package_id': pack_id, 'qty': 2, 'received': 2,
                       'unit_cost': 4000, 'expiry': self.expiry}],
            'nova_sale_prices': [{'package_id': pack_id, 'price': 5000}],
            'nova_unit_rules': [{'package_id': pack_id, 'strips': 3, 'unit_price': 1667}],
            'nova_purchase_barcodes': [{'package_id': pack_id, 'barcode': 'NOVA13-BAR-CODE'}]
        }, self.uid)
        self.assertEqual(response['total'], 8000)
        pack = app.one(self.c, 'SELECT * FROM packages WHERE id=?', (pack_id,))
        strip = app.one(self.c, "SELECT * FROM packages WHERE product_id=? AND unit_name='شريط'",
                        (pkg['product_id'],))
        self.assertEqual(pack['sale_price'], 5000)
        self.assertEqual(pack['barcode'], 'NOVA13-BAR-CODE')
        self.assertEqual(pack['factor'], 3)
        self.assertEqual(strip['factor'], 1)
        self.assertEqual(strip['sale_price'], 1667)
        self.assertEqual(app.one(self.c, 'SELECT COUNT(*) n FROM purchases')['n'], 1)
        sale = app.sell(self.c, {
            'idempotency': uuid.uuid4().hex,
            'items': [{'package_id': strip['id'], 'qty': 1}],
            'payments': [{'method': 'cash', 'amount': 1667}]
        }, self.uid)
        self.assertEqual(sale['total'], 1667)
        self.assertEqual(app.one(self.c,'SELECT qty_base FROM lots WHERE product_id=?',
                                 (pkg['product_id'],))['qty_base'], 5)

    def test_bad_unit_count_rejects_without_stock_or_price_changes(self):
        pkg = self.quick('NOVA13 Test B', 3)
        with self.assertRaisesRegex(ValueError, 'معامل'):
            app.purchase(self.c, {
                'supplier_id': self.supplier, 'invoice_ref': 'NOVA13-INV-BAD',
                'items': [{'package_id': pkg['package_id'], 'qty': 2,
                           'unit_cost': 1000, 'expiry': self.expiry}],
                'nova_sale_prices': [{'package_id': pkg['package_id'], 'price': 1500}],
                'nova_unit_rules': [{'package_id': pkg['package_id'],
                                     'strips': 4, 'unit_price': 375}]
            }, self.uid)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM purchases')['n'],0)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM lots')['n'],0)
        self.assertEqual(app.one(self.c,'SELECT sale_price FROM packages WHERE id=?',
                                  (pkg['package_id'],))['sale_price'],0)

    def test_catalogue_box_activates_strips_atomically_on_first_purchase(self):
        product = app.create_product(self.c, {
            'sku': 'CATALOGUE-NOVA13-NEW', 'name': 'Catalogue Box NOVA13',
            'base_uom': 'علبة',
            'packages': [{'unit_name': 'علبة', 'factor': 1,
                          'sale_price': 0, 'is_default': 1}]
        }, self.uid)
        pid = product['id']
        pk = app.one(self.c, 'SELECT id FROM packages WHERE product_id=?', (pid,))['id']
        result = app.purchase(self.c, {
            'supplier_id': self.supplier,
            'items': [{'package_id': pk, 'qty': 5, 'unit_cost': 5000,
                       'expiry': self.expiry}],
            'nova_sale_prices': [{'package_id': pk, 'price': 15000}],
            'nova_unit_rules': [{'package_id': pk, 'strips': 3, 'unit_price': 5000}]
        }, self.uid)
        self.assertEqual(result['total'], 25000)
        self.assertEqual(app.one(self.c, 'SELECT base_uom FROM products WHERE id=?',
                                 (pid,))['base_uom'], 'شريط')
        self.assertEqual(app.one(self.c, 'SELECT factor FROM packages WHERE id=?',
                                 (pk,))['factor'], 3)
        self.assertEqual(app.one(self.c, 'SELECT qty_base FROM lots WHERE product_id=?',
                                 (pid,))['qty_base'], 15)
        strip = app.one(self.c, "SELECT * FROM packages WHERE product_id=? AND unit_name='شريط'", (pid,))
        self.assertEqual(strip['factor'], 1)
        self.assertEqual(strip['sale_price'], 5000)

    def test_historical_box_is_never_silently_reinterpreted(self):
        product = app.create_product(self.c, {
            'sku': 'CATALOGUE-NOVA13-HISTORY', 'name': 'Historical Box NOVA13',
            'base_uom': 'علبة',
            'packages': [{'unit_name': 'علبة', 'factor': 1,
                          'sale_price': 0, 'is_default': 1}]
        }, self.uid)
        pid = product['id']
        pk = app.one(self.c, 'SELECT id FROM packages WHERE product_id=?', (pid,))['id']
        app.purchase(self.c, {
            'supplier_id': self.supplier,
            'items': [{'package_id': pk, 'qty': 1, 'unit_cost': 1000,
                       'expiry': self.expiry}]
        }, self.uid)
        with self.assertRaisesRegex(ValueError, 'حركات'):
            app.purchase(self.c, {
                'supplier_id': self.supplier,
                'items': [{'package_id': pk, 'qty': 1, 'unit_cost': 1000,
                           'expiry': self.expiry}],
                'nova_unit_rules': [{'package_id': pk, 'strips': 3, 'unit_price': 500}]
            }, self.uid)
        self.assertEqual(app.one(self.c, 'SELECT factor FROM packages WHERE id=?',
                                 (pk,))['factor'], 1)
        self.assertEqual(app.one(self.c, 'SELECT COUNT(*) n FROM purchases')['n'], 1)

    def test_duplicate_barcode_and_duplicate_name_are_rejected(self):
        item = self.quick('NOVA13 Test C', 3, barcode='UNIQUE-13-C')
        with self.assertRaisesRegex(ValueError, 'موجود'):
            self.quick('NOVA13 Test C', 3)
        other = self.quick('NOVA13 Test D', 3)
        with self.assertRaisesRegex(ValueError, 'الباركود مرتبط'):
            app.purchase(self.c, {
                'supplier_id': self.supplier, 'invoice_ref': 'NOVA13-INV-C',
                'items': [{'package_id': other['package_id'], 'qty': 1,
                           'unit_cost': 150, 'expiry': self.expiry}],
                'nova_sale_prices': [{'package_id': other['package_id'], 'price': 200}],
                'nova_purchase_barcodes': [{'package_id': other['package_id'],
                                            'barcode': 'UNIQUE-13-C'}]
            }, self.uid)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM purchases')['n'],0)
        self.assertEqual(app.one(self.c,'SELECT barcode FROM packages WHERE id=?',
                                  (item['package_id'],))['barcode'],'UNIQUE-13-C')

if __name__ == '__main__':
    unittest.main()
