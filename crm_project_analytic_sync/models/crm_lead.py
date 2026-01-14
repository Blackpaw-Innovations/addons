from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    project_id = fields.Many2one('project.project', string='Project')
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
        copy=False,
    )

    @api.model
    def create(self, vals):
        lead = super().create(vals)
        # Always select the "Projects" analytic plan
        plan = self.env['account.analytic.plan'].search([('name', '=', 'Projects')], limit=1)
        if not plan:
            raise ValueError("Analytic Plan 'Projects' not found. Please create it in Accounting > Configuration > Analytic Plans.")
        analytic_account = self.env['account.analytic.account'].create({
            'name': lead.name or 'Opportunity',
            'plan_id': plan.id,
        })
        lead.analytic_account_id = analytic_account.id
        return lead

    def action_create_project(self):
        for lead in self:
            partner_name = lead.partner_id.name if lead.partner_id else lead.name
            project_name = f"{partner_name}'s Project"
            # Create the project and link to the lead
            project_vals = {
                'name': project_name,
                'lead_id': lead.id,
            }
            project = self.env['project.project'].create(project_vals)
            lead.project_id = project.id

            # Find or create the "Projects" analytic plan
            plan = self.env['account.analytic.plan'].search([('name', '=', 'Projects')], limit=1)
            plan_id = plan.id if plan else False

            # Create analytic account for the project
            analytic_account = self.env['account.analytic.account'].create({
                'name': project_name,
                'plan_id': plan_id,
            })
            # Link analytic account to both project and lead
            project.analytic_account_id = analytic_account.id
            lead.analytic_account_id = analytic_account.id

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
                }
                self.env['project.task'].create(task_vals)
        return True