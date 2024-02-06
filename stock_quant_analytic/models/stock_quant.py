##############################################################################
# Copyright (c) 2023 brain-tec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html).
# See LICENSE file for full licensing details.
##############################################################################

from decimal import Decimal

from odoo import api, fields, models
from odoo import Command


class StockQuant(models.Model):
    _inherit = "stock.quant"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        default=lambda self: self._get_default_analytic_account(),
    )
    analytic_tag_ids = fields.Many2many(
        "account.analytic.tag",
        string="Analytic Tags",
        default=lambda self: self._get_default_analytic_tags(),
    )

    @api.model
    def create(self, vals):
        """Override to set default analytic account and
        tags based on quant location.
        """
        self._set_default_analytic_account_and_tags(vals)
        return super().create(vals)

    @api.model
    def find_inventory_by_product(self, product_id):
        """Finds the quants of the current inventory of the
        product with the specified ID.

        Args:
            product_id: The ID of the ProductProduct record.

        Returns:
            A StockQuant recordset with the quants of the current
            inventory of the specified product.
        """
        return self.env[self._name].search([
            ('product_id', '=', product_id),
            ('location_id.usage', 'in', ['internal', 'transit']),
        ])

    @api.model
    def has_any_unset_analytic_account(self):
        """Indicates whether this StockQuant recordset has any
        quants for which no analytic account is set.

        Returns:
            True if this StockQuant recordset contains at least
            one quant for which no analytic account is set.
            Returns False if all quants have an analytic account set.
        """
        return any(not record.analytic_account_id for record in self)

    @api.model
    def get_unique_analytic_accounts(self):
        """Gets the analytic accounts of this StockQuant recordset.

        Returns:
            An AccountAnalyticAccount recordset with all the analytic accounts
            referenced by the quants in this StockQuant recordset,
            without any duplicates.
        """
        return self.env['account.analytic.account'].browse(
            list(set(self.analytic_account_id.ids))
        )

    @api.model
    def filter_by_analytic_account(self, analytic_account):
        """Filters the quants in this recordset for those having
        the specified analytic account.

        Args:
            analytic_account: The AccountAnalyticAccount record to filter by.
                May be falsy to filter for quants having no AA set.

        Returns:
            This StockQuant recordset filtered by the
            specified analytic account. May be empty.
        """
        if not analytic_account:
            analytic_account = self.env['account.analytic.account']

        return self.filtered(
            lambda quant: quant.analytic_account_id == analytic_account
        )

    @api.model
    def get_total_quantity(self):
        """Gets the total quantity on hand of the quants in this recordset.

        Returns:
            The sum of the quantities in this StockQuant recordset, as a Decimal.
            Returns a numeric value of zero if this recordset is empty.
        """
        return Decimal(sum(self.mapped('quantity')))

    def _set_default_analytic_account_and_tags(self, vals):
        """Sets the analytic account and tags in the given vals dict.

        The accout and tags are only overridden when they are
        not already set in the given dict.

        Args:
            vals: The create() dict.
        """
        if not vals.get('analytic_account_id'):
            self._set_default_analytic_account(vals)

        if self._should_set_default_analytic_account_tags(vals):
            self._set_default_analytic_account_tags(vals)

    def _set_default_analytic_account(self, vals):
        """Sets the default analytic account based on the
        location of the quant to be created.

        Args:
            vals: The create() dict.
        """
        location = self.env['stock.location'].browse(vals['location_id'])
        default_aa = location.default_analytic_account_id
        if default_aa:
            vals['analytic_account_id'] = default_aa.id

    def _should_set_default_analytic_account_tags(self, vals):
        """Indicates whether the *default* analytic account tags based
        on the location of the quant to be created should be set.

        Args:
            vals: The create() dict.

        Returns:
            `True` if the default AA tags should be set.
            `False` if at least one AA tag is already present and therefore
            the defaults should not be set.
        """
        analytic_tags_list = vals.get('analytic_tag_ids')
        return bool(
            analytic_tags_list
            and len(analytic_tags_list[0]) == 3
            and not analytic_tags_list[0][2]
        )

    def _set_default_analytic_account_tags(self, vals):
        """Sets the default analytic account tags based on the
        location of the quant to be created.

        Args:
            vals: The create() dict.
        """
        location = self.env['stock.location'].browse(vals['location_id'])
        default_aa_tags = location.default_analytic_tag_ids
        if default_aa_tags:
            vals['analytic_tag_ids'] = [Command.set(default_aa_tags.ids)]

    def _get_default_analytic_account(self):
        return self.env.company.analytic_account_id.id

    def _get_default_analytic_tags(self):
        return self.env.company.analytic_tag_ids.ids

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res = super(StockQuant, self)._get_inventory_move_values(
            qty, location_id, location_dest_id, out
        )
        if self.analytic_account_id:
            res["analytic_account_id"] = self.analytic_account_id.id
        if self.analytic_tag_ids:
            res["analytic_tag_ids"] = [(6, 0, self.analytic_tag_ids.ids)]
        return res

    @api.model
    def _get_inventory_fields_write(self):
        res = super()._get_inventory_fields_write()
        res.extend(["analytic_account_id", "analytic_tag_ids"])
        return res
