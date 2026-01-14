{
    'name': 'CRM Project Analytic Sync',
    'version': '17.0.1.0.0',
    'summary': 'Syncs CRM Opportunities with Projects and Analytic Accounts',
    'description': 'Automatically creates a project and analytic account from CRM opportunities and links them.',
    'author': 'BlackPaw Innovations',
    'website': 'https://blackpawinnovation.com',    
    'depends': ['crm', 'project', 'analytic'],
    'data': [
        'views/crm_lead_views.xml',      
    ],
    'installable': True,
    'application': False,
}