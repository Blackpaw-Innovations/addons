{
    "name": "BP LPG Solution",
    "version": "17.0.1.0.0",
    "category": "Inventory",
    "summary": "LPG cylinder exchange and lifecycle tracking",
    "author": "Blackpaw Innovations",
    "license": "LGPL-3",
    "depends": ["sale", "stock", "account", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
        "views/stock_lot_views.xml",
        "views/sale_order_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
