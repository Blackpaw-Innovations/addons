# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BarberConsumableUsage(models.Model):
    _name = 'bp.barber.consumable.usage'
    _description = 'Barber Consumable Usage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Usage Reference',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    
    origin_type = fields.Selection([
        ('appointment', 'Appointment'),
        ('pos', 'POS Order')
    ], string='Origin Type', required=True, tracking=True)
    
    appointment_id = fields.Many2one(
        'bp.barber.appointment',
        string='Appointment',
        ondelete='cascade',
        help="Related appointment if origin is appointment"
    )
    
    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        ondelete='cascade',
        help="Related POS order if origin is POS"
    )
    
    barber_id = fields.Many2one(
        'bp.barber',
        string='Barber',
        # related='usage_id.barber_id',  # DISABLED to prevent _unknown object errors
        store=True
    )
    
    line_ids = fields.One2many(
        'bp.barber.consumable.usage.line',
        'usage_id',
        string='Usage Lines',
        copy=True
    )
    
    date = fields.Date(
        string='Date',
        # related='usage_id.date',  # DISABLED to prevent _unknown object errors
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], string='State', default='done', required=True, tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    # Computed fields
    total_lines = fields.Integer(
        string='Total Lines',
        compute='_compute_totals',
        store=True
    )
    
    total_products = fields.Integer(
        string='Total Products',
        compute='_compute_totals',
        store=True
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self._generate_usage_name(vals)
        return super().create(vals_list)
    
    def _generate_usage_name(self, vals):
        """Generate usage name based on origin"""
        if vals.get('origin_type') == 'appointment' and vals.get('appointment_id'):
            appointment = self.env['bp.barber.appointment'].browse(vals['appointment_id'])
            return f"Use: {', '.join(appointment.service_ids.mapped('name'))} ({appointment.name})"
        elif vals.get('origin_type') == 'pos' and vals.get('pos_order_id'):
            order = self.env['pos.order'].browse(vals['pos_order_id'])
            return f"Use: POS Order ({order.name})"
        else:
            return f"Use: {vals.get('origin_type', 'Unknown').title()}"
    
    # @api.depends('line_ids')
    def _compute_totals(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.total_lines = 0
            record.total_products = 0
    
    def action_confirm(self):
        """Confirm usage and process consumption"""
        for record in self.filtered(lambda r: r.state == 'draft'):
            record._process_consumption()
            record.state = 'done'
    
    def _process_consumption(self):
        """Process the actual consumption (stock moves or ledger entries)"""
        self.ensure_one()
        
        # Check if stock module is installed
        stock_installed = 'stock' in self.env.registry._init_modules
        
        if stock_installed and self.barber_id.stock_location_id:
            self._create_stock_moves()
        else:
            self._create_ledger_entries()
    
    def _create_stock_moves(self):
        """Create stock moves for consumption (if stock module installed)"""
        if not hasattr(self, '_get_consumption_location'):
            # Will be implemented in consumable_stock.py
            return
        
        consumption_location = self._get_consumption_location()
        
        for line in self.line_ids:
            if line.qty > 0:
                move_vals = {
                    'name': f"Consumption: {self.name}",
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                    'product_uom': line.uom_id.id,
                    'location_id': self.barber_id.stock_location_id.id,
                    'location_dest_id': consumption_location.id,
                    'company_id': self.company_id.id,
                    'state': 'done',
                    'date': self.date,
                }
                
                move = self.env['stock.move'].create(move_vals)
                move._action_done()
    
    def _create_ledger_entries(self):
        """Create ledger entries for consumption (fallback when no stock)"""
        for line in self.line_ids:
            if line.qty > 0:
                self.env['bp.barber.consumable.ledger'].create({
                    'barber_id': self.barber_id.id,
                    'product_id': line.product_id.id,
                    'move_type': 'consume',
                    'qty': line.qty,
                    'uom_id': line.uom_id.id,
                    'date': self.date,
                    'origin_usage_id': self.id,
                    'origin_note': self.name,
                    'company_id': self.company_id.id,
                })
    
    @classmethod
    def create_from_services(cls, env, barber, services, origin_type, origin_record):
        """Create usage record from a list of services"""
        # Aggregate BOM quantities by product
        product_totals = {}
        
        for service in services:
            bom_lines = env['bp.barber.service.bom'].search([
                ('service_id', '=', service.id),
                ('company_id', '=', env.company.id)
            ])
            
            for bom_line in bom_lines:
                product_key = (bom_line.product_id.id, bom_line.uom_id.id)
                if product_key not in product_totals:
                    product_totals[product_key] = {
                        'product_id': bom_line.product_id,
                        'uom_id': bom_line.uom_id,
                        'qty': 0.0
                    }
                product_totals[product_key]['qty'] += bom_line.qty
        
        if not product_totals:
            return None  # No consumables defined
        
        # Prepare usage values
        usage_vals = {
            'origin_type': origin_type,
            'barber_id': barber.id,
            'date': fields.Datetime.now(),
            'state': 'done',
            'company_id': env.company.id
        }
        
        if origin_type == 'appointment':
            usage_vals['appointment_id'] = origin_record.id
        elif origin_type == 'pos':
            usage_vals['pos_order_id'] = origin_record.id
        
        # Create usage lines
        line_vals = []
        for product_data in product_totals.values():
            line_vals.append((0, 0, {
                'product_id': product_data['product_id'].id,
                'qty': product_data['qty'],
                'uom_id': product_data['uom_id'].id,
            }))
        
        usage_vals['line_ids'] = line_vals
        
        # Create the usage record
        usage = env['bp.barber.consumable.usage'].create(usage_vals)
        
        # Process consumption immediately
        usage._process_consumption()
        
        return usage


class BarberConsumableUsageLine(models.Model):
    _name = 'bp.barber.consumable.usage.line'
    _description = 'Barber Consumable Usage Line'
    _order = 'usage_id, product_id'

    usage_id = fields.Many2one(
        'bp.barber.consumable.usage',
        string='Usage',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', 'in', ['consu', 'product'])]
    )
    
    qty = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure'
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    
    note = fields.Char(
        string='Note',
        help="Additional information about this consumption"
    )
    
    # Related fields for display
    product_name = fields.Char(
        string='Product Name',
        # related='product_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True,
        store=False
    )
    
    barber_id = fields.Many2one(
        'bp.barber.barber',
        # related='usage_id.barber_id',  # DISABLED to prevent _unknown object errors
        readonly=True,
        store=True
    )
    
    date = fields.Datetime(
        string='Date',
        # related='usage_id.date',  # DISABLED to prevent _unknown object errors
        readonly=True,
        store=True
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
    pass
    
    def _disabled_onchange_product_id(self):
        """DISABLED to prevent _unknown object errors"""
        # If there's any error accessing product data, clear UOM
        self.uom_id = False
    
    @api.constrains('qty')
    def _check_qty_positive(self):
        """Ensure quantity is positive"""
        for record in self:
            if record.qty <= 0:
                raise ValidationError(_('Quantity must be positive.'))
    
    def name_get(self):
        """Custom name for display"""
        result = []
        for record in self:
            name = f"{record.product_id.name}: {record.qty} {record.uom_id.name}"
            result.append((record.id, name))
        return result


class BarberConsumableLedger(models.Model):
    _name = 'bp.barber.consumable.ledger'
    _description = 'Barber Consumable Ledger (No Stock Fallback)'
    _order = 'date desc, id desc'

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
        index=True
    )
    
    move_type = fields.Selection([
        ('issue', 'Issue'),
        ('consume', 'Consume')
    ], string='Movement Type', required=True)
    
    qty = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure',
        help="Positive quantity (issue adds, consume subtracts from balance)"
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    
    date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now
    )
    
    origin_usage_id = fields.Many2one(
        'bp.barber.consumable.usage',
        string='Usage Origin',
        ondelete='set null',
        help="Usage record that created this consumption entry"
    )
    
    origin_note = fields.Char(
        string='Origin Note',
        help="Description of the operation that created this entry"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    # Related fields
    barber_name = fields.Char(
        string='Barber Name',
        # related='barber_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True,
        store=False
    )
    
    product_name = fields.Char(
        string='Product Name',
        # related='product_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True,
        store=False
    )
    
    @api.constrains('qty')
    def _check_qty_positive(self):
        """Ensure quantity is positive"""
        for record in self:
            if record.qty <= 0:
                raise ValidationError(_('Quantity must be positive.'))
    
    @api.model
    def get_balance(self, barber_id, product_id, date=None):
        """Get current balance for barber+product combination"""
        domain = [
            ('barber_id', '=', barber_id),
            ('product_id', '=', product_id),
        ]
        
        if date:
            domain.append(('date', '<=', date))
        
        entries = self.search(domain)
        
        balance = 0.0
        for entry in entries:
            if entry.move_type == 'issue':
                balance += entry.qty
            else:  # consume
                balance -= entry.qty
        
        return balance
    
    def name_get(self):
        """Custom name for display"""
        result = []
        for record in self:
            sign = '+' if record.move_type == 'issue' else '-'
            name = f"{record.barber_name}: {sign}{record.qty} {record.product_name}"
            result.append((record.id, name))
        return result