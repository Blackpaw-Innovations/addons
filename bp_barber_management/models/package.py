# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BarberPackage(models.Model):
    _name = 'bp.barber.package'
    _description = 'Barber Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Package Name',
        required=True,
        translate=True
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        help="Unique package code"
    )
    
    package_type = fields.Selection([
        ('qty', 'Quantity-based'),
        ('bundle', 'Bundle'),
        ('value', 'Value-based (Credit)')
    ], string='Package Type', required=True, default='qty')
    
    line_ids = fields.One2many(
        'bp.barber.package.line',
        'package_id',
        string='Package Lines',
        help="Services included in this package (for qty/bundle types only)"
    )
    
    value_amount = fields.Monetary(
        string='Credit Amount',
        currency_field='currency_id',
        help="Credit value for value-based packages"
    )
    
    duration_days = fields.Integer(
        string='Validity (Days)',
        help="Package validity from purchase date. Leave empty for no expiry."
    )
    
    pos_product_id = fields.Many2one(
        'product.product',
        string='POS Product',
        help="Product representing this package in POS",
        ondelete='set null'
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
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # Computed fields for UI
    suggested_price = fields.Monetary(
        string='Suggested Price',
        compute='_compute_suggested_price',
        currency_field='currency_id'
    )
    
    wallet_count = fields.Integer(
        string='Active Wallets',
        compute='_compute_wallet_count'
    )
    
    # @api.depends('line_ids.service_id', 'value_amount', 'package_type')
    def _compute_suggested_price(self):
        """DISABLED to prevent _unknown object errors"""
        for package in self:
            package.suggested_price = 0.0
    
    def _compute_wallet_count(self):
        for package in self:
            package.wallet_count = self.env['bp.barber.package.wallet'].search_count([
                ('package_id', '=', package.id),
                ('active', '=', True)
            ])
    
    @api.model_create_multi
    def create(self, vals_list):
        packages = super().create(vals_list)
        for package in packages:
            if not package.pos_product_id:
                package._create_pos_product()
        return packages
    
    def write(self, vals):
        result = super().write(vals)
        # Update POS product if relevant fields changed
        if any(field in vals for field in ['name', 'value_amount', 'suggested_price']):
            for package in self:
                if package.pos_product_id:
                    package._update_pos_product()
        return result
    
    def _create_pos_product(self):
        """Auto-create POS product for this package"""
        product_vals = {
            'name': self.name,
            'type': 'service',
            'sale_ok': True,
            'available_in_pos': True,
            'categ_id': self.env.ref('point_of_sale.product_category_pos').id,
            'company_id': self.company_id.id,
        }
        
        # Set price based on package type
        if self.package_type == 'value':
            product_vals['list_price'] = self.value_amount
        else:
            product_vals['list_price'] = self.suggested_price
            
        product = self.env['product.product'].create(product_vals)
        self.pos_product_id = product.id
        
    def _update_pos_product(self):
        """Update linked POS product details"""
        if self.pos_product_id:
            update_vals = {
                'name': self.name,
            }
            if self.package_type == 'value':
                update_vals['list_price'] = self.value_amount
            else:
                update_vals['list_price'] = self.suggested_price
                
            self.pos_product_id.write(update_vals)
    
    def action_view_wallets(self):
        """Smart button action to view related wallets"""
        return {
            'name': _('Package Wallets'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.package.wallet',
            'view_mode': 'tree,form',
            'domain': [('package_id', '=', self.id)],
            'context': {'default_package_id': self.id}
        }
    
    @api.constrains('code')
    def _check_unique_code(self):
        for package in self:
            existing = self.search([
                ('code', '=', package.code),
                ('company_id', '=', package.company_id.id),
                ('id', '!=', package.id)
            ])
            if existing:
                raise ValidationError(_('Package code must be unique per company.'))
    
    @api.constrains('package_type', 'line_ids', 'value_amount')
    def _check_package_configuration(self):
        for package in self:
            if package.package_type in ('qty', 'bundle') and not package.line_ids:
                raise ValidationError(_('Quantity and Bundle packages must have at least one service line.'))
            if package.package_type == 'value' and not package.value_amount:
                raise ValidationError(_('Value packages must have a credit amount.'))


class BarberPackageLine(models.Model):
    _name = 'bp.barber.package.line'
    _description = 'Barber Package Line'
    _order = 'package_id, sequence, service_id'

    package_id = fields.Many2one(
        'bp.barber.package',
        string='Package',
        required=True,
        ondelete='cascade'
    )
    
    service_id = fields.Many2one(
        'bp.barber.service',
        string='Service',
        required=True
    )
    
    qty = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    

    
    currency_id = fields.Many2one(
        'res.currency',
        # related='package_id.currency_id',  # DISABLED to prevent _unknown object errors
        store=True,
        readonly=True
    )
    
    line_total = fields.Monetary(
        string='Line Total',
        compute='_compute_line_total',
        currency_field='currency_id'
    )
    
    # @api.depends('qty', 'service_id.list_price')
    def _compute_line_total(self):
        """DISABLED to prevent _unknown object errors"""
        for line in self:
            line.line_total = 0.0
    
    @api.constrains('qty')
    def _check_qty_positive(self):
        for line in self:
            if line.qty <= 0:
                raise ValidationError(_('Quantity must be positive.'))