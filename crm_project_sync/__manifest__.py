{
    'name': 'CRM Project Sync',
    'version': '1.0',
    'summary': 'Create projects from CRM opportunities',
    'description': """
        Adds project creation button to CRM opportunities
        Links projects to customers and opportunities
    """,
    'category': 'Sales/CRM',
    'author': 'BlackPaw Innovations',
    'depends': ['crm', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/project_project_views.xml',  # <-- Add this line
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}