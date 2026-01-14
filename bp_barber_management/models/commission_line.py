# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarberCommissionLine(models.Model):
    _name = 'bp.barber.commission.line'
    _description = 'Barber Commission Line'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Description',
        compute='_compute_name',
        store=True
    )
    
    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Barber',
        required=True,
        index=True
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        index=True
    )
    
    origin_type = fields.Selection([
        ('appointment', 'Appointment'),
        ('pos', 'POS Order')
    ], string='Origin Type', required=True)
    
    # Appointment origin fields
    appointment_id = fields.Many2one(
        'bp.barber.appointment',
        string='Appointment',
        ondelete='cascade'
    )
    
    # POS origin fields
    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        ondelete='cascade'
    )
    
    pos_order_line_id = fields.Many2one(
        'pos.order.line',
        string='POS Order Line',
        ondelete='cascade'
    )
    
    # Service/Product references
    service_id = fields.Many2one(
        'bp.service',
        string='Service'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    
    qty = fields.Float(
        string='Quantity',
        default=1.0,
        digits='Product Unit of Measure'
    )
    
    amount_base = fields.Monetary(
        string='Base Amount',
        required=True,
        help="Base amount for commission computation"
    )
    
    percent = fields.Float(
        string='Commission %',
        digits=(5, 2),
        help="Commission percentage applied"
    )
    
    amount_commission = fields.Monetary(
        string='Commission Amount',
        compute='_compute_commission_amount',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('statement', 'In Statement'),
        ('paid', 'Paid')
    ], string='State', default='draft', index=True)
    
    statement_id = fields.Many2one(
        'bp.barber.commission.statement',
        string='Statement',
        ondelete='set null'
    )

    _sql_constraints = [
        ('unique_pos_order_line', 
         'UNIQUE(pos_order_line_id)', 
         'Commission line already exists for this POS order line'),
        ('unique_appointment_service', 
         'UNIQUE(appointment_id, barber_id, service_id)', 
         'Commission line already exists for this appointment service'),
        ('check_origin_consistency', 
         'CHECK((origin_type = \'pos\' AND pos_order_line_id IS NOT NULL) OR (origin_type = \'appointment\' AND appointment_id IS NOT NULL))',
         'Origin fields must match origin type'),
        ('check_positive_amounts', 
         'CHECK(amount_base >= 0 AND percent >= 0)',
         'Amounts and percentages must be positive')
    ]

    # @api.depends('amount_base', 'percent', 'currency_id')
    def _compute_commission_amount(self):
        """DISABLED to prevent _unknown object errors"""
        for line in self:
            line.amount_commission = 0.0

    # @api.depends('origin_type', 'appointment_id', 'pos_order_id', 'pos_order_line_id', 'service_id', 'product_id')
    def _compute_name(self):
        """DISABLED to prevent _unknown object errors"""
        for line in self:
            line.name = "Commission Line"

    @api.model
    def create_from_pos_line(self, pos_order_line, barber):
        """Create commission line from POS order line"""
        
        # Check if line already exists (idempotency)
        existing = self.search([('pos_order_line_id', '=', pos_order_line.id)])
        if existing:
            return existing
        
        # Determine if service or retail
        product = pos_order_line.product_id
        is_service = product.type == 'service'
        
        # Find applicable service if it's a service product
        service = None
        if is_service:
            service = self.env['bp.service'].search([
                ('name', '=', product.name)
            ], limit=1)
        
        # Get commission percentages
        percent_service, percent_retail = self.env['bp.barber.commission.rule'].get_commission_percentages(
            service=service,
            product=product,
            company_id=pos_order_line.order_id.company_id.id
        )
        
        # Use appropriate percentage
        percent = percent_service if is_service else percent_retail
        
        if percent <= 0:
            return self.browse()  # No commission rule applies
        
        # Create commission line
        vals = {
            'barber_id': barber.id,
            'date': pos_order_line.order_id.date_order.date(),
            'origin_type': 'pos',
            'pos_order_id': pos_order_line.order_id.id,
            'pos_order_line_id': pos_order_line.id,
            'product_id': product.id,
            'qty': pos_order_line.qty,
            'amount_base': pos_order_line.price_subtotal_incl,
            'percent': percent,
            'currency_id': pos_order_line.order_id.currency_id.id,
            'company_id': pos_order_line.order_id.company_id.id,
        }
        
        if service:
            vals['service_id'] = service.id
        
        return self.create(vals)

    @api.model
    def create_from_appointment(self, appointment):
        """Create commission lines from appointment services"""
        
        # Check if appointment has linked paid POS order (avoid double-counting)
        paid_pos_order = self.env['pos.order'].search([
            ('appointment_id', '=', appointment.id),
            ('state', 'in', ['paid', 'invoiced'])
        ], limit=1)
        
        if paid_pos_order:
            return self.browse()  # Skip if POS order exists
        
        lines_created = self.browse()
        
        # Get total for proration calculation
        subtotal = appointment.price_subtotal or 0.0
        total = appointment.price_total or 0.0
        
        for service in appointment.service_ids:
            # Check if line already exists
            existing = self.search([
                ('appointment_id', '=', appointment.id),
                ('barber_id', '=', appointment.barber_id.id),
                ('service_id', '=', service.id)
            ])
            if existing:
                continue
            
            # Calculate prorated base amount (handles appointment-level discount)
            if subtotal > 0:
                proration_factor = total / subtotal
                base_amount = service.list_price * proration_factor
            else:
                base_amount = 0.0
            
            # Get commission percentage for service
            percent_service, _ = self.env['bp.barber.commission.rule'].get_commission_percentages(
                service=service,
                company_id=appointment.company_id.id
            )
            
            if percent_service <= 0:
                continue  # No commission rule applies
            
            # Create commission line
            vals = {
                'barber_id': appointment.barber_id.id,
                'date': appointment.start_datetime.date() if appointment.start_datetime else fields.Date.today(),
                'origin_type': 'appointment',
                'appointment_id': appointment.id,
                'service_id': service.id,
                'qty': 1.0,
                'amount_base': base_amount,
                'percent': percent_service,
                'currency_id': appointment.currency_id.id or self.env.company.currency_id.id,
                'company_id': appointment.company_id.id,
            }
            
            line = self.create(vals)
            lines_created |= line
        
        return lines_created