This module allows to add **analytic accounts** on stock moves using **Inventory Adjustments**.
When applying, adds the analytic account from the *stock.quant* to the *stock.move*.
When adjusting product prices (standard price/cost), the created journal entry representing
the changed stock valuation within the inventory will have its lines grouped by the analytic
accounts set on the inventory quants.
A default analytic account and analytic tags can be set on newly created stock
quants based on their stock location.
