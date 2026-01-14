{
    "name": "BP POS Invoice Payment Bridge",
    "summary": "Pay customer invoices (deposits and balances) directly from POS and reconcile them in accounting.",
    "version": "17.0.1.0.0",
    "author": "Blackpaw Innovations",
    "website": "https://blackpaw.africa",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "account", "bp_optical_pos"],
    "data": [
        "data/product_data.xml",
        "security/ir.model.access.csv",
        "views/pos_config_views.xml",
        "views/pos_order_views.xml",
        "views/account_move_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "bp_pos_pay_invoice/static/src/js/*.js",
            "bp_pos_pay_invoice/static/src/xml/*.xml",
        ],
    },
}
