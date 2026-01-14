# -*- coding: utf-8 -*-
# OdooES El Salvador - https://odooes.com
# @author: Enmanuele <enmanuele777@gmail.com>
# License LGPL-3
{
    'name': 'POS Pre Print',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': """Pre Print""",
    'description': """
          Allows you to print a pre-account at the retail point of sale similar to the restaurant type point of sale.
    """,
    'author': 'OdooES El Salvador',
    'maintainer': 'Enmanuele <enmanuele777@gmail.com>',
    'website': 'https://odooes.com',
    'support': 'odooes.sv@gmail.com',
    #'price': 25.00,
    #'currency': 'USD',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'pos_restaurant'
    ],
    'data': [
        'views/res_config_settings_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'images': [
        'static/description/images/parameters.png',
        'static/description/images/function.png',
        'static/description/images/function_one.png',
        'static/description/images/my_logo.png'
    ],
    'module_type': 'official',
    'installable': True,
    'application': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: