##############################################################################
# Copyright (c) 2023 brain-tec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html).
# See LICENSE file for full licensing details.
##############################################################################

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Default Analytic Account on Inventory Adjustment Line",
    )
    analytic_tag_ids = fields.Many2many(
        "account.analytic.tag",
        string="Default Analytic Tags on Inventory Adjustment Line",
    )
