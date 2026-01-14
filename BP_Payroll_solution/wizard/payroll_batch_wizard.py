from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PayrollBatchWizard(models.TransientModel):
    _name = "bp.payroll.batch.wizard"
    _description = "Generate Payslips for Batch"

    run_id = fields.Many2one("hr.payslip.run", string="Batch", required=True)
    mode = fields.Selection(
        [("all", "All Employees"), ("dept", "By Department"), ("selected", "Selected Employees")],
        string="Generation Mode",
        default="all",
        required=True,
    )
    department_id = fields.Many2one("hr.department", string="Department")
    employee_ids = fields.Many2many("hr.employee", string="Employees")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "hr.payslip.run":
            res["run_id"] = self.env.context.get("active_id")
        return res

    def action_generate(self):
        self.ensure_one()
        run = self.run_id
        employees = self.env["hr.employee"]

        if self.mode == "all":
            employees = self.env["hr.employee"].search([("company_id", "=", run.company_id.id)])
        elif self.mode == "dept":
            if not self.department_id:
                raise UserError(_("Please select a department."))
            employees = self.env["hr.employee"].search([
                ("department_id", "=", self.department_id.id),
                ("company_id", "=", run.company_id.id)
            ])
        elif self.mode == "selected":
            employees = self.employee_ids

        # Filter out employees who already have a slip in this run
        existing_employees = run.slip_ids.mapped("employee_id")
        employees = employees - existing_employees

        if not employees:
            raise UserError(_("No new employees found to generate payslips for."))

        Payslip = self.env["hr.payslip"]
        slips_vals = []
        for emp in employees:
            # Check for active contract
            contract = self.env["hr.contract"].search([
                ("employee_id", "=", emp.id),
                ("state", "=", "open"),
                ("company_id", "=", run.company_id.id)
            ], limit=1)
            
            if not contract:
                continue # Skip employees without active contract

            slips_vals.append({
                "employee_id": emp.id,
                "date_from": run.date_start,
                "date_to": run.date_end,
                "contract_id": contract.id,
                "structure_id": contract.structure_id.id,
                "payslip_run_id": run.id,
                "name": _("Payslip %s") % emp.name,
                "company_id": run.company_id.id,
            })

        if slips_vals:
            slips = Payslip.create(slips_vals)
            # Compute the slips immediately? User said "auto created", usually implies computed too.
            # But standard Odoo separates creation and computation.
            # Let's just create them for now, user can click "Compute" on the batch.
            # Or we can call compute. Let's call compute to be helpful.
            slips.action_compute_inputs()
        
        return {"type": "ir.actions.act_window_close"}
