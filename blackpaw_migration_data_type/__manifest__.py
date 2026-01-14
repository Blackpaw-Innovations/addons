{
    'name': 'Migration Data Type',
    'version': '1.0',
    'depends': ['crm'],
    'author': 'Blackpaw Innovations',
    'category': 'CRM',
    'summary': 'Add Migration Data Type tags to CRM Leads',
    'description': 'This module allows tagging CRM Leads with custom Migration Data Types.',
    'data': [
	'security/ir.model.access.csv',
        'views/migration_data_type_views.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
