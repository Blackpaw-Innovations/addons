from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class HrSalaryRule(models.Model):
    _name = "hr.salary.rule"
    _description = "Salary Rule"
    _order = "sequence, code"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one("hr.salary.rule.category", required=True)
    amount_select = fields.Selection(
        [("fixed", "Fixed Amount"), ("percentage", "Percentage"), ("code", "Python Code")],
        default="fixed",
        required=True,
        help="How the amount is computed.",
    )
    amount = fields.Float(default=0.0, help="Fixed amount or percentage value when applicable.")
    quantity = fields.Float(default=1.0, help="Quantity multiplier; for code mode set inside python if needed.")
    python_code = fields.Text(
        help="Python code to compute result. Provide variable 'result' in the namespace."
    )
    condition_country_code = fields.Selection(
        selection=[("KE", "Kenya")],
        string="Country Restriction",
        help="If set, rule only applies when the payslip/company payroll country matches.",
    )
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        default=False,
        help="Technical field for UX purpose.",
    )
    active = fields.Boolean(default=True)
    struct_ids = fields.Many2many(
        "hr.payroll.structure", string="Structures", relation="hr_structure_rule_rel"
    )
    note = fields.Text()

    def compute_rule_amount(self, localdict):
        """Compute amount using localdict (payslip context)."""
        self.ensure_one()
        if self.amount_select == "fixed":
            return self.amount * self.quantity
        if self.amount_select == "percentage":
            base_amount = localdict.get("base_amount", 0.0)
            return base_amount * (self.amount / 100.0) * self.quantity
        if self.amount_select == "code" and self.python_code:
            safe_dict = dict(localdict)
            safe_dict.update({"result": 0.0, "hasattr": hasattr})
            safe_eval(self.python_code, safe_dict, mode="exec", nocopy=True)
            return safe_dict.get("result") or 0.0
        return 0.0


class HrPayrollStructure(models.Model):
    _name = "hr.payroll.structure"
    _description = "Payroll Structure"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    rule_ids = fields.Many2many(
        "hr.salary.rule", string="Salary Rules", relation="hr_structure_rule_rel"
    )
    note = fields.Text()


class HrPayslipWorkedDays(models.Model):
    _name = "hr.payslip.worked_days"
    _description = "Payslip Worked Days"

    name = fields.Char(required=True)
    code = fields.Char()
    number_of_days = fields.Float(default=0.0)
    number_of_hours = fields.Float(default=0.0)
    slip_id = fields.Many2one("hr.payslip", required=True, ondelete="cascade")


class HrPayslipInput(models.Model):
    _name = "hr.payslip.input"
    _description = "Payslip Input"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    amount = fields.Float(default=0.0)
    slip_id = fields.Many2one("hr.payslip", required=True, ondelete="cascade")
    note = fields.Text()


class HrPayslipLine(models.Model):
    _name = "hr.payslip.line"
    _description = "Payslip Line"
    _order = "sequence, code"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one("hr.salary.rule.category")
    amount = fields.Float(default=0.0)
    quantity = fields.Float(default=1.0)
    rate = fields.Float(default=100.0)
    total = fields.Float(compute="_compute_total", store=True)
    debit = fields.Float(compute="_compute_debit_credit", store=True)
    credit = fields.Float(compute="_compute_debit_credit", store=True)
    slip_id = fields.Many2one("hr.payslip", required=True, ondelete="cascade")
    note = fields.Text()
    salary_rule_id = fields.Many2one("hr.salary.rule", string="Salary Rule", ondelete="set null")
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        default=False,
        help="Technical field for UX purpose.",
    )

    @api.depends("amount", "quantity", "rate")
    def _compute_total(self):
        for line in self:
            line.total = line.amount * line.quantity * (line.rate / 100.0)

    @api.depends("total", "category_id")
    def _compute_debit_credit(self):
        for line in self:
            code = (line.category_id.code or "").upper() if line.category_id else ""
            if code in ("DED", "STAT", "TAX", "STAT_DED", "RELIEFS", "TOT_DED"):
                line.debit = abs(line.total)
                line.credit = 0.0
            else:
                line.debit = 0.0
                line.credit = line.total


