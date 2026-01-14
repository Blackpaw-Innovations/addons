from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    lead_id = fields.Many2one('crm.lead', string='Lead')