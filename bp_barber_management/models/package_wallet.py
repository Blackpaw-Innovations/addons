# -*- coding: utf-8 -*-

import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BarberPackageWallet(models.Model):
    _name = 'bp.barber.package.wallet'
    _description = 'Barber Package Wallet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'purchase_date desc, id desc'

    name = fields.Char(
        string='Wallet Name',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True,
        tracking=True
    )
    
    package_id = fields.Many2one(
        'bp.barber.package',
        string='Package',
        required=True,
        tracking=True
    )
    
    purchase_pos_order_id = fields.Many2one(
        'pos.order',
        string='Purchase POS Order',
        ondelete='set null',
        help="Original POS order that created this wallet"
    )
    
    purchase_date = fields.Date(
        string='Purchase Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        compute='_compute_expiry_date',
        store=True,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        # related='company_id.currency_id',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=True
    )
    
    # Balance fields
    balance_amount = fields.Monetary(
        string='Value Balance',
        currency_field='currency_id',
        compute='_compute_balances',
        store=True,
        help="Remaining credit amount for value packages"
    )
    
    balance_json = fields.Text(
        string='Service Units Balance',
        help="JSON storage of remaining units per service"
    )
    
    balance_summary = fields.Char(
        string='Balance Summary',
        compute='_compute_balance_summary',
        help="Human-readable balance summary"
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # Related fields
    package_type = fields.Selection([
        ('qty', 'Quantity-based'),
        ('bundle', 'Bundle'),
        ('value', 'Value-based (Credit)')
    ], string='Package Type',
        # related='package_id.package_type',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=True
    )
    
    # Ledger lines
    wallet_line_ids = fields.One2many(
        'bp.barber.package.wallet.line',
        'wallet_id',
        string='Wallet Movements'
    )
    
    # Computed fields
    redemption_count = fields.Integer(
        string='Redemptions',
        compute='_compute_redemption_count'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self._generate_wallet_name(vals)
        return super().create(vals_list)
    
    def _generate_wallet_name(self, vals):
        """Generate wallet name from package and partner"""
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        package = self.env['bp.barber.package'].browse(vals.get('package_id'))
        date_str = fields.Date.to_string(vals.get('purchase_date', fields.Date.today()))
        return f"{partner.name} - {package.name} - {date_str}"
    
    # @api.depends('package_id.duration_days', 'purchase_date')
    def _compute_expiry_date(self):
        """DISABLED to prevent _unknown object errors"""
        for wallet in self:
            wallet.expiry_date = False
    
    # @api.depends('wallet_line_ids.amount', 'wallet_line_ids.qty', 'wallet_line_ids.service_id', 'wallet_line_ids.move_type')
    def _compute_balances(self):
        """DISABLED to prevent _unknown object errors"""
        for wallet in self:
            wallet.balance_amount = 0.0
            wallet.balance_json = '{}'
    
    def _compute_balance_summary(self):
        for wallet in self:
            if wallet.package_type == 'value':
                wallet.balance_summary = f"{wallet.currency_id.symbol}{wallet.balance_amount:,.2f}"
            else:
                if wallet.balance_json:
                    try:
                        balance_dict = json.loads(wallet.balance_json)
                        summary_parts = []
                        for service_name, units in balance_dict.items():
                            if units > 0:
                                summary_parts.append(f"{service_name}: {units}")
                        wallet.balance_summary = ", ".join(summary_parts) if summary_parts else "No units remaining"
                    except (json.JSONDecodeError, TypeError):
                        wallet.balance_summary = "Error reading balance"
                else:
                    wallet.balance_summary = "No units"
    
    def _compute_redemption_count(self):
        for wallet in self:
            wallet.redemption_count = self.env['bp.barber.package.redemption'].search_count([
                ('wallet_id', '=', wallet.id)
            ])
    
    @classmethod
    def credit_from_sale(cls, env, pos_order_line):
        """Create wallet from POS order line selling a package"""
        if not pos_order_line.order_id.partner_id:
            raise UserError(_('Package purchase requires a customer to be selected.'))
        
        # Find the package by product
        package = env['bp.barber.package'].search([
            ('pos_product_id', '=', pos_order_line.product_id.id),
            ('company_id', '=', pos_order_line.order_id.company_id.id)
        ], limit=1)
        
        if not package:
            return None
        
        # Create wallet
        wallet_vals = {
            'partner_id': pos_order_line.order_id.partner_id.id,
            'package_id': package.id,
            'purchase_pos_order_id': pos_order_line.order_id.id,
            'purchase_date': pos_order_line.order_id.date_order.date(),
            'company_id': pos_order_line.order_id.company_id.id,
        }
        
        wallet = env['bp.barber.package.wallet'].create(wallet_vals)
        
        # Create credit movements
        if package.package_type == 'value':
            # Credit the line amount
            wallet._create_wallet_line(
                move_type='credit',
                amount=pos_order_line.price_subtotal_incl,
                pos_order_line_id=pos_order_line.id,
                note=f"Purchase of {package.name}"
            )
        else:
            # Credit service units
            for line in package.line_ids:
                wallet._create_wallet_line(
                    move_type='credit',
                    service_id=line.service_id.id,
                    qty=line.qty,
                    pos_order_line_id=pos_order_line.id,
                    note=f"Purchase of {package.name}"
                )
        
        return wallet
    
    def _create_wallet_line(self, move_type, amount=0.0, qty=0.0, service_id=None, 
                           pos_order_line_id=None, appointment_id=None, note=None):
        """Create a wallet movement line"""
        vals = {
            'wallet_id': self.id,
            'move_type': move_type,
            'date': fields.Datetime.now(),
            'amount': amount,
            'qty': qty,
            'service_id': service_id,
            'pos_order_line_id': pos_order_line_id,
            'appointment_id': appointment_id,
            'note': note or '',
        }
        return self.env['bp.barber.package.wallet.line'].create(vals)
    
    def get_available_units(self, service):
        """Get available units for a specific service"""
        if self.package_type == 'value':
            return 0  # Value packages don't have service units
        
        if self.balance_json:
            try:
                balance_dict = json.loads(self.balance_json)
                return balance_dict.get(service.name, 0.0)
            except (json.JSONDecodeError, TypeError):
                return 0.0
        return 0.0
    
    def has_expired(self):
        """Check if wallet has expired"""
        if not self.expiry_date:
            return False
        return fields.Date.today() > self.expiry_date
    
    def consume_units(self, service, qty, source_record=None, note=None):
        """Consume units from wallet and create debit line"""
        if self.has_expired():
            raise UserError(_('This wallet has expired and cannot be used.'))
        
        available_units = self.get_available_units(service)
        if available_units < qty:
            raise UserError(_('Insufficient units available. Available: %s, Requested: %s') % (available_units, qty))
        
        # Create debit line
        line_vals = {
            'move_type': 'debit',
            'service_id': service.id,
            'qty': qty,
            'note': note or f"Consumed {qty} {service.name}"
        }
        
        if hasattr(source_record, '_name'):
            if source_record._name == 'pos.order.line':
                line_vals['pos_order_line_id'] = source_record.id
            elif source_record._name == 'bp.barber.appointment':
                line_vals['appointment_id'] = source_record.id
        
        return self._create_wallet_line(**line_vals)
    
    def consume_value(self, amount, source_record=None, note=None):
        """Consume value from wallet and create debit line"""
        if self.has_expired():
            raise UserError(_('This wallet has expired and cannot be used.'))
        
        if self.balance_amount < amount:
            raise UserError(_('Insufficient balance. Available: %s, Requested: %s') % (self.balance_amount, amount))
        
        # Create debit line
        line_vals = {
            'move_type': 'debit',
            'amount': amount,
            'note': note or f"Consumed {self.currency_id.symbol}{amount}"
        }
        
        if hasattr(source_record, '_name'):
            if source_record._name == 'pos.order.line':
                line_vals['pos_order_line_id'] = source_record.id
            elif source_record._name == 'bp.barber.appointment':
                line_vals['appointment_id'] = source_record.id
        
        return self._create_wallet_line(**line_vals)
    
    def action_view_redemptions(self):
        """Smart button action to view redemptions"""
        return {
            'name': _('Package Redemptions'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.package.redemption',
            'view_mode': 'tree,form',
            'domain': [('wallet_id', '=', self.id)],
            'context': {'default_wallet_id': self.id}
        }
    
    def action_view_purchase_order(self):
        """Smart button action to view purchase order"""
        if self.purchase_pos_order_id:
            return {
                'name': _('Purchase Order'),
                'type': 'ir.actions.act_window',
                'res_model': 'pos.order',
                'view_mode': 'form',
                'res_id': self.purchase_pos_order_id.id,
            }


class BarberPackageWalletLine(models.Model):
    _name = 'bp.barber.package.wallet.line'
    _description = 'Barber Package Wallet Movement Line'
    _order = 'date desc, id desc'

    wallet_id = fields.Many2one(
        'bp.barber.package.wallet',
        string='Wallet',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    move_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit', 'Debit')
    ], string='Movement Type', required=True)
    
    date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now
    )
    
    service_id = fields.Many2one(
        'bp.barber.service',
        string='Service',
        help="Service for quantity-based movements"
    )
    
    qty = fields.Float(
        string='Quantity',
        default=0.0,
        digits='Product Unit of Measure'
    )
    
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        default=0.0,
        help="Amount for value-based movements"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        # related='wallet_id.currency_id',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=True
    )
    
    pos_order_line_id = fields.Many2one(
        'pos.order.line',
        string='POS Order Line',
        ondelete='set null'
    )
    
    appointment_id = fields.Many2one(
        'bp.barber.appointment',
        string='Appointment',
        ondelete='set null'
    )
    
    note = fields.Char(
        string='Note',
        help="Description of the movement"
    )
    
    # Related fields for display
    partner_id = fields.Many2one(
        'res.partner',
        # related='wallet_id.partner_id',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=True
    )


