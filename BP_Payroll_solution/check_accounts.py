
from odoo import api, SUPERUSER_ID
import sys

def check_accounts():
    import odoo
    from odoo.tools import config
    
    # Initialize Odoo
    config.parse_config(['-c', '/etc/odoo.conf'])
    registry = odoo.registry('default')
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        codes_to_check = [
            "510900", "221010", "221020", "221000", "221050", "221030", "221040", "222000"
        ]
        
        print("Checking accounts...")
        for code in codes_to_check:
            acc = env['account.account'].search([('code', '=', code)], limit=1)
            if acc:
                print(f"Account {code}: Found ({acc.name})")
            else:
                print(f"Account {code}: NOT FOUND")

if __name__ == "__main__":
    check_accounts()
