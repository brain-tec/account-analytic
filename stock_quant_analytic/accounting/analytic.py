##############################################################################
# Copyright (c) 2024 braintec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html)
# See LICENSE file for full licensing details.
##############################################################################

import logging

from decimal import Decimal

from odoo import Command
from odoo.exceptions import ValidationError

log = logging.getLogger('AnalyticQuantRevaluator')


class AnalyticQuantRevaluator:
    """A business object to perform inventory accounting valuation adjustments.

    When certain attributes of a product, for which there is available stock,
    are changed, then the valuation as perceived by the system's accounting
    needs to be adjusted in order to reflect an accurate financial representation
    of the assets that are in inventory at a given time.
    For example, this is the case when a user changes the standard price of a
    product for which there is stock available in the inventory.
    Odoo by default creates a journal entry with two lines (debit + credit) with
    the monetary amounts that were recomputed by the triggered change, usually
    by creating another 'stock.valuation.layer'. However, Odoo by default does not
    set any analytic accounts to those lines. This class is used to gather all
    available analytic accounts from the underlying stock quants that are part of
    the inventory revaluation and recomputes the journal entry lines to reflect
    the accounting revaluation based on the analytic accounts of those quants.
    The total monetary revaluation is distributed based on the weighted quantity
    factor of the quanty in stock. Analytic accounts for which the computed factor
    would be too small, e.g. because their sum of quantities is too small in relation
    to the overall available quantity which is revaluated, then that analytic account
    may be excluded from the grouping with the underlying journal entry. That is, an
    AnalyticQuantRevaluator instance may decide to not add an additional
    debit-credit-pair in the journal entry lines.
    """

    def __init__(self, env):
        """Constructs a new AnalyticQuantRevaluator instance.

        Args:
            env: The Odoo environment to use for the revaluation.
        """
        self._env = env
        self._prec = 4

    def is_revaluation_required(self):
        """Indicates whether a revaluation is required based on
        the underlying environment.

        Returns:
            True if the AnalyticQuantRevaluator instance detects
            that a revaluation is required.
            Returns False if no revaluation is needed.
        """
        return bool(
            self._env.context.get('stock_quant_analytic_revaluate_aml_aa', False)
        )

    def revaluate(self, vals):
        """Performs a revaluation of the inventory quants
        for the underlying product.

        Args:
            vals: The vals dict passed by Odoo to the AccountMove.create() method
            when the Odoo stock accounting core determines to create a new
            journal entry for an occurred stock revaluation.

        Returns:
            True if the AccountMoveLines were changed as a result of this operation.
            Returns False if the lines remain unchanged.

        Raises:
            ValidationError: If the revaluation cannot be carried out due
                to an unmet precondition.
        """
        line_ids = vals.get('line_ids', [])
        if len(line_ids) != 2:
            raise ValidationError(f'Expected two lines, got {len(line_ids)}')

        new_lines = self.compute_lines(line_ids)
        if new_lines is not None:
            vals['line_ids'] = new_lines
            return True

        return False

    def compute_lines(self, lines):
        """Computes the adjusted account move lines for the analytic-based stock
        revaluation based on the original (AA-ungrouped) account move lines.

        Args:
            lines: The list of account move line command vals.

        Returns:
            The revaluated account move line vals, in the same format as the input.
            Returns None if the revaluation has no effect and can be omitted.

        Raises:
            ValidationError: If the revaluation cannot be carried out due
            to an unmet precondition.
        """
        product_id = self.check_lines(lines)

        debit_line = self._get_line_by_type(lines, 'debit')
        credit_line = self._get_line_by_type(lines, 'credit')
        total_value = Decimal(debit_line['debit'])

        quants = self._env['stock.quant'].find_inventory_by_product(product_id)

        analytic_account_records = quants.get_unique_analytic_accounts()
        group_count = len(analytic_account_records)
        if group_count == 0:
            return None  # No AA set. Nothing to be revaluated.

        add_empty_aa_pair = quants.has_any_unset_analytic_account()

        analytic_accounts = []

        if add_empty_aa_pair and group_count > 0:
            group_count += 1
            analytic_accounts.append(None)

        analytic_accounts.extend(analytic_account_records)
        total_quantity = quants.get_total_quantity()
        revaluated_lines = []
        for account in analytic_accounts:
            factor = self._compute_revaluation_factor(
                quants, account, total_quantity
            )
            group_value = self._compute_group_value(factor, total_value)
            if group_value.is_zero():
                log.info(
                    "Excluding quants with analytic account '%s' from "
                    "revaluation since factor is too small", account
                )
                continue

            debit, credit = self._create_aml_pair(
                debit_line, credit_line, account, group_value
            )
            revaluated_lines.append(Command.create(debit))
            revaluated_lines.append(Command.create(credit))

        if self._correct_numeric_discrepancy(revaluated_lines, total_value):
            log.info(
                'Performed numeric correction for analytic '
                'account quant revaluation'
            )

        return revaluated_lines or None

    def check_lines(self, lines):
        """Performs validity checks on the given account move lines and
        finds out the ID of the product the revaluation should be performed for.

        Args:
            lines: The list of account move line command vals.

        Returns:
            The ID of the product the revaluation should be performed for.

        Raises:
            ValidationError: If the validity check fails.
        """
        cmd_line_1 = lines[0]
        cmd_line_2 = lines[1]
        if cmd_line_1[0] != Command.CREATE or cmd_line_2[0] != Command.CREATE:
            raise ValidationError(
                'Expected Command.CREATE code but found line '
                f'command codes {cmd_line_1[0]} and {cmd_line_2[0]}'
            )

        line_vals_1 = cmd_line_1[2]
        line_vals_2 = cmd_line_2[2]
        product_id = line_vals_1.get('product_id')
        if product_id is None:
            raise ValidationError('No product ID Found')

        if product_id != line_vals_2.get('product_id'):
            raise ValidationError('Internal error: Product IDs do not match')

        return product_id

    def _get_line_by_type(self, lines, acc_type):
        """Finds the account move line for the specified account type.

        Args:
            lines: The list of account move line command vals.
            acc_type: The account type to search for, as a str.
                Either 'debit' or 'credit'.

        Returns:
            The account move line vals dict for the specified account type.

        Raises:
            ValidationError: If the given account type cannot be found in
                the specified lines. This is considered an internal error.

        """
        for position in (0, 1):
            line_vals = lines[position][2]
            value = line_vals.get(acc_type, 0)
            if value != 0:
                return line_vals

        raise ValidationError(
            f"Failed to find account move line of type '{acc_type}'"
        )

    def _needs_numeric_correction(self, total_computed, expected_sum):
        """Indicates whether the computed revaluation sum requires
        a numeric correction to be performed.

        A numeric correction might have to be performed in case the total sum
        of the journal entry used in the revaluation cannot be numerically
        distributed (based on the computed factors) among the individual analytic
        account groups, such that summing up the grouped entries would not yield
        the same result. For example, in the simplest case, assuming evenly
        distributed factors of three groups with a total journal entry sum of 100:
        (100 / 3 = 33.33)  <!=>  (3 * 33.33 = 99.99)

        Args:
            total_computed: The computed revaluation sum, as a float or Decimal.
            expected_sum: The expected revaluation sum, i.e. the target sum of
                the underlying journal entry, as a float or Decimal.

        Returns:
            True if a numeric correction has to be performed, False otherwise.
        """
        expected = round(expected_sum, self._prec)
        actual = round(total_computed, self._prec)
        return actual != expected

    def _correct_numeric(self, revaluated_lines, actual_computed, expected_sum):
        """Performs a numeric correction for the given revaluation lines.

        The monetary values of the given lines are adjusted in place.

        Args:
            revaluated_lines: The computed revaluation account move lines, as a list.
            actual_computed: The result sum of the revaluation lines,
                as a float or Decimal
            expected_sum: The expected revaluation sum, as a float or Decimal.
        """
        difference = expected_sum - actual_computed
        first_line_debit = self._get_line_by_type(revaluated_lines, 'debit')
        first_line_credit = self._get_line_by_type(revaluated_lines, 'credit')
        corrected_debit = Decimal(first_line_debit['debit']) + difference
        corrected_credit = Decimal(first_line_credit['credit']) + difference
        first_line_debit['debit'] = float(round(abs(corrected_debit), self._prec))
        first_line_credit['credit'] = float(round(abs(corrected_credit), self._prec))

    def _compute_revaluation_factor(self, quants, account, total_quantity):
        """Computes the revaluation factor for the specified quants based
        on the given analytic account.

        Args:
            quants: The StockQuant recordset for which to compute
                the group revaluation factor.
            account: The AccountAnalyticAccount record to group by,
                may be Falsy.
            total_quantity: The total quantity to factorise, as a Decimal.

        Returns:
            The revaluation factor for the specified analytic account,
            as a Decimal.
        """
        aa_quantity = quants.filter_by_analytic_account(account).get_total_quantity()
        return round(aa_quantity / total_quantity, self._prec)

    def _compute_group_value(self, factor, valuation_total):
        """Computes the monetary value of the analytic account group
        with the given factor.

        Args:
            factor: The group factor to apply, as a Decimal.
            valuation_total: The total monetary value of the journal entry,
                which should be divided into AA-groups, as a Decimal.

        Returns:
            The group value, as a Decimal.
        """
        return round(factor * valuation_total, self._prec)

    def _compute_actual_total_of(self, revaluated_lines):
        """Returns the sum of the given revaluation lines.

        Args:
            revaluated_lines: The revaluation lines, as a list.

        Returns:
            The monetary sum, as a Decimal.
        """
        return sum([
            Decimal(line[2].get('debit', 0.0)) for line in revaluated_lines
        ])

    def _correct_numeric_discrepancy(self, revaluated_lines, expected_sum):
        """Checks whether a numeric discrepancy is in place for the given
        revaluation lines and carries out a correction if necessary.

        Args:
            revaluated_lines: The computed revaluation lines, as a list.
            expected_sum: The expected monetary sum of the revaluation journal
                entry which should match the sum of the revaluation lines.

        Returns:
            True if the numeric correction was performed, False otherwise.
        """
        if not revaluated_lines:
            return False

        total_computed = self._compute_actual_total_of(revaluated_lines)
        if self._needs_numeric_correction(total_computed, expected_sum):
            self._correct_numeric(revaluated_lines, total_computed, expected_sum)
            return True

        return False

    def _create_aml_pair(self, template_debit, template_credit, account, value):
        """Creates an account move line debit-credit-pair based on
        the given template dict values.

        Args:
            template_debit: The dict values for the debit line.
                Is not changed by this operation but copied.
            template_credit: The dict values for the credit line.
                Is not changed by this operation but copied.
            account: The AccountAnalyticAccount record to set for the returned
                debit-credit-pair of account move lines. May be falsy which
                will not set any analytic account.
            value: The debit/credit monetary value that the created
                lines should have, as a numeric.

        Returns:
            A debit-credit-pair of account move line dict vals.
            Debit line first, credit line second.
        """
        debit = template_debit.copy()
        credit = template_credit.copy()
        debit.update({
            'debit': float(abs(value)),
            'credit': 0.0,
            'analytic_account_id': account.id if account else False,
        })
        credit.update({
            'debit': 0.0,
            'credit': float(abs(value)),
            'analytic_account_id': account.id if account else False,
        })

        return debit, credit

    @staticmethod
    def activate_on(recordset):
        """Marks the given recordset as requiring a stock revaluation.

        Args:
            recordset: A ProductProduct recordset which has observed a change
                in the products for which an analytic-account-based inventory
                revaluation should occur.

        Returns:
            The given recordset, with an added mark, in its environment
            context or otherwise.
        """
        return recordset.with_context(
            stock_quant_analytic_revaluate_aml_aa=True
        )
