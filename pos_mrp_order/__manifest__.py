{
    'name': 'Make MRP Orders from POS',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': """Generate Automatic MRP orders from POS.""",
    'description': """This module enables to create automatic MRP orders after 
    selling through POS.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['point_of_sale', 'mrp', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_mrp_order/static/src/overrides/components/payment_screen/payment_screen.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
