from odoo import SUPERUSER_ID
from odoo.api import Environment


def post_init_hook(cr, registry):
    """Map Kenyan payroll accounts by code to salary rules/categories."""
    env = Environment(cr, SUPERUSER_ID, {})
    Account = env["account.account"].sudo()
    Rule = env["hr.salary.rule"].sudo()
    Category = env["hr.salary.rule.category"].sudo()

    code_to_account = {}

    def find_account(code):
        if code in code_to_account:
            return code_to_account[code]
        acc = Account.search([("code", "=", str(code))], limit=1)
        code_to_account[code] = acc
        return acc

    # Category defaults (optional)
    cat_map = {
        "EARN": {"debit": "510900", "credit": False},
        "DED": {"debit": False, "credit": False},
        "EMP": {"debit": "221050", "credit": False},
        "NET": {"debit": False, "credit": "222000"},
    }
    for cat_code, mapping in cat_map.items():
        cat = Category.search([("code", "=", cat_code)], limit=1)
        if not cat:
            continue
        if mapping.get("debit"):
            acc = find_account(mapping["debit"])
            if acc:
                cat.debit_account_id = acc.id
        if mapping.get("credit"):
            acc = find_account(mapping["credit"])
            if acc:
                cat.credit_account_id = acc.id

    # Rule-level mapping
    rule_map = {
        "BASIC": {"debit": "510900"},
        "GROSS": {"debit": "510900"},
        "TAXABLE": {"debit": "510900"},
        "NSSF_T1_EMP": {"credit": "221010"},
        "NSSF_T2_EMP": {"credit": "221010"},
        "NSSF_EMP": {"credit": "221010"},
        "SHIF": {"credit": "221020"},
        "PAYE": {"credit": "221000"},
        "INCOME_TAX": {"credit": "221000"},
        "AHL_EMP": {"credit": "221020"},
        "NSSF_T1_EMPR": {"debit": "221050", "credit": "221030"},
        "NSSF_T2_EMPR": {"debit": "221050", "credit": "221030"},
        "NSSF_EMPR": {"debit": "221050", "credit": "221030"},
        "AHL_EMPR": {"debit": "221050", "credit": "221040"},
        "NITA_EMPR": {"debit": "221050", "credit": "221040"},
        "NET": {"credit": "222000"},
    }
    for code, mapping in rule_map.items():
        rule = Rule.search([("code", "=", code)], limit=1)
        if not rule:
            continue
        if mapping.get("debit"):
            acc = find_account(mapping["debit"])
            if acc:
                rule.debit_account_id = acc.id
        if mapping.get("credit"):
            acc = find_account(mapping["credit"])
            if acc:
                rule.credit_account_id = acc.id
