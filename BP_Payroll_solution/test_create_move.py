
from odoo import fields
import sys

def test_move(env):
    with open('/tmp/test_move_result.txt', 'w') as f:
        f.write("\n--- Testing Move Creation for Payslip 2 ---\n")
        
        payslip = env['hr.payslip'].browse(2)
        if not payslip.exists():
             payslip = env['hr.payslip'].search([], limit=1)
        
        if not payslip:
            f.write("No payslip found.\n")
            return

        f.write(f"Payslip: {payslip.name} (ID: {payslip.id})\n")
        
        # We need to mock the journal if it's missing, but let's assume it works or fails with UserError
        try:
            # We use a savepoint to rollback later
            with env.cr.savepoint():
                move = payslip._bp_create_move()
                f.write(f"Move Created: {move.name} (ID: {move.id})\n")
                
                total_debit = 0
                total_credit = 0
                f.write(f"{'Account':<30} | {'Debit':<15} | {'Credit':<15}\n")
                f.write("-" * 65 + "\n")
                for line in move.line_ids:
                    f.write(f"{line.account_id.name:<30} | {line.debit:<15} | {line.credit:<15}\n")
                    total_debit += line.debit
                    total_credit += line.credit
                
                f.write("-" * 65 + "\n")
                f.write(f"{'TOTAL':<30} | {total_debit:<15} | {total_credit:<15}\n")
                
                if abs(total_debit - total_credit) < 0.01:
                    f.write("SUCCESS: Move is balanced.\n")
                else:
                    f.write(f"FAILURE: Unbalanced ({total_debit - total_credit})\n")
                
                # Rollback is automatic because we are in a savepoint context? 
                # No, savepoint just allows rollback. We need to raise error to rollback or just let the script finish without commit?
                # Shell commits at exit.
                # So we must raise an exception to prevent commit.
                raise Exception("Rollback Test")
                
        except Exception as e:
            if str(e) == "Rollback Test":
                f.write("\nTest finished (Rolled back).\n")
            else:
                f.write(f"\nERROR: {e}\n")
                import traceback
                f.write(traceback.format_exc())

test_move(env)
