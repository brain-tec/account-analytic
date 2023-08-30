##############################################################################
# Copyright (c) 2023 brain-tec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html).
# See LICENSE file for full licensing details.
##############################################################################

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    analytic_account_id = fields.Many2one(
        related="company_id.analytic_account_id", readonly=False
    )
    analytic_tag_ids = fields.Many2many(
        related="company_id.analytic_tag_ids", readonly=False
    )
