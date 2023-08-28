##############################################################################
# Copyright (c) 2023 brain-tec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html).
# See LICENSE file for full licensing details.
##############################################################################

from odoo.tests.common import TransactionCase


class TestStockQuantAnalytic(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        AccountAnalyticTag = cls.env["account.analytic.tag"]
        ProductProduct = cls.env["product.product"]
        eur = cls.env["res.currency"].search([("name", "=", "EUR")])
        eur.active = True

        cls.Quant = cls.env["stock.quant"]
        cls.StockMove = cls.env["stock.move"]
        cls.product_1 = ProductProduct.create(
            {
                "name": "Test Product 1",
                "type": "product",
                "price": 500,
                "standard_price": 1000,
            }
        )
        cls.product_2 = ProductProduct.create(
            {
                "name": "Test Product 2",
                "type": "product",
                "price": 500,
                "standard_price": 1000,
            }
        )
        cls.location = cls.env["stock.location"].create(
            {
                "name": "Test Location",
                "usage": "internal",
            }
        )
        cls.analytic_account_1 = cls.env["account.analytic.account"].create(
            {"name": "Test Analytic Account 1"}
        )
        cls.analytic_account_2 = cls.env["account.analytic.account"].create(
            {"name": "Test Analytic Account 2"}
        )
        cls.analytic_tag_1 = AccountAnalyticTag.create({"name": "Test Analytic Tag 1"})
        cls.analytic_tag_2 = AccountAnalyticTag.create({"name": "Test Analytic Tag 2"})

        cls.env.user.company_id.write(
            {
                "analytic_account_id": cls.analytic_account_1.id,
                "analytic_tag_ids": [
                    (6, 0, [cls.analytic_tag_1.id, cls.analytic_tag_2.id])
                ],
            }
        )

    def test_quant_adjustment_analytic_using_defaults(self):
        quants = self.Quant.search([("product_id", "=", self.product_1.id)])
        self.assertEqual(len(quants), 0)

        self.Quant.create(
            {
                "product_id": self.product_1.id,
                "location_id": self.location.id,
                "inventory_quantity": 10,
            }
        ).action_apply_inventory()
        stock_move = self.StockMove.search(
            [
                ("product_id.id", "=", self.product_1.id),
            ]
        )
        self.assertEqual(len(stock_move), 1)
        self.assertEqual(stock_move.analytic_account_id.id, self.analytic_account_1.id)
        self.assertListEqual(
            stock_move.analytic_tag_ids.ids,
            [self.analytic_tag_1.id, self.analytic_tag_2.id],
        )

    def test_quant_adjustment_analytic_setting_manually(self):
        quants = self.Quant.search([("product_id", "=", self.product_2.id)])
        self.assertEqual(len(quants), 0)

        self.Quant.create(
            {
                "product_id": self.product_2.id,
                "location_id": self.location.id,
                "inventory_quantity": 10,
                "analytic_account_id": self.analytic_account_2.id,
                "analytic_tag_ids": [(6, 0, [self.analytic_tag_1.id])],
            }
        ).action_apply_inventory()
        stock_move = self.StockMove.search(
            [
                ("product_id.id", "=", self.product_2.id),
            ]
        )
        self.assertEqual(len(stock_move), 1)
        self.assertEqual(stock_move.analytic_account_id.id, self.analytic_account_2.id)
        self.assertListEqual(
            stock_move.analytic_tag_ids.ids,
            [self.analytic_tag_1.id],
        )
