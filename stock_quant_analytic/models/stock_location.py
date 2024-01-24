##############################################################################
# Copyright (c) 2024 braintec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html)
# See LICENSE file for full licensing details.
##############################################################################

from odoo import models, fields


class StockLocation(models.Model):
    """Extension to the StockLocation model.

    Adds relational fields to track a default analytic account and tags.
    """
    _inherit = 'stock.location'

    default_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        check_company=True,
        string='Default Analytic Account',
        help='The analytic account to apply be default on quants that are based '
             'on this location. The account specified here is only applied when '
             'no analytic account is explicitly defined on a created quant.',
    )

    default_analytic_tag_ids = fields.Many2many(
        comodel_name='account.analytic.tag',
        check_company=True,
        string='Default Analytic Tags',
        help='The analytic tags to apply be default on quants that are based '
             'on this location. The tags specified here are only applied when '
             'no analytic tags are explicitly defined on a created quant.',
    )
