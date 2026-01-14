# -*- coding: utf-8 -*-
{
    'name': 'BP Postpay Analytics',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Multi-Company Multi-Currency Postpay Analytics',
    'description': """
BP Postpay Analytics
===================

Clean implementation of multi-company and multi-currency postpay analytics:

* Company-scoped exposure calculations
* Multi-currency support without conversions  
* Payment timing metrics
* Credit utilization tracking
* Enhanced partner analytics

Key Features:
- Multi-company data isolation
- Per-currency exposure tracking
- Time-to-clear payment analytics
- Credit availability monitoring
    """,
    'author': 'Blackpaw Innovations',
    'website': 'https://blackpaw-innovations.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'sale',
        'contacts',
    ],
    'data': [
        # Clean module - no data files
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}