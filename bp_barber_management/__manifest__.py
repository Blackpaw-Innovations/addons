# -*- coding: utf-8 -*-

{
    'name': 'Barber Management',
    'version': '17.0.2.1.0',
    'summary': 'Complete barbershop management: appointments, POS, packages, consumables, analytics & maintenance.',
    'author': 'Blackpaw Innovations',
    'website': 'https://blackpawinnovations.com',
    # 'maintainers': ['Blackpaw Innovations'],
    'category': 'Services/Barbershop',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
        'point_of_sale',
        'website',
        'website_sale',
        'portal',
    ],
    'data': [
        'security/bp_barber_groups.xml',
        'security/ir.model.access.csv',
        
        'views/menu.xml',
        'views/service_views.xml',
        'views/chair_views.xml',
        'views/barber_views.xml',
        'views/appointment_views.xml',
        'views/schedule_views.xml',
        'views/website_templates.xml',
        'views/pos_config_views.xml',
        'views/product_template_views.xml',

        'views/consumable_bom_views.xml',
        'views/consumable_usage_views.xml',
        'views/consumable_supply_views.xml',
        'wizard/consumable_issue_wizard_views.xml',

        'views/kiosk_templates.xml',
        'data/ir_sequence_data.xml',
        'data/mail_templates.xml',
        'data/ir_cron_barber_notifications.xml',
        'views/notification_settings_views.xml',
        'views/notification_portal_templates.xml',

        'report/appointment_report_templates.xml',
        'report/appointment_report_actions.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'demo': [
        'data/demo_services.xml',
        'data/demo_barbers.xml',
        'data/demo_schedules.xml',
        'data/demo_appointments.xml',
        'data/demo_products_retail.xml',
        'data/demo_pos_config.xml',
    ],
    'assets': {

        'web.assets_frontend': [
            'bp_barber_management/static/src/js/booking_slots.js',
            'bp_barber_management/static/src/js/kiosk_app.js',
            'bp_barber_management/static/src/xml/kiosk_templates.xml',
            'bp_barber_management/static/src/scss/kiosk.scss',
        ],
        'web.assets_backend': [
            'bp_barber_management/static/src/scss/kanban_views.scss',
        ],
        # 'point_of_sale._assets_pos': [
        #     'bp_barber_management/static/src/js/pos_test_minimal.js',
        # ],
        'web.report_assets_common': [
            'bp_barber_management/static/src/scss/report.scss',
        ],
    },
    'application': True,
    'installable': True,
    # 'post_init_hook': 'post_init_hook',
}