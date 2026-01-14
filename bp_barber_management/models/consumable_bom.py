# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarberServiceBOM(models.Model):
    _name = 'bp.barber.service.bom'
    _description = 'Barber Service Bill of Materials'
    _order = 'service_id, product_id'

    service_id = fields.Many2one(
        'bp.barber.service',
        string='Service',
        required=True,
        index=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Consumable Product',
        required=True,
        domain=[('type', 'in', ['consu', 'product'])],
        help="Consumable or stockable product used during this service"
    )
    
    qty = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
        help="Quantity consumed per service execution"
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        # related='product_id.uom_id',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    note = fields.Char(
        string='Note',
        help="Additional information about this consumable"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    
    # Related fields for convenience
    product_name = fields.Char(
        string='Product Name',
        # related='product_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        # related='product_id.uom_id',  # DISABLED to prevent _unknown object errors
        readonly=True,
        store=False
    )
    
    # Temporarily disabled to fix _unknown object error
    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     """Set default UOM from product"""
    #     try:
    #         if self.product_id and self.product_id.uom_id:
    #             self.uom_id = self.product_id.uom_id
    #         else:
    #             self.uom_id = False
    #     except:
    #         # If there's any error accessing product data, clear UOM
    pass
    
    def _disabled_onchange_product_id(self):
        """DISABLED to prevent _unknown object errors"""
        self.uom_id = False
    
    @api.constrains('qty')
    def _check_qty_positive(self):
        """Ensure quantity is positive"""
        for record in self:
            if record.qty <= 0:
                raise ValidationError(_('Quantity must be positive.'))
    
    _sql_constraints = [
        ('unique_service_product_company',
         'UNIQUE(service_id, product_id, company_id)',
         'Product can only be added once per service in the same company.')
    ]
    
    def name_get(self):
        """Custom name for display"""
        result = []
        for record in self:
            name = f"{record.service_id.name} - {record.product_id.name} ({record.qty} {record.uom_id.name})"
            result.append((record.id, name))
        return result


class BarberBarberSupply(models.Model):
    _name = 'bp.barber.barber.supply'
    _description = 'Barber Supply Profile'
    _order = 'barber_id, product_id'

    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Barber',
        required=True,
        index=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', 'in', ['consu', 'product'])],
        help="Consumable product to track for this barber"
    )
    
    min_qty = fields.Float(
        string='Minimum Quantity',
        default=0.0,
        digits='Product Unit of Measure',
        help="Alert when on-hand quantity falls below this level"
    )
    
    target_qty = fields.Float(
        string='Target Quantity',
        default=0.0,
        digits='Product Unit of Measure',
        help="Suggested replenishment level"
    )
    
    avg_daily_usage = fields.Float(
        string='Avg Daily Usage',
        compute='_compute_avg_daily_usage',
        store=False,
        digits='Product Unit of Measure',
        help="Average daily consumption over last 30 days"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    
    # Related fields
    product_uom_id = fields.Many2one(
        'uom.uom',
        # related='product_id.uom_id',  # DISABLED to prevent _unknown object errors
        readonly=True,
        store=False
    )
    
    barber_name = fields.Char(
        string='Barber Name',
        # related='barber_id.name',  # DISABLED to prevent _unknown object errors
        store=True
    )
    
    def _compute_avg_daily_usage(self):
        """Compute average daily usage from last 30 days"""
        from datetime import datetime, timedelta
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        for record in self:
            # Find usage lines for this barber+product in last 30 days
            usage_lines = self.env['bp.barber.consumable.usage.line'].search([
                ('usage_id.barber_id', '=', record.barber_id.id),
                ('product_id', '=', record.product_id.id),
                ('usage_id.date', '>=', thirty_days_ago),
                ('usage_id.state', '=', 'done')
            ])
            
            total_consumed = sum(line.qty for line in usage_lines)
            record.avg_daily_usage = total_consumed / 30.0
    
    @api.constrains('min_qty', 'target_qty')
    def _check_quantities(self):
        """Validate quantity constraints"""
        for record in self:
            if record.min_qty < 0:
                raise ValidationError(_('Minimum quantity cannot be negative.'))
            if record.target_qty < 0:
                raise ValidationError(_('Target quantity cannot be negative.'))
            if record.target_qty > 0 and record.min_qty > record.target_qty:
                raise ValidationError(_('Minimum quantity cannot be greater than target quantity.'))
    
    _sql_constraints = [
        ('unique_barber_product_company',
         'UNIQUE(barber_id, product_id, company_id)',
         'Product can only be configured once per barber in the same company.')
    ]
    
    def name_get(self):
        """Custom name for display"""
        result = []
        for record in self:
            name = f"{record.barber_id.name} - {record.product_id.name}"
            result.append((record.id, name))
        return result
    
    def get_current_balance(self):
        """Get current balance for this barber+product"""
        self.ensure_one()
        
        # Check if stock module is installed
        stock_installed = 'stock' in self.env.registry._init_modules
        
        if stock_installed and self.barber_id.stock_location_id:
            # Use stock quants
            quants = self.env['stock.quant'].search([
                ('location_id', '=', self.barber_id.stock_location_id.id),
                ('product_id', '=', self.product_id.id),
            ])
            return sum(quant.quantity for quant in quants)
        else:
            # Use ledger system
            ledger_entries = self.env['bp.barber.consumable.ledger'].search([
                ('barber_id', '=', self.barber_id.id),
                ('product_id', '=', self.product_id.id),
            ])
            
            balance = 0.0
            for entry in ledger_entries:
                if entry.move_type == 'issue':
                    balance += entry.qty
                else:  # consume
                    balance -= entry.qty
            
            return balance
    
    def get_days_to_empty(self):
        """Calculate days until stock runs out based on current usage"""
        self.ensure_one()
        
        current_balance = self.get_current_balance()
        if current_balance <= 0:
            return 0.0
        
        if self.avg_daily_usage <= 0:
            return 999.0  # Effectively infinite
        
        return current_balance / self.avg_daily_usage