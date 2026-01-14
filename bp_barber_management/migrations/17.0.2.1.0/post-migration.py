def migrate(cr, version):
    """Add missing enable_barber_mode column to pos.config"""
    # Add the missing column with default False to avoid POS errors
    cr.execute("""
        ALTER TABLE pos_config 
        ADD COLUMN IF NOT EXISTS enable_barber_mode BOOLEAN DEFAULT FALSE;
    """)
    
    # Update existing records to have enable_barber_mode = False by default
    cr.execute("""
        UPDATE pos_config 
        SET enable_barber_mode = FALSE 
        WHERE enable_barber_mode IS NULL;
    """)