class HrPayslip(models.Model):
    _name = "hr.payslip"
    _description = "Payslip"
    _order = "date_to desc, employee_id"

    name = fields.Char(default="Payslip")
    employee_id = fields.Many2one("hr.employee", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contract")
    company_id = fields.Many2one(
        "res.company", related="employee_id.company_id", store=True, readonly=True
    )
    department_id = fields.Many2one(
        "hr.department", related="employee_id.department_id", store=True, readonly=True
    )
    structure_id = fields.Many2one("hr.payroll.structure", string="Structure")
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    def _default_stage_id(self):
        return self.env["hr.payslip.stage"].search(
            [("company_id", "in", (self.env.company.id, False))],
            order="sequence asc",
            limit=1,
        )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env["hr.payslip.stage"].search(
            [("company_id", "in", (self.env.company.id, False))], order=order
        )

    stage_id = fields.Many2one(
        "hr.payslip.stage",
        string="Stage",
        default=_default_stage_id,
        group_expand="_read_group_stage_ids",
        tracking=True,
        copy=False,
        index=True,
    )
    state = fields.Selection(
        related="stage_id.state",
        store=True,
        readonly=True,
    )
    line_ids = fields.One2many("hr.payslip.line", "slip_id", string="Payslip Lines")
    worked_days_line_ids = fields.One2many(
        "hr.payslip.worked_days", "slip_id", string="Worked Days"
    )
    input_line_ids = fields.One2many("hr.payslip.input", "slip_id", string="Inputs")
    payslip_run_id = fields.Many2one("hr.payslip.run", string="Batch")
    bp_ready_for_payment = fields.Boolean(default=False)
    bp_payment_reference = fields.Char(
        string="Payment Reference",
        help="Reference used when exporting to bank or payment batches.",
    )
    bp_prevalidated = fields.Boolean(
        string="Pre-Validated",
        help="Set when the payslip passes pre-validation checks.",
    )
    bp_finance_approved = fields.Boolean(
        string="Finance Approved",
        help="Indicates that finance has approved the payslip.",
    )
    total_gross = fields.Float(compute="_compute_totals", store=True)
    total_net = fields.Float(compute="_compute_totals", store=True)
    total_deduction = fields.Float(compute="_compute_totals", store=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
        store=True,
    )
    payroll_country_code = fields.Selection(
        selection=[("KE", "Kenya")],
        string="Payroll Country",
        help="Localization for payroll computation. Defaulted from company country.",
        default=lambda self: "KE"
        if self.env.company.country_id and self.env.company.country_id.code == "KE"
        else False,
    )

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if not self.employee_id:
            self.contract_id = False
            self.structure_id = False
            return

        # Find active contract
        contract = self.env["hr.contract"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("state", "=", "open"),
            ],
            limit=1,
        )
        if contract:
            self.contract_id = contract
            if contract.structure_id:
                self.structure_id = contract.structure_id

    @api.onchange("payslip_run_id")
    def _onchange_payslip_run_id(self):
        if self.payslip_run_id:
            self.date_from = self.payslip_run_id.date_start
            self.date_to = self.payslip_run_id.date_end

    @api.depends("line_ids.total", "line_ids.category_id")
    def _compute_totals(self):
        for slip in self:
            gross = net = deductions = 0.0
            
            # Map lines by code for quick access
            lines_by_code = {line.code: line for line in slip.line_ids}
            
            # 1. Gross
            if 'GROSS' in lines_by_code:
                gross = lines_by_code['GROSS'].total
            else:
                # Sum EARN lines if GROSS rule is missing
                gross = sum(line.total for line in slip.line_ids if line.category_id.code == 'EARN')

            # 2. Deductions
            if 'TOTAL_DED' in lines_by_code:
                deductions = lines_by_code['TOTAL_DED'].total
            else:
                # Sum DED lines
                deductions = sum(abs(line.total) for line in slip.line_ids if line.category_id.code == 'DED')

            # 3. Net
            if 'NET' in lines_by_code:
                net = lines_by_code['NET'].total
            else:
                net = gross - deductions
            
            slip.total_gross = gross
            slip.total_net = net
            slip.total_deduction = deductions

    def action_prevalidate(self):
        for slip in self:
            slip._bp_run_prechecks()
            slip.bp_prevalidated = True
        return True

    def _bp_run_prechecks(self):
        self.ensure_one()
        company = self.company_id
        if not self.contract_id:
            raise UserError(_("Payslip %s has no contract.") % self.display_name)
        if company.payroll_requires_bank_account and not self.employee_id.bank_account_id:
            raise UserError(
                _("Employee %s is missing bank account details.")
                % self.employee_id.name
            )
        return True

    def _get_ke_config(self):
        """Return active Kenya config for this payslip company, or False."""
        self.ensure_one()
        company = self.company_id or self.env.company
        return (
            self.env["bp.payroll.ke.config"]
            .sudo()
            .search([("company_id", "=", company.id), ("active", "=", True)], limit=1)
        )

    def action_mark_ready_for_payment(self):
        for slip in self:
            if slip.state not in ("done", "paid"):
                raise UserError(
                    _("Only confirmed or paid payslips can be marked ready for payment.")
                )
            slip.bp_ready_for_payment = True
        return True

    def action_approve_stage(self):
        """Move to the next stage if authorized."""
        for slip in self:
            if slip.stage_id.responsible_user_ids and self.env.user not in slip.stage_id.responsible_user_ids:
                raise UserError(_("You are not authorized to approve this stage."))
            
            next_stage = self.env["hr.payslip.stage"].search([
                ("sequence", ">", slip.stage_id.sequence),
                ("company_id", "in", (slip.company_id.id, False))
            ], order="sequence asc", limit=1)
            
            if next_stage:
                slip.stage_id = next_stage
                if next_stage.state == "payment_ready":
                    slip.bp_ready_for_payment = True

    def _move_to_state(self, target_state):
        """Move to a stage corresponding to the target state."""
        for slip in self:
            target_stage = self.env["hr.payslip.stage"].search([
                ("state", "=", target_state),
                ("company_id", "in", (slip.company_id.id, False))
            ], limit=1)
            if target_stage:
                slip.stage_id = target_stage
                if target_state == "payment_ready":
                    slip.bp_ready_for_payment = True

    def action_verify(self):
        self._move_to_state("verify")

    def action_submit_finance(self):
        self._move_to_state("approval")

    def action_finance_approve(self):
        self.write({"bp_finance_approved": True})

    def action_director_approve(self):
        self._move_to_state("payment_ready")

    def action_pay(self):
        return {
            "name": _("Register Payment"),
            "type": "ir.actions.act_window",
            "res_model": "bp.payroll.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_payslip_ids": self.ids},
        }

    def action_set_paid(self):
        self._move_to_state("done")

    def action_reject(self):
        self._move_to_state("draft")
        self.write({"bp_prevalidated": False, "bp_ready_for_payment": False})

    def action_done(self):
        self._move_to_state("done")

    def action_reset_to_draft(self):
        self._move_to_state("draft")
        self.write({"bp_prevalidated": False, "bp_ready_for_payment": False})

    def action_download_csv(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/print/payslip/csv/%s' % self.id,
            'target': 'new',
        }

    def action_compute_inputs(self):
        """Compute payslip lines using structure salary rules with optional Python code."""
        for slip in self:
            slip.line_ids.unlink()
            structure = slip.structure_id
            if not structure:
                # fallback: mirror inputs
                slip.write(
                    {
                        "line_ids": [
                            (0, 0, {"name": line.name, "code": line.code, "amount": line.amount})
                            for line in slip.input_line_ids
                        ]
                    }
                )
                continue

            # Auto-fill inputs from contract if available
            if slip.contract_id:
                contract = slip.contract_id
                input_updates = []
                
                # Map contract fields to input codes
                contract_map = {
                    "PENSION": contract.pension_contribution,
                    "MORTGAGE": contract.mortgage_interest,
                    "INSURANCE": contract.life_insurance + contract.voluntary_medical_insurance,
                    "FOOD": contract.food_allowance,
                    "AIRTIME": contract.airtime_allowance,
                    "EDUCATION": contract.education_benefit,
                    "PENSION_ALLOWANCE": contract.pension_allowance,
                    "HOUSE": contract.house_allowance,
                    "OTHER_ALLOWANCE": contract.other_allowance,
                }

                existing_inputs = {line.code: line for line in slip.input_line_ids}
                
                for code, amount in contract_map.items():
                    if amount > 0:
                        if code in existing_inputs:
                            existing_inputs[code].amount = amount
                        else:
                            input_updates.append((0, 0, {
                                "name": code.replace("_", " ").title(),
                                "code": code,
                                "amount": amount,
                                "slip_id": slip.id,
                            }))
                
                if input_updates:
                    slip.write({"input_line_ids": input_updates})

            categories = {}
            results = {}
            inputs_map = {line.code: line.amount for line in slip.input_line_ids}
            worked_days = {line.code: line.number_of_days for line in slip.worked_days_line_ids}
            base_amount = sum(inputs_map.values())
            localdict = {
                "payslip": slip,
                "employee": slip.employee_id,
                "contract": slip.contract_id,
                "inputs": inputs_map,
                "worked_days": worked_days,
                "categories": categories,
                "results": results,
                "base_amount": base_amount,
                "config_ke": getattr(slip, "_bp_ke_get_config", lambda: False)(),
            }
            lines_vals = []
            for rule in structure.rule_ids.sorted(key=lambda r: (r.sequence, r.id)):
                if not rule.active:
                    continue
                if rule.condition_country_code == "KE":
                    if not getattr(slip, "_bp_ke_is_applicable", lambda: False)():
                        continue
                amount = rule.compute_rule_amount(localdict)
                total = amount
                categories.setdefault(rule.category_id.code or rule.code, 0.0)
                categories[rule.category_id.code or rule.code] += total
                results[rule.code] = total
                localdict["categories"] = categories
                localdict["results"] = results
                lines_vals.append(
                    {
                        "name": rule.name,
                        "code": rule.code,
                        "category_id": rule.category_id.id,
                        "salary_rule_id": rule.id,
                        "amount": amount,
                        "quantity": rule.quantity,
                        "rate": 100.0,
                        "display_type": rule.display_type,
                        "sequence": rule.sequence,
                    }
                )
            slip.write({"line_ids": [(0, 0, vals) for vals in lines_vals]})


