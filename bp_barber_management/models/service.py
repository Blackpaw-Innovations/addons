# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class BarberService(models.Model):
    _name = 'bp.barber.service'
    _description = 'Barber Service'
    _order = 'name'

    name = fields.Char(string='Service Name', required=True)
    code = fields.Char(string='Service Code')
    description = fields.Text(string='Description')
    duration_minutes = fields.Integer(string='Duration (Minutes)', default=30)
    list_price = fields.Monetary(string='Price', default=0.0)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Consumable BOM (Stage 11)
    bom_ids = fields.One2many(
        'bp.barber.service.bom',
        'service_id',
        string='Bill of Materials',
        help="Consumable products used for this service"
    )
    
    # POS Integration
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        ondelete='set null',
        help="Linked product template for POS sales"
    )
    product_id = fields.Many2one(
        'product.product',
        string='POS Product',
        ondelete='set null',
        help="Linked POS product for this service",
        compute='_compute_product_id',
        store=True
    )
    
    # @api.depends('product_tmpl_id')
    def _compute_product_id(self):
        """DISABLED to prevent _unknown object errors"""
        for service in self:
            service.product_id = False

    @api.model
    def create(self, vals):
        """Auto-create product template when service is created"""
        service = super().create(vals)
        if not service.product_tmpl_id:
            service._create_product_template()
        return service

    def write(self, vals):
        """Update product template when service is modified"""
        result = super().write(vals)
        for service in self:
            if not service.product_tmpl_id:
                service._create_product_template()
            elif service.product_tmpl_id and any(field in vals for field in ['name', 'list_price', 'description']):
                service._update_product_template()
        return result

    def _create_product_template(self):
        """Create product template for POS integration"""
        # Get or create Services category
        pos_category = self.env['pos.category'].search([('name', '=', 'Services')], limit=1)
        if not pos_category:
            pos_category = self.env['pos.category'].create({
                'name': 'Services',
                'parent_id': False,
            })
        
        # Get or create product category
        product_category = self.env['product.category'].search([('name', '=', 'Services')], limit=1)
        if not product_category:
            product_category = self.env['product.category'].create({
                'name': 'Services',
                'parent_id': False,
            })

        # Create product template
        product_vals = {
            'name': self.name,
            'type': 'service',
            'list_price': self.list_price or 0.0,
            'standard_price': 0.0,
            'sale_ok': True,
            'purchase_ok': False,
            'available_in_pos': True,
            'categ_id': product_category.id,
            'pos_categ_id': pos_category.id,
            'description': self.description or '',
            'barcode': False,
            'default_code': self.code or False,
            'company_id': self.company_id.id or False,
            'requires_service_provider': True,  # Services automatically require a service provider
            'service_provider_type': 'barber',  # Default to barber for barber services
        }
        
        product_template = self.env['product.template'].create(product_vals)
        self.product_tmpl_id = product_template.id
        return product_template

    def _update_product_template(self):
        """Update existing product template with service changes"""
        if self.product_tmpl_id:
            update_vals = {
                'name': self.name,
                'list_price': self.list_price or 0.0,
                'description': self.description or '',
                'default_code': self.code or False,
            }
            self.product_tmpl_id.write(update_vals)

    def unlink(self):
        """Handle product template deletion when service is deleted"""
        product_templates = self.mapped('product_tmpl_id')
        result = super().unlink()
        # Delete associated product templates
        for template in product_templates:
            if template.exists():
                template.unlink()
        return result