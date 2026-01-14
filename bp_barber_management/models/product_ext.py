# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    requires_service_provider = fields.Boolean(
        string='Requires Service Provider',
        default=False,
        help="Check this box if selling this product requires selecting a service provider (barber) in POS. "
             "This will prompt for barber selection when the product is added to cart in POS."
    )
    
    service_provider_type = fields.Selection([
        ('barber', 'Barber'),
        ('any', 'Any Service Provider')
    ], string='Service Provider Type', default='barber',
       help="Type of service provider required for this product")


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    requires_service_provider = fields.Boolean(
        # related='product_tmpl_id.requires_service_provider',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    service_provider_type = fields.Selection([
        ('barber', 'Barber'),
        ('any', 'Any Service Provider')
    ], string='Service Provider Type',
        # related='product_tmpl_id.service_provider_type',  # DISABLED to prevent _unknown object errors
        readonly=True
    )