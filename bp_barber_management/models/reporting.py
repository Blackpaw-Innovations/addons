# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from psycopg2 import sql
import logging

_logger = logging.getLogger(__name__)


class BarberReportAppointment(models.Model):
    """SQL reporting view for appointment analytics"""
    _name = 'bp.barber.report_appointment'
    _description = 'Barber Appointment Analytics'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    # Fields for analytics
    date = fields.Date(string='Date')
    barber_id = fields.Many2one('bp.barber.barber', string='Barber')
    service_id = fields.Many2one('bp.barber.service', string='Service')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_service', 'In Service'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], string='Status')
    duration_minutes = fields.Integer(string='Duration (Minutes)')
    price_total = fields.Monetary(string='Total Price', currency_field='currency_id')
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', string='Currency')

    def init(self):
        """Create the SQL view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    a.start_datetime::date AS date,
                    a.barber_id,
                    s.id AS service_id,
                    a.state,
                    CASE 
                        WHEN a.duration_minutes > 0 THEN a.duration_minutes
                        ELSE COALESCE(s.duration_minutes, 30)
                    END AS duration_minutes,
                    CASE 
                        WHEN a.price_total > 0 THEN a.price_total
                        ELSE COALESCE(s.list_price, 0)
                    END AS price_total,
                    a.company_id,
                    comp.currency_id
                FROM bp_barber_appointment a
                LEFT JOIN bp_barber_appointment_bp_barber_service_rel asr ON asr.bp_barber_appointment_id = a.id
                LEFT JOIN bp_barber_service s ON s.id = asr.bp_barber_service_id
                LEFT JOIN res_company comp ON comp.id = a.company_id
                WHERE a.state IN ('confirmed', 'in_service', 'done', 'no_show')
            )
        """ % self._table)


class BarberReportPosLine(models.Model):
    """SQL reporting view for POS line analytics"""
    _name = 'bp.barber.report_pos_line'
    _description = 'Barber POS Line Analytics'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    # Fields for analytics
    date = fields.Date(string='Date')
    barber_id = fields.Many2one('bp.barber.barber', string='Barber')
    product_id = fields.Many2one('product.product', string='Product')
    is_service = fields.Boolean(string='Is Service')
    amount_subtotal = fields.Monetary(string='Subtotal', currency_field='currency_id')
    qty = fields.Float(string='Quantity')
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', string='Currency')

    def init(self):
        """Create the SQL view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    pol.id,
                    po.date_order::date AS date,
                    pol.barber_id,
                    pol.product_id,
                    CASE 
                        WHEN pt.type = 'service' THEN true
                        ELSE false
                    END AS is_service,
                    pol.price_subtotal AS amount_subtotal,
                    pol.qty,
                    po.company_id,
                    comp.currency_id
                FROM pos_order_line pol
                JOIN pos_order po ON po.id = pol.order_id
                JOIN product_product pp ON pp.id = pol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN res_company comp ON comp.id = po.company_id
                WHERE po.state IN ('paid', 'invoiced', 'done')
                  AND pol.barber_id IS NOT NULL
            )
        """ % self._table)


class BarberReportConsumable(models.Model):
    """SQL reporting view for consumable analytics"""
    _name = 'bp.barber.report_consumable'
    _description = 'Barber Consumable Analytics'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    # Fields for analytics
    date = fields.Date(string='Date')
    barber_id = fields.Many2one('bp.barber.barber', string='Barber')
    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string='Quantity Used')
    company_id = fields.Many2one('res.company', string='Company')

    def init(self):
        """Create the SQL view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    cul.id,
                    cu.date::date AS date,
                    cu.barber_id,
                    cul.product_id,
                    cul.qty,
                    cu.company_id
                FROM bp_barber_consumable_usage_line cul
                JOIN bp_barber_consumable_usage cu ON cu.id = cul.usage_id
            )
        """ % self._table)


class BarberReportingMixin(models.AbstractModel):
    """Mixin to safely handle view creation/deletion"""
    _name = 'bp.barber.reporting.mixin'
    _description = 'Reporting View Management Mixin'

    @api.model
    def _drop_reporting_views(self):
        """Safely drop all reporting views"""
        view_tables = [
            'bp_barber_report_appointment',
            'bp_barber_report_pos_line', 
            'bp_barber_report_consumable'
        ]
        
        for table in view_tables:
            try:
                tools.drop_view_if_exists(self.env.cr, table)
                _logger.info(f"Dropped view {table}")
            except Exception as e:
                _logger.warning(f"Could not drop view {table}: {e}")

    @api.model  
    def _create_reporting_views(self):
        """Recreate all reporting views"""
        try:
            # Trigger init() on each model to recreate views
            self.env['bp.barber.report_appointment'].init()
            self.env['bp.barber.report_pos_line'].init()
            self.env['bp.barber.report_consumable'].init()
            _logger.info("Successfully created reporting views")
        except Exception as e:
            _logger.error(f"Error creating reporting views: {e}")
            raise