class HrPayslipRun(models.Model):
    _name = "hr.payslip.run"
    _description = "Payslip Batch"
    _order = "date_end desc, name"

    name = fields.Char(required=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )

    def _default_stage_id(self):
        return self.env["hr.payslip.stage"].search(
            [("company_id", "in", (self.env.company.id, False))],
            order="sequence asc",
            limit=1,
        )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env["hr.payslip.stage"].search(
            [("company_id", "in", (self.env.company.id, False))], order=order
        )

    stage_id = fields.Many2one(
        "hr.payslip.stage",
        string="Stage",
        default=_default_stage_id,
        group_expand="_read_group_stage_ids",
        tracking=True,
        copy=False,
        index=True,
    )
    state = fields.Selection(
        related="stage_id.state",
        store=True,
        readonly=True,
    )

    slip_ids = fields.One2many("hr.payslip", "payslip_run_id")
    # department_id = fields.Many2one("hr.department", string="Department") # Deprecated
    analytic_account_id = fields.Many2one(
        "account.analytic.account", 
        string="Analytic Account",
        default=lambda self: self.env.company.payroll_analytic_account_id
    )
    bp_note = fields.Text(string="Payroll Note")
    bp_prevalidated = fields.Boolean(
        string="Pre-Validated",
        help="Indicates pre-validation for bank accounts, contracts, and duplicates.",
    )
    bp_finance_approved = fields.Boolean(
        string="Finance Approved",
        help="Indicates that finance has approved the batch.",
    )
    bp_total_gross = fields.Monetary(
        string="Gross Total", compute="_compute_bp_totals", currency_field="currency_id"
    )
    bp_total_net = fields.Monetary(
        string="Net Total", compute="_compute_bp_totals", currency_field="currency_id"
    )
    bp_total_deductions = fields.Monetary(
        string="Employee Deductions",
        compute="_compute_bp_totals",
        currency_field="currency_id",
    )
    bp_total_employer_cost = fields.Monetary(
        string="Employer Cost",
        compute="_compute_bp_totals",
        currency_field="currency_id",
    )
    bp_all_payslips_approved = fields.Boolean(
        string="All Payslips Approved",
        compute="_compute_bp_all_payslips_approved",
        help="True if all payslips in the batch are approved (payment_ready, done, paid, or cancel)."
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", store=True, readonly=True
    )
    payroll_country_code = fields.Selection(
        selection=[("KE", "Kenya")],
        string="Payroll Country",
        help="Localization for payroll computation. Defaulted from company country.",
        default=lambda self: "KE"
        if self.env.company.country_id and self.env.company.country_id.code == "KE"
        else False,
    )

    @api.depends("slip_ids.state")
    def _compute_bp_all_payslips_approved(self):
        for run in self:
            if not run.slip_ids:
                run.bp_all_payslips_approved = False
                continue
            # Consider slips approved if they are ready for payment, paid, or cancelled
            approved_states = ('payment_ready', 'done', 'paid', 'cancel')
            run.bp_all_payslips_approved = all(s.state in approved_states for s in run.slip_ids)

    def action_prevalidate(self):
        for run in self:
            errors = []
            employees = run.slip_ids.mapped("employee_id")
            if len(employees) != len(run.slip_ids):
                errors.append(_("Duplicate payslips found for the same employee."))
            for slip in run.slip_ids:
                try:
                    slip._bp_run_prechecks()
                except UserError as exc:
                    errors.append(str(exc))
            if errors:
                raise UserError("\n".join(errors))
            run.bp_prevalidated = True
        return True

    def action_mark_slips_ready_for_payment(self):
        for run in self:
            slips = run.slip_ids.filtered(lambda s: s.state in ("done", "paid"))
            slips.write({"bp_ready_for_payment": True})
        return True

    def _move_to_state(self, target_state):
        """Move to a stage corresponding to the target state."""
        for run in self:
            target_stage = self.env["hr.payslip.stage"].search([
                ("state", "=", target_state),
                ("company_id", "in", (run.company_id.id, False))
            ], limit=1)
            if target_stage:
                run.stage_id = target_stage

    def action_compute_slips(self):
        for slip in self.slip_ids:
            slip.action_compute_inputs()
        self._move_to_state("verify")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payslips computed successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_done(self):
        self.slip_ids.write({"state": "done", "bp_ready_for_payment": True})
        self._move_to_state("done")

    def action_reset_to_draft(self):
        self.slip_ids.write(
            {
                "state": "draft",
                "bp_prevalidated": False,
                "bp_ready_for_payment": False,
            }
        )
        self._move_to_state("draft")
        self.write({"bp_prevalidated": False, "bp_finance_approved": False})

    def action_open_pay_wizard(self):
        return {
            "name": _("Register Batch Payment"),
            "type": "ir.actions.act_window",
            "res_model": "bp.payroll.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id, "active_model": "hr.payslip.run"},
        }

    def action_open_generate_wizard(self):
        return {
            "name": _("Generate Payslips"),
            "type": "ir.actions.act_window",
            "res_model": "bp.payroll.batch.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id, "active_model": "hr.payslip.run"},
        }

    def action_submit_to_finance(self):
        self._move_to_state("approval")

    def action_finance_approve(self):
        self.write({"bp_finance_approved": True})

    def action_director_approve(self):
        self._move_to_state("payment_ready")

    def action_approve_all_payslips(self):
        for run in self:
            run.slip_ids.action_director_approve()
        return True

    def action_pay_batch(self):
        # This method is intended to be overridden by payroll_accounting to create moves
        # But we set state to paid here
        self._move_to_state("done")

    @api.depends("slip_ids.state", "slip_ids.line_ids.total")
    def _compute_bp_totals(self):
        for run in self:
            gross = net = deductions = employer_cost = 0.0
            for slip in run.slip_ids:
                gross += run._bp_get_line_total(slip, "GROSS")
                net += slip.total_net
                deductions += slip.total_deduction
                employer_cost += run._bp_get_employer_cost(slip)
            run.bp_total_gross = gross
            run.bp_total_net = net
            run.bp_total_deductions = deductions
            run.bp_total_employer_cost = employer_cost

    @staticmethod
    def _bp_get_line_total(slip, target_code):
        for line in slip.line_ids:
            # Check both rule code and category code
            line_code = (line.code or "").upper()
            cat_code = (line.category_id.code or "").upper() if line.category_id else ""
            if line_code == target_code or cat_code == target_code:
                return line.total
        return 0.0

    @staticmethod
    def _bp_get_employer_cost(slip):
        total = 0.0
        for line in slip.line_ids:
            code = (line.category_id.code or "").upper() if line.category_id else ""
            if code in ("COMP", "EMPCOST", "EMP"):
                total += abs(line.total)
        return total

    # -----------------------
    # Reporting helpers
    # -----------------------
    def get_batch_report_data(self):
        """Aggregate batch data for the PDF report."""
        self.ensure_one()

        def map_earning_label(code, name):
            c = (code or "").upper()
            n = (name or "").upper()
            if c.startswith("BASIC") or c == "BAS":
                return "Basic Salary"
            if c.startswith("ALW") or "ALLOW" in n:
                return "Allowances"
            if c.startswith("OT") or "OVERTIME" in n:
                return "Overtime"
            if c.startswith("BON") or "BONUS" in n or "COMM" in c:
                return "Bonus"
            return "Other Earnings"

        def map_deduction_label(code, name):
            c = (code or "").upper()
            n = (name or "").upper()
            if "PAYE" in c or "TAX" in c:
                return "PAYE"
            if "NSSF" in c:
                return "NSSF"
            if "NHIF" in c or "SHIF" in c:
                return "SHIF / NHIF"
            if "PENS" in c or "PENSION" in n:
                return "Pension"
            if "LOAN" in c or "ADV" in c or "ADVANCE" in n:
                return "Loans / Advances"
            return "Other Deductions"

        earnings_totals = defaultdict(float)
        deductions_totals = defaultdict(float)
        employer_totals = defaultdict(float)

        for slip in self.slip_ids:
            for line in slip.line_ids:
                cat_code = (line.category_id.code or "").upper() if line.category_id else ""
                code = (line.code or "").upper()
                name = line.name or ""
                if cat_code in ("EARN", "BASIC", "ALW"):
                    earnings_totals[map_earning_label(code, name)] += line.total
                elif cat_code in ("DED", "STAT", "STAT_DED", "TAX"):
                    deductions_totals[map_deduction_label(code, name)] += abs(line.total)
                elif cat_code in ("EMP", "COMP", "EMPCOST"):
                    employer_totals[code or name] += abs(line.total)

        def _dict_to_list(data_dict):
            return [
                {"label": k, "value": round(v, 2)}
                for k, v in sorted(data_dict.items(), key=lambda item: item[1], reverse=True)
                if v
            ]

        earnings_list = _dict_to_list(earnings_totals)
        deductions_list = _dict_to_list(deductions_totals)
        employer_list = _dict_to_list(employer_totals)

        slip_states = defaultdict(int)
        payslips_data = []
        for slip in self.slip_ids:
            slip_states[slip.state] += 1
            payslips_data.append({
                "name": slip.name,
                "employee": slip.employee_id.name,
                "net": slip.total_net,
            })

        return {
            "currency": self.company_id.currency_id,
            "payslips": payslips_data,
            "earnings": earnings_list,
            "deductions": deductions_list,
            "employer": employer_list,
            "summary": {
                "gross": self.bp_total_gross,
                "net": self.bp_total_net,
                "deductions": self.bp_total_deductions,
                "employer_cost": self.bp_total_employer_cost,
                "payslip_count": len(self.slip_ids),
                "employee_count": len(self.slip_ids.mapped("employee_id")),
            },
            "states": slip_states,
            "period": f"{self.date_start} - {self.date_end}",
            "report_generation_date": fields.Date.context_today(self),
        }
