from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count')
    bp_display_payslip_button = fields.Boolean(compute='_compute_bp_display_payslip_button')

    def _compute_bp_display_payslip_button(self):
        for employee in self:
            employee.bp_display_payslip_button = employee.company_id.bp_show_payslip_smart_button

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = self.env['hr.payslip'].search_count([('employee_id', '=', employee.id)])

    def action_view_payslips(self):
        self.ensure_one()
        return {
            'name': 'Payslips',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
