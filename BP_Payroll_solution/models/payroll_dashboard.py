from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class BpPayrollDashboardNote(models.Model):
    _name = "bp.payroll.dashboard.note"
    _description = "Payroll Dashboard Note"

    name = fields.Char("Title", required=True)
    content = fields.Html("Content")
    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)


class PayrollDashboard(models.AbstractModel):
    _name = "bp.payroll.dashboard"
    _description = "Payroll Dashboard Service"

    @api.model
    def get_dashboard_data(self):
        company = self.env.company
        employee_model = self.env["hr.employee"].sudo()
        contract_model = self.env["hr.contract"].sudo()
        payslip_model = self.env["hr.payslip"].sudo()
        payslip_run_model = self.env["hr.payslip.run"].sudo()

        # 1. Missing from batches
        open_runs = payslip_run_model.search([("state", "!=", "done")])
        open_run_employee_ids = set(open_runs.mapped("slip_ids.employee_id.id"))
        open_contracts = contract_model.search(
            [("state", "=", "open"), ("company_id", "=", company.id)]
        )
        employees_open_contract = {c.employee_id.id for c in open_contracts}
        missing_ids = [emp_id for emp_id in employees_open_contract if emp_id not in open_run_employee_ids]
        missing_from_batches = len(missing_ids)

        # 2. Multiple open payslips
        multiple_open_payslips_count, multiple_open_payslips_domain = self._compute_multiple_open_payslips(payslip_model, company.id)

        # 3. Missing Bank
        missing_bank_domain = [("company_id", "=", company.id), "|", ("bank_account_id", "=", False), ("bank_account_id", "=", None)]
        missing_bank = employee_model.search_count(missing_bank_domain)

        # 4. Missing ID
        missing_id_domain = [
                ("company_id", "=", company.id),
                "|",
                ("identification_id", "=", False),
                ("identification_id", "=", None),
            ]
        missing_identification = employee_model.search_count(missing_id_domain)

        pay_runs = self._prepare_pay_runs(payslip_run_model, company.id)
        employer_cost = self._prepare_monthly_totals(payslip_model, company.id, "total_net")
        employee_count = self._prepare_new_hires(employee_model, company.id)
        notes = self._prepare_notes()

        return {
            "warnings": [
                {
                    "label": "Employees (With Running Contracts) missing from open batches",
                    "value": missing_from_batches,
                    "color": "warning",
                    "action_model": "hr.employee",
                    "action_domain": [("id", "in", missing_ids)],
                },
                {
                    "label": "Employees With Multiple Open Payslips of Same Type",
                    "value": multiple_open_payslips_count,
                    "color": "gold",
                    "action_model": "hr.payslip",
                    "action_domain": multiple_open_payslips_domain,
                },
                {
                    "label": "Employees Without Bank account Number",
                    "value": missing_bank,
                    "color": "pink",
                    "action_model": "hr.employee",
                    "action_domain": missing_bank_domain,
                },
                {
                    "label": "Employees Without Identification Number",
                    "value": missing_identification,
                    "color": "indigo",
                    "action_model": "hr.employee",
                    "action_domain": missing_id_domain,
                },
            ],
            "pay_runs": pay_runs,
            "employer_cost": employer_cost,
            "employee_count": employee_count,
            "notes": notes,
        }

    def _prepare_notes(self):
        notes = self.env["bp.payroll.dashboard.note"].search([("company_id", "=", self.env.company.id)])
        return [{"id": n.id, "name": n.name, "content": n.content} for n in notes]

    @api.model
    def create_note(self, name, content):
        note = self.env["bp.payroll.dashboard.note"].create({
            "name": name,
            "content": content,
        })
        return {"id": note.id, "name": note.name, "content": note.content}

    @api.model
    def update_note(self, note_id, name, content):
        note = self.env["bp.payroll.dashboard.note"].browse(note_id)
        if note.exists():
            note.write({"name": name, "content": content})
            return True
        return False

    @api.model
    def delete_note(self, note_id):
        note = self.env["bp.payroll.dashboard.note"].browse(note_id)
        if note.exists():
            note.unlink()
            return True
        return False

    def _compute_multiple_open_payslips(self, payslip_model, company_id):
        groups = payslip_model.read_group(
            domain=[("state", "in", ["draft", "verify"]), ("company_id", "=", company_id)],
            fields=["employee_id"],
            groupby=["employee_id"],
        )
        emp_ids = [g["employee_id"][0] for g in groups if g["employee_id_count"] and g["employee_id_count"] > 1]
        return len(emp_ids), [("employee_id", "in", emp_ids), ("state", "in", ["draft", "verify"])]

    def _prepare_pay_runs(self, payslip_run_model, company_id):
        runs = payslip_run_model.search(
            [("company_id", "=", company_id)], order="date_end desc", limit=4
        )
        state_labels = {"draft": "Ready", "verify": "Ready", "done": "Done"}
        state_classes = {"draft": "info", "verify": "info", "done": "success"}
        data = []
        for run in runs:
            data.append(
                {
                    "id": run.id,
                    "name": run.name,
                    "period": self._format_period(run.date_end),
                    "slip_count": len(run.slip_ids),
                    "state_label": state_labels.get(run.state, run.state),
                    "state_class": state_classes.get(run.state, "info"),
                }
            )
        return data

    def _prepare_monthly_totals(self, payslip_model, company_id, field_name):
        end_date = date.today().replace(day=1)
        months = []
        labels = []
        for i in range(5, -1, -1):
            month_date = end_date - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
            domain = [
                ("company_id", "=", company_id),
                ("date_to", ">=", month_start),
                ("date_to", "<=", month_end),
                ("state", "in", ["done", "paid"]),
            ]
            slips = payslip_model.search_read(domain, [field_name])
            total = sum(s.get(field_name, 0.0) for s in slips)
            months.append(round(total, 2))
            labels.append(month_date.strftime("%b %Y"))
        return {"labels": labels, "values": months}

    def _prepare_new_hires(self, employee_model, company_id):
        end_date = date.today().replace(day=1)
        months = []
        labels = []
        for i in range(5, -1, -1):
            month_date = end_date - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
            domain = [
                ("company_id", "=", company_id),
                ("create_date", ">=", month_start),
                ("create_date", "<=", month_end),
            ]
            count = employee_model.search_count(domain)
            months.append(count)
            labels.append(month_date.strftime("%b %Y"))
        return {"labels": labels, "values": months}

    def _format_period(self, end_date):
        if not end_date:
            return ""
        return end_date.strftime("%B %Y")
