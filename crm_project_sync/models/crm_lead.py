from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    project_id = fields.Many2one('project.project', string='Project')

    def action_create_project(self):
        for lead in self:
            partner_name = lead.partner_id.name if lead.partner_id else lead.name
            project_name = f"{partner_name}'s Project"
            project_vals = {
                'name': project_name,
                'lead_id': lead.id,
            }
            project = self.env['project.project'].create(project_vals)
            lead.project_id = project.id       

            # Create default stages for the new project
            default_stages = [
                {'name': 'New', 'project_ids': [(4, project.id)]},
                {'name': 'In Progress', 'project_ids': [(4, project.id)]},
                {'name': 'Done', 'project_ids': [(4, project.id)]},
            ]
            for stage_vals in default_stages:
                self.env['project.task.type'].create(stage_vals)

            # Create default tasks for the new project
            default_tasks = [
                "Site Assessment & Measurement",
                "Client Brief & Requirement Gathering",
                "Cost Estimation & Quotation",
                "Construction Execution",
                "Final Inspection & Handover",
            ]
            for task_name in default_tasks:
                task_vals = {
                    'name': task_name,
                    'project_id': project.id,
                    'partner_id': lead.partner_id.id if lead.partner_id else False,
                    # Add other fields as needed, but make sure they exist on project.task
                }
                self.env['project.task'].create(task_vals)

    def open_project(self):
        self.ensure_one()
        if self.project_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project',
                'res_model': 'project.project',
                'view_mode': 'form',
                'res_id': self.project_id.id,
                'target': 'current',
            }
