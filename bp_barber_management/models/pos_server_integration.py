# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        """Load POS data and add barbers to the response dictionary."""
        res = super().load_pos_data()
        
        # Add barber data if barber mode is enabled
        if self.config_id.enable_barber_mode:
            barbers = self.env['bp.barber.barber'].search_read([
                ('active', '=', True), 
                ('company_id', '=', self.config_id.company_id.id)
            ], fields=['name', 'barber_code', 'color', 'active'])
            res['bp_barber_barbers'] = barbers
        
        return res


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_pos_ui_order(self, ui_order, draft=False):
        """Override to validate barber assignments before processing"""
        
        # Check if barber mode is enabled for this session
        session = self.env['pos.session'].browse(ui_order.get('pos_session_id'))
        if session.config_id.enable_barber_mode and not draft:
            
            # Validate barber assignments on order lines
            for line_data in ui_order.get('lines', []):
                line_vals = line_data[2]  # Get line values
                product_id = line_vals.get('product_id')
                
                if product_id:
                    product = self.env['product.product'].browse(product_id)
                    
                    # Check if product requires service provider
                    if hasattr(product, 'requires_service_provider') and product.requires_service_provider:
                        barber_id = line_vals.get('barber_id')
                        
                        if not barber_id:
                            raise UserError(_(
                                "Product '%s' requires a barber assignment. "
                                "Please assign a barber before completing the order."
                            ) % product.display_name)
        
        # Call parent method
        return super()._process_pos_ui_order(ui_order, draft)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _export_for_ui(self, orderline):
        """Export orderline data including barber information"""
        result = super()._export_for_ui(orderline)
        
        # Add barber information
        if orderline.barber_id:
            result.update({
                'barber_id': orderline.barber_id.id,
                'barber_name': orderline.barber_id.name,
                'barber_color': orderline.barber_id.color,
            })
        
        # Add service provider requirement info
        if hasattr(orderline.product_id, 'requires_service_provider'):
            result.update({
                'requires_service_provider': orderline.product_id.requires_service_provider,
                'service_provider_type': orderline.product_id.service_provider_type,
            })
        
        return result


class PosSession(models.Model):
    _inherit = 'pos.session'
    
    def _get_pos_ui_product_product(self, params):
        """Override to include service provider fields in product data"""
        # Get the standard product fields
        products = super()._get_pos_ui_product_product(params)
        
        # Add service provider fields to each product
        for product in products:
            product_record = self.env['product.product'].browse(product['id'])
            product.update({
                'requires_service_provider': getattr(product_record, 'requires_service_provider', False),
                'service_provider_type': getattr(product_record, 'service_provider_type', False),
            })
        
        return products


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def validate_barber_assignment(self, product_id, barber_id=None):
        """Server-side validation for barber assignment"""
        product = self.env['product.product'].browse(product_id)
        
        if hasattr(product, 'requires_service_provider') and product.requires_service_provider:
            if not barber_id:
                return {
                    'success': False,
                    'message': _("Product '%s' requires a barber assignment.") % product.display_name,
                    'requires_barber': True,
                    'product_name': product.display_name,
                }
        
        return {'success': True, 'requires_barber': False}

    @api.model 
    def get_available_barbers(self, config_id):
        """Get available barbers for POS configuration"""
        config = self.browse(config_id)
        
        if not config.enable_barber_mode:
            return []
        
        barbers = self.env['bp.barber.barber'].search([
            ('active', '=', True),
            ('company_id', '=', config.company_id.id)
        ])
        
        return [{
            'id': barber.id,
            'name': barber.name,
            'barber_code': barber.barber_code,
            'color': barber.color,
        } for barber in barbers]

    @api.model
    def assign_barber_to_line(self, line_data, barber_id):
        """Assign barber to order line"""
        # This will be called from the frontend
        return {
            'success': True,
            'barber_id': barber_id,
            'message': _("Barber assigned successfully.")
        }