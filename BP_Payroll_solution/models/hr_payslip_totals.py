from odoo import api, fields, models


class HrPayslipTotals(models.Model):
    _inherit = "hr.payslip"

    total_earnings = fields.Monetary(
        string="Total Earnings",
        currency_field="currency_id",
        compute="_compute_totals_bp",
        store=False,
    )
    total_deductions = fields.Monetary(
        string="Total Deductions",
        currency_field="currency_id",
        compute="_compute_totals_bp",
        store=False,
    )
    total_employer_cost = fields.Monetary(
        string="Employer Costs",
        currency_field="currency_id",
        compute="_compute_totals_bp",
        store=False,
    )
    total_net_pay = fields.Monetary(
        string="Net Pay",
        currency_field="currency_id",
        compute="_compute_totals_bp",
        store=True,
    )
    
    # Fields for Dashboard (Stored for read_group)
    total_gross = fields.Monetary(
        string="Total Gross",
        currency_field="currency_id",
        compute="_compute_totals_bp",
        store=True,
    )
    total_net = fields.Monetary(
        string="Total Net",
        currency_field="currency_id",
        compute="_compute_totals_bp",
        store=True,
    )
    total_deduction = fields.Monetary(
        string="Total Deduction",
        currency_field="currency_id",
        compute="_compute_totals_bp",
        store=True,
    )

    @api.depends("line_ids.total", "line_ids.category_id.code")
    def _compute_totals_bp(self):
        for slip in self:
            earnings = deductions = employer_cost = net = 0.0
            
            lines_by_code = {line.code: line for line in slip.line_ids}
            
            # Earnings
            if 'GROSS' in lines_by_code:
                earnings = lines_by_code['GROSS'].total
            else:
                earnings = sum(line.total for line in slip.line_ids if line.category_id.code == 'EARN')
            
            # Deductions
            if 'TOTAL_DED' in lines_by_code:
                deductions = lines_by_code['TOTAL_DED'].total
            else:
                deductions = sum(abs(line.total) for line in slip.line_ids if line.category_id.code == 'DED')
            
            # Employer Cost
            employer_cost = sum(abs(line.total) for line in slip.line_ids if line.category_id.code == 'EMP')
            
            # Net
            if 'NET' in lines_by_code:
                net = lines_by_code['NET'].total
            else:
                net = earnings - deductions

            slip.total_earnings = earnings
            slip.total_deductions = deductions
            slip.total_employer_cost = employer_cost
            slip.total_net_pay = net
            
            # Dashboard fields
            slip.total_gross = earnings
            slip.total_net = net
            slip.total_deduction = deductions