class BarberPackageRedemption(models.Model):
    _name = 'bp.barber.package.redemption'
    _description = 'Barber Package Redemption'
    _order = 'date desc, id desc'

    wallet_id = fields.Many2one(
        'bp.barber.package.wallet',
        string='Wallet',
        required=True,
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True
    )
    
    origin_type = fields.Selection([
        ('pos', 'POS'),
        ('appointment', 'Appointment')
    ], string='Origin Type', required=True)
    
    service_id = fields.Many2one(
        'bp.barber.service',
        string='Service',
        help="Service for quantity-based redemptions"
    )
    
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        help="Amount redeemed for value packages"
    )
    
    qty = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        help="Quantity redeemed for service packages"
    )
    
    date = fields.Datetime(
        string='Redemption Date',
        required=True,
        default=fields.Datetime.now
    )
    
    pos_order_line_id = fields.Many2one(
        'pos.order.line',
        string='POS Order Line',
        ondelete='set null'
    )
    
    appointment_id = fields.Many2one(
        'bp.barber.appointment',
        string='Appointment',
        ondelete='set null'
    )
    
    state = fields.Selection([
        ('done', 'Done'),
        ('reversed', 'Reversed')
    ], string='State', default='done', required=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        # related='company_id.currency_id',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=True
    )
    
    # Related fields for display
    package_id = fields.Many2one(
        'bp.barber.package',
        # related='wallet_id.package_id',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=True
    )
    
    def action_reverse(self):
        """Reverse this redemption"""
        for redemption in self:
            if redemption.state == 'reversed':
                continue
            
            # Create credit movement to return units/value
            if redemption.service_id and redemption.qty > 0:
                redemption.wallet_id._create_wallet_line(
                    move_type='credit',
                    service_id=redemption.service_id.id,
                    qty=redemption.qty,
                    note=f"Reversal of redemption {redemption.id}"
                )
            elif redemption.amount > 0:
                redemption.wallet_id._create_wallet_line(
                    move_type='credit',
                    amount=redemption.amount,
                    note=f"Reversal of redemption {redemption.id}"
                )
            
            redemption.state = 'reversed'