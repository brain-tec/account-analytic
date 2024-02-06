##############################################################################
# Copyright (c) 2024 braintec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html)
# See LICENSE file for full licensing details.
##############################################################################

from odoo import models
from odoo.addons.stock_quant_analytic.accounting import AnalyticQuantRevaluator


class ProductProduct(models.Model):
    """Extension to the ProductProduct model.

    Overrides the ORM write() method to check whether the standard price was
    changed, and checks accordingly whether the monetary analytic revaluation
    needs to be triggered.
    """
    _inherit = 'product.product'

    def write(self, vals):
        if 'standard_price' in vals:
            return super(
                ProductProduct,
                AnalyticQuantRevaluator.activate_on(self)
            ).write(vals)

        return super().write(vals)
