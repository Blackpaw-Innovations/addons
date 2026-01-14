from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrSalaryRuleCategory(models.Model):
    _inherit = "hr.salary.rule.category"

    debit_account_id = fields.Many2one("account.account", string="Debit Account")
    credit_account_id = fields.Many2one("account.account", string="Credit Account")


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    debit_account_id = fields.Many2one("account.account", string="Debit Account")
    credit_account_id = fields.Many2one("account.account", string="Credit Account")


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    move_id = fields.Many2one("account.move", string="Payroll Move", readonly=True, copy=False)

    def _bp_get_partner(self):
        self.ensure_one()
        # address_home_id is missing in this environment.
        # We prioritize the user partner, then work contact, then work address.
        return (
            self.employee_id.user_partner_id 
            or self.employee_id.work_contact_id 
            or self.employee_id.address_id
        )

    def action_create_move(self):
        for slip in self:
            slip._bp_create_move()
        return True

    def action_open_journal_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "bp.payroll.journal.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_payslip_ids": self.ids,
                "default_company_id": self.company_id.id if len(self.mapped("company_id")) == 1 else False,
            },
        }

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            "name": _("Journal Entry"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.move_id.id,
        }

    def _bp_get_journal(self, journal=None):
        self.ensure_one()
        if journal:
            return journal
        # Prefer KE config journal, fallback to company payroll journal
        ke_config = getattr(self, "_bp_ke_get_config", lambda: False)()
        if ke_config and ke_config.payroll_journal_id:
            return ke_config.payroll_journal_id
        if self.company_id.payroll_journal_id:
            return self.company_id.payroll_journal_id
        raise UserError(_("Please configure a payroll journal on company or Kenya payroll settings."))

    def _bp_create_move(self, custom_journal=None):
        self.ensure_one()
        if self.move_id:
            return self.move_id
        journal = self._bp_get_journal(custom_journal)
        ke_config = getattr(self, "_bp_ke_get_config", lambda: False)()
        
        lines = []
        account_cache = {}
        
        # Default Accounts from Config
        acc_basic = ke_config.account_basic_salary_id if ke_config else False
        acc_net = ke_config.account_net_pay_payable_id if ke_config else False
        acc_paye = ke_config.account_paye_payable_id if ke_config else False
        acc_nssf_pay = ke_config.account_nssf_payable_id if ke_config else False
        acc_shif_pay = ke_config.account_shif_payable_id if ke_config else False
        acc_ahl_pay = ke_config.account_housing_levy_payable_id if ke_config else False
        acc_nita_pay = ke_config.account_nita_payable_id if ke_config else False
        
        acc_nssf_exp = ke_config.account_nssf_expense_id if ke_config else False
        acc_ahl_exp = ke_config.account_housing_levy_expense_id if ke_config else False
        acc_nita_exp = ke_config.account_nita_expense_id if ke_config else False

        rule_account_map = {
            # rule_code: (debit_account, credit_account)
            "BASIC": (acc_basic, False),
            "GROSS": (False, False),
            "TAXABLE": (False, False),
            "NSSF_T1_EMP": (False, False),
            "NSSF_T2_EMP": (False, False),
            "NSSF_EMP": (False, acc_nssf_pay),
            "SHIF": (False, acc_shif_pay),
            "PAYE": (False, acc_paye),
            "INCOME_TAX": (False, False),
            "AHL_EMP": (False, acc_ahl_pay),
            "NSSF_T1_EMPR": (False, False),
            "NSSF_T2_EMPR": (False, False),
            "NSSF_EMPR": (acc_nssf_exp, acc_nssf_pay),
            "AHL_EMPR": (acc_ahl_exp, acc_ahl_pay),
            "NITA_EMPR": (acc_nita_exp, acc_nita_pay),
            "NET": (False, acc_net),
            
            # Missing Deductions - Ignored because they don't reduce Net Pay in this setup
            "PENSION": (False, False),
            "INSURANCE": (False, False),

            # Ignore Calculation/Summary Rules
            "TOTAL_EMP": (False, False),
            "TOTAL_DED": (False, False),
            "PAYE_GROSS": (False, False),
            "SEC_EARN": (False, False),
            "SEC_STAT_DED": (False, False),
            "SEC_TAX_BASE": (False, False),
            "SEC_PAYE_CALC": (False, False),
            "SEC_RELIEFS": (False, False),
            "SEC_TOT_DED": (False, False),
            "SEC_EMP": (False, False),
            "SEC_NET": (False, False),
            "PAYE_BAND_1": (False, False),
            "PAYE_BAND_2": (False, False),
            "PAYE_BAND_3": (False, False),
            "PAYE_BAND_4": (False, False),
            "PAYE_BAND_5": (False, False),
            "RELIEF_PERSONAL": (False, False),
            "RELIEF_INSURANCE": (False, False),
            "RELIEF_ADDITIONAL": (False, False),
            "REPORT_PAYE": (False, False),
            "REPORT_AHL": (False, False),
            "REPORT_NSSF": (False, False),
            "REPORT_SHIF": (False, False),
        }
        category_account_map = {
            "EARN": (acc_basic, False),
            "DED": (False, False),
            "EMP": (acc_nssf_exp, False),
            "NET": (False, acc_net),
        }

        def get_account_by_code(code):
            if not code:
                return False
            if code in account_cache:
                return account_cache[code]
            acc = (
                self.env["account.account"]
                .sudo()
                .search([("code", "=", str(code)), ("company_id", "=", self.company_id.id)], limit=1)
            )
            account_cache[code] = acc
            return acc

        for line in self.line_ids:
            category = line.category_id
            rule = line.salary_rule_id
            debit_account = False
            credit_account = False
            rule_handled = False

            # 1. Explicit Rule Configuration (DB)
            if rule and (rule.debit_account_id or rule.credit_account_id):
                debit_account = rule.debit_account_id
                credit_account = rule.credit_account_id
                rule_handled = True

            # Use line code if rule is missing
            rule_code = rule.code if rule else line.code

            # 2. Rule Map (Dynamic from Config)
            if not rule_handled and rule_code in rule_account_map:
                debit_account, credit_account = rule_account_map[rule_code]
                
                # Fallback to hardcoded if config is missing but we have codes (Legacy support)
                # (Removed legacy hardcoded fallback to force config usage or DB usage)
                
                rule_handled = True

            # 3. Category Fallback (DB & Map)
            if not rule_handled:
                # Check Category DB
                if category.debit_account_id or category.credit_account_id:
                    debit_account = category.debit_account_id
                    credit_account = category.credit_account_id
                # Check Category Map
                elif category.code in category_account_map:
                    debit_account, credit_account = category_account_map[category.code]

            if not (debit_account or credit_account):
                continue
            amount = line.total
            partner = self._bp_get_partner()
            if debit_account:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "name": line.name,
                            "account_id": debit_account.id,
                            "debit": max(amount, 0),
                            "credit": max(-amount, 0),
                            "partner_id": partner.id if partner else False,
                        },
                    )
                )
            if credit_account:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "name": line.name,
                            "account_id": credit_account.id,
                            "credit": max(amount, 0),
                            "debit": max(-amount, 0),
                            "partner_id": partner.id if partner else False,
                        },
                    )
                )
        if not lines:
            raise UserError(_("No account mappings set. Please configure accounts in Kenya Payroll Settings."))

        # Ensure the move is balanced; add a rounding line if needed.
        debit_total = sum(l[2]["debit"] for l in lines)
        credit_total = sum(l[2]["credit"] for l in lines)
        diff = round(debit_total - credit_total, 2)
        if diff:
            if not journal.default_account_id:
                raise UserError(
                    _("The payroll journal has no default account to post rounding adjustments. Please set one.")
                )
            lines.append(
                (
                    0,
                    0,
                    {
                        "name": _("Payroll Rounding Adjustment"),
                        "account_id": journal.default_account_id.id,
                        "debit": 0 if diff > 0 else abs(diff),
                        "credit": diff if diff > 0 else 0,
                        "partner_id": partner.id if partner else False,
                    },
                )
            )
        move_vals = {
            "date": self.date_to or fields.Date.context_today(self),
            "ref": self.name,
            "journal_id": journal.id,
            "line_ids": lines,
            "company_id": self.company_id.id,
        }
        move = self.env["account.move"].sudo().create(move_vals)
        move._post()
        self.move_id = move.id
        return move


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    move_ids = fields.Many2many("account.move", string="Payroll Moves", readonly=True, copy=False)

    def action_create_moves(self):
        moves = self.env["account.move"]
        for run in self:
            for slip in run.slip_ids:
                moves |= slip._bp_create_move()
            run.move_ids = [(6, 0, moves.ids)]
        return True

    def action_view_moves(self):
        self.ensure_one()
        return {
            "name": _("Journal Entries"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.move_ids.ids)],
            "context": {"create": False},
        }

    def action_pay_batch(self):
        self.action_create_moves()
        return self.action_open_pay_wizard()
