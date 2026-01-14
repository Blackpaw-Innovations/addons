
import sys
import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config

def check_registry():
    config.parse_config(['-c', '/etc/odoo.conf'])
    db_name = sys.argv[1]
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        models_to_check = [
            "hr.salary.rule.category",
            "hr.salary.rule",
            "hr.payroll.structure",
            "hr.payslip",
            "hr.payslip.line",
            "hr.payslip.run",
            "hr.payslip.worked_days",
            "hr.payslip.input",
            "bp.payroll.ke.config",
            "bp.payroll.tax.band",
            "bp.payroll.contribution",
            "bp.payroll.benefit.policy"
        ]
        
        print("Checking models in registry...")
        for model_name in models_to_check:
            if model_name in env:
                model = env[model_name]
                print(f"[OK] {model_name}: {model._name} (Table: {model._table})")
                # Check if it is _unknown
                if model._name == '_unknown':
                     print(f"[ERROR] {model_name} is _unknown!")
            else:
                print(f"[MISSING] {model_name} not found in registry!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_registry.py <db_name>")
        sys.exit(1)
    check_registry()
