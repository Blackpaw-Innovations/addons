{
    "name": "Blackpaw Appraisal",
    "summary": "Employee appraisal workflows with configurable templates and reviews.",
    "version": "17.0.1.0",
    "author": "Blackpaw Innovations",
    "website": "https://www.blackpawinnovations.com",
    "category": "Human Resources/Appraisal",
    "license": "LGPL-3",
    "depends": [
        "base",
        "hr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/appraisal_template_views.xml",
    ],
    "application": True,
    "installable": True,
    "description": """
Blackpaw Appraisal
------------------
Foundation module for employee appraisal workflows on Odoo 17 Community. Extends HR Appraisal to support configurable templates, multi-reviewer input, and reporting.
"""
}
