##############################################################################
# Copyright (c) 2023 brain-tec AG (https://braintec.com)
# All Rights Reserved
#
# Licensed under the AGPL-3.0 (http://www.gnu.org/licenses/agpl.html).
# See LICENSE file for full licensing details.
##############################################################################

{
    "name": "Stock Quant Analytic",
    "author": "Odoo Community Association (OCA), brain-tec AG",
    "license": "AGPL-3",
    "version": "15.0.1.1.0",
    "summary": "Stock Quant Analytic",
    "category": "Warehouse Management",
    "website": "https://github.com/OCA/account-analytic",
    "images": [],
    "depends": [
        "stock",
        "analytic",
        "stock_analytic",
        "stock_account",
    ],
    "data": [
        "views/stock_quant_views.xml",
        "views/stock_location_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "qweb": [],
    "test": [],
    "js": [],
    "external_dependencies": {},
    "installable": True,
    "application": False,
    "auto_install": True,
}
