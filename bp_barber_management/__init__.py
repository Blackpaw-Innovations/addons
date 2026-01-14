# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizard


def post_init_hook(env):
    """Create database indexes for performance optimization and fix data issues"""
    from odoo import tools
    
    # Safety check - drop any temporary views
    tools.drop_view_if_exists(env.cr, 'tmp')
    
    # Fix data issues
    try:
        if 'bp.barber.chair' in env:
            chair_model = env['bp.barber.chair']
            chair_model._fix_invalid_references()
            print("✅ Barber Management: Fixed chair references")
        if 'bp.barber.barber' in env:
            barber_model = env['bp.barber.barber']
            barber_model._fix_invalid_references()
            print("✅ Barber Management: Fixed barber references")
    except Exception as e:
        print(f"⚠️  Barber Management: Data fix warning: {e}")
    
    # Create performance indexes for barber management
    indexes_sql = """
    -- Appointment indexes for frequent queries
    CREATE INDEX IF NOT EXISTS idx_bp_appt_company_state_start 
        ON bp_barber_appointment (company_id, state, start_datetime);
    
    CREATE INDEX IF NOT EXISTS idx_bp_appt_barber_start 
        ON bp_barber_appointment (barber_id, start_datetime);
    
    CREATE INDEX IF NOT EXISTS idx_bp_appt_partner_state 
        ON bp_barber_appointment (partner_id, state);
    
    -- POS integration indexes
    CREATE INDEX IF NOT EXISTS idx_pos_order_line_barber 
        ON pos_order_line (barber_id);
    
    -- Consumable usage indexes
    CREATE INDEX IF NOT EXISTS idx_bp_cons_usage_barber_date 
        ON bp_barber_consumable_usage (barber_id, date);
    
    CREATE INDEX IF NOT EXISTS idx_bp_cons_usage_line_product 
        ON bp_barber_consumable_usage_line (product_id);
    
    -- Package wallet indexes
    CREATE INDEX IF NOT EXISTS idx_bp_wallet_expiry_company 
        ON bp_barber_package_wallet (company_id, expiry_date);
    
    CREATE INDEX IF NOT EXISTS idx_bp_wallet_partner_active 
        ON bp_barber_package_wallet (partner_id, active);
    
    -- Commission indexes
    CREATE INDEX IF NOT EXISTS idx_bp_commission_line_barber_date 
        ON bp_barber_commission_line (barber_id, date);
    """
    
    try:
        env.cr.execute(indexes_sql)
        env.cr.commit()
        print("✅ Barber Management: Performance indexes created successfully")
    except Exception as e:
        # Don't fail the installation if indexes can't be created
        print(f"⚠️  Barber Management: Index creation warning: {e}")
        env.cr.rollback()