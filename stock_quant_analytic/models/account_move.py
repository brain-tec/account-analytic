##############################################################################
# Copyright (c) 2024 braintec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html)
# See LICENSE file for full licensing details.
##############################################################################

from odoo import api, models
from odoo.addons.stock_quant_analytic.accounting import AnalyticQuantRevaluator


class AccountMove(models.Model):
    """Extension to the AccountMove model.

    Overrides the ORM create() method to check whether the journal entry
    to be created as a result of a triggered product inventory revaluation
    based on a standard price change needs to take into account any set
    analytic accounts on the underlying inventory quants.
    """
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        analytic = self.get_analytic_quant_revaluator_instance()
        if analytic.is_revaluation_required():
            analytic.revaluate(vals)

        return super().create(vals)

    def get_analytic_quant_revaluator_instance(self):
        """Gets an AnalyticQuantRevaluator implementation business object.

        Can be overridden by extensions to provide their own implementations,
        possibly by sublassing AnalyticQuantRevaluator.

        Returns:
            An AnalyticQuantRevaluator-like object. Never None.
        """
        return AnalyticQuantRevaluator(self.env)
