from odoo import models, fields, api
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    #is_won_stage = fields.Boolean(string="Is Won Stage", compute='_compute_is_won_stage', store=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    is_won_stage = fields.Boolean(compute='_compute_is_won_stage', store=True)
    show_convert_button = fields.Boolean(
        string="Show Convert to Employee Button",
        compute='_compute_show_convert_button',
        store=True
    )

    @api.depends('stage_id')
    def _compute_show_convert_button(self):
        for lead in self:
            lead.show_convert_button = bool(lead.stage_id and lead.stage_id.is_won)

    @api.depends('stage_id.is_won')
    def _compute_is_won_stage(self):
        for lead in self:
            lead.is_won_stage = lead.stage_id.is_won


    def action_convert_to_employee(self):
        for lead in self:
            if not lead.partner_id:
                raise UserError("No customer linked to this opportunity.")

            if lead.employee_id:
                raise UserError("Already converted to a member")

            partner = lead.partner_id

            employee = self.env['hr.employee'].create({
                'name': partner.name,
                'work_email': partner.email,
                'work_phone': partner.phone or partner.mobile,
            })

            lead.employee_id = employee
