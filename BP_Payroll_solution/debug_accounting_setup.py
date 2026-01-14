
from odoo import fields
import sys

def inspect(env):
    with open('/tmp/debug_payroll.txt', 'w') as f:
        f.write("\n--- Checking Rule Configuration ---\n")
        
        payslip = env['hr.payslip'].browse(2)
        if not payslip.exists():
             payslip = env['hr.payslip'].search([], limit=1)
        
        if payslip:
            f.write(f"Payslip: {payslip.name} (ID: {payslip.id})\n")
            f.write(f"{'Line Code':<15} | {'Rule ID':<10} | {'Debit Acc':<20} | {'Credit Acc':<20}\n")
            f.write("-" * 70 + "\n")
            for line in payslip.line_ids:
                rule = line.salary_rule_id
                if not rule:
                    f.write(f"{line.code:<15} | {'NO RULE':<10} | {'-':<20} | {'-':<20}\n")
                    continue
                
                debit = rule.debit_account_id.code if rule.debit_account_id else "False"
                credit = rule.credit_account_id.code if rule.credit_account_id else "False"
                f.write(f"{line.code:<15} | {rule.id:<10} | {debit:<20} | {credit:<20}\n")
                
                cat = rule.category_id
                if cat:
                    debit_cat = cat.debit_account_id.code if cat.debit_account_id else "False"
                    credit_cat = cat.credit_account_id.code if cat.credit_account_id else "False"
                    f.write(f"  [Cat: {cat.code}] | {'-':<10} | {debit_cat:<20} | {credit_cat:<20}\n")

inspect(env)
