# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    appointment_id = fields.Many2one(
        'bp.barber.appointment',
        string='Linked Appointment',
        ondelete='set null',
        index=True,
        help="Appointment that was loaded into this POS order"
    )
    
    package_redemptions_data = fields.Text(
        string='Package Redemptions Data',
        help="JSON data of package redemptions applied in POS frontend"
    )

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        """Override to auto-complete linked appointment on payment"""
        result = super()._process_payment_lines(pos_order, order, pos_session, draft)
        
        # Process package sales and redemptions (Stage 10)
        if not draft:
            self._process_package_transactions(order)
        
        # Auto-complete appointment if configured and order is paid
        if (not draft and order.appointment_id and 
            pos_session.config_id.pos_autocomplete_appointment):
            
            appointment = order.appointment_id
            if appointment.state in ['confirmed', 'in_service']:
                try:
                    # Finish the appointment
                    appointment.action_finish_service()
                    
                    # Post message to appointment chatter
                    message_body = _(
                        "Appointment completed via POS Order <b>%s</b><br/>"
                        "Total Amount: %s"
                    ) % (order.name, order.amount_total)
                    
                    appointment.message_post(
                        body=message_body,
                        subject=_("POS Payment Completed"),
                        message_type='comment'
                    )
                    
                    _logger.info(
                        "Auto-completed appointment %s via POS order %s",
                        appointment.name, order.name
                    )
                    
                except Exception as e:
                    _logger.warning(
                        "Failed to auto-complete appointment %s: %s",
                        appointment.name, str(e)
                    )
        
        # Commission creation removed
        
        # Log consumable usage from POS order lines (Stage 11)
        if not draft:
            self._create_consumable_usage(order)
        
        return result
    
    # Commission creation method removed

    def _create_consumable_usage(self, order):
        """Create consumable usage records from POS order lines with assigned barbers"""
        try:
            # Group lines by barber and map to services
            barber_services = {}
            
            for line in order.lines:
                if line.barber_id:
                    # Find service from product (Stage 2 linkage)
                    service = self.env['bp.barber.service'].search([
                        ('product_id', '=', line.product_id.id),
                        ('company_id', '=', order.company_id.id)
                    ], limit=1)
                    
                    if service:
                        if line.barber_id.id not in barber_services:
                            barber_services[line.barber_id.id] = {
                                'barber': line.barber_id,
                                'services': []
                            }
                        
                        # Add service for each quantity (e.g., 2 haircuts = 2 services)
                        for _ in range(int(line.qty)):
                            barber_services[line.barber_id.id]['services'].append(service)
            
            # Create usage record for each barber
            for barber_data in barber_services.values():
                if barber_data['services']:
                    self.env['bp.barber.consumable.usage'].create_from_services(
                        self.env, barber_data['barber'], barber_data['services'], 'pos', order
                    )
                    
        except Exception as e:
            _logger.warning(
                "Failed to create consumable usage for POS order %s: %s",
                order.name, str(e)
            )

    def get_barbers_summary(self):
        """Get summary of barbers for this order (for receipts)"""
        barbers = self.lines.mapped('barber_id.name')
        return ', '.join(filter(None, barbers))
    
    def _process_package_transactions(self, order):
        """Process package sales and redemptions for this order"""
        try:
            # Process package sales (create wallets)
            self._process_package_sales(order)
            
            # Process package redemptions (from frontend data)
            self._process_package_redemptions(order)
            
        except Exception as e:
            _logger.warning(
                "Failed to process package transactions for order %s: %s",
                order.name, str(e)
            )
    
    def _create_package_wallets(self, order):
        """Create wallets for package sales - DISABLED"""
        return  # Package functionality removed

    def _process_package_redemptions(self, order):
        """Process package redemptions from POS frontend data - DISABLED"""
        return  # Package functionality removed
    
    @api.model
    def get_partner_wallets(self, partner_id, company_id):
        """Get active wallets for a partner (called from POS frontend) - DISABLED"""
        return []  # Package functionality removed


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Assigned Barber',
        ondelete='set null',
        index=True,
        help="Barber assigned to this line"
    )
    
    barber_name = fields.Char(
        string='Barber Name',
        # related='barber_id.name',  # DISABLED to prevent _unknown object errors
        readonly=True
    )
    
    has_barber_assigned = fields.Boolean(
        string='Has Barber',
        compute='_compute_has_barber',
        store=False
    )
    
    # @api.depends('barber_id')
    def _compute_has_barber(self):
        """DISABLED to prevent _unknown object errors"""
        for line in self:
            line.has_barber_assigned = False


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_barber_mode = fields.Boolean(
        string='Enable Barber Mode',
        default=False,
        help="Enable barber-specific features in POS"
    )
    
    pos_autocomplete_appointment = fields.Boolean(
        string='Auto-finish Appointment on Payment',
        default=True,
        help="Automatically complete linked appointment when order is paid"
    )
    
    pos_appointments_scope = fields.Selection([
        ('all_barbers', 'All Barbers'),
        ('my_barber_only', 'My Barber Only')
    ], string='Appointments Scope', default='all_barbers',
       help="Filter appointments shown in POS")
    
    pos_barber_default = fields.Many2one(
        'bp.barber.barber',
        string='Default Line Barber',
        help="Default barber assignment for lines when not loaded from appointment"
    )
    
    enable_packages = fields.Boolean(
        string='Enable Packages',
        default=True,
        help="Enable package/membership features in POS"
    )

    @api.model
    def get_today_appointments(self, config_id):
        """Get today's appointments for POS display"""
        config = self.browse(config_id)
        
        # Get today's date in user timezone
        from datetime import datetime, date
        today = date.today()
        
        domain = [
            ('company_id', '=', config.company_id.id),
            ('state', 'in', ['confirmed', 'in_service']),
            ('start_datetime', '>=', datetime.combine(today, datetime.min.time())),
            ('start_datetime', '<', datetime.combine(today, datetime.max.time()))
        ]
        
        # Apply scope filter if needed
        if config.pos_appointments_scope == 'my_barber_only' and config.pos_barber_default:
            domain.append(('barber_id', '=', config.pos_barber_default.id))
        
        appointments = self.env['bp.barber.appointment'].search(domain)
        
        result = []
        for apt in appointments:
            # Get service product IDs
            service_product_ids = []
            for service in apt.service_ids:
                if hasattr(service, 'product_id') and service.product_id:
                    service_product_ids.append(service.product_id.id)
            
            result.append({
                'id': apt.id,
                'name': apt.name,
                'partner_name': apt.partner_id.name if apt.partner_id else 'Walk-in',
                'phone': apt.phone or '',
                'barber_id': apt.barber_id.id if apt.barber_id else False,
                'barber_name': apt.barber_id.name if apt.barber_id else '',
                'barber_color': apt.barber_id.color if apt.barber_id else 0,
                'service_ids': apt.service_ids.ids,
                'service_product_ids': service_product_ids,
                'start_datetime': apt.start_datetime.isoformat() if apt.start_datetime else False,
                'end_datetime': apt.end_datetime.isoformat() if apt.end_datetime else False,
                'price_total': apt.price_total,
                'state': apt.state,
                'duration_minutes': apt.duration_minutes
            })
        
        return result