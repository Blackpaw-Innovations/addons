# -*- coding: utf-8 -*-
{
    'name': 'Stock Minimum',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Flags products whose on-hand quantity is at or below a minimum quantity.',
    'description': """
This module adds a minimum_qty field and a below_minimum boolean flag on product.template to help track products that fall below their minimum stock levels. It includes a scheduled cron job to automatically update the flags and search filters to easily find products below minimum quantities.
    """,
    'author': 'Blackpaw Innovations',
    'website': 'https://blackpawinnovations.com',
    'license': 'LGPL-3',
    'depends': [
        'product',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
}