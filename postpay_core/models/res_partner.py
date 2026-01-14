# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
from datetime import date, timedelta


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Essential postpay fields only
    current_exposure_json = fields.Text(
        string='Current Exposure Data',
        compute='_compute_postpay_exposure',
        store=True,
        help='JSON data of current postpay exposure by currency'
    )
    
    postpay_aging_json = fields.Text(
        string='Postpay Aging Data', 
        compute='_compute_postpay_aging',
        store=True,
        help='JSON data of aging analysis by currency'
    )
    
    # Payment timing metrics
    avg_days_to_pay = fields.Float(
        string='Average Days to Pay',
        compute='_compute_payment_timing_metrics',
        store=True,
        help='Average number of days to pay invoices'
    )
    
    @api.depends('invoice_ids.amount_residual', 'invoice_ids.state', 'invoice_ids.move_type', 'invoice_ids.currency_id')
    def _compute_postpay_exposure(self):
        """Compute postpay exposure by currency with company isolation."""
        for partner in self:
            exposure_by_currency = {}
            
            # Get all posted customer invoices and credit notes (company-scoped)
            moves = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('amount_residual', '!=', 0),
                ('company_id', '=', self.env.company.id)
            ])
            
            for move in moves:
                currency = move.currency_id
                if currency.id not in exposure_by_currency:
                    exposure_by_currency[currency.id] = {
                        'currency_name': currency.name,
                        'currency_symbol': currency.symbol,
                        'exposure_amount': 0.0,
                    }
                
                # Add invoice residuals, subtract credit note residuals
                if move.move_type == 'out_invoice':
                    exposure_by_currency[currency.id]['exposure_amount'] += move.amount_residual
                else:  # out_refund
                    exposure_by_currency[currency.id]['exposure_amount'] -= move.amount_residual
            
            # Store as JSON
            partner.current_exposure_json = json.dumps(exposure_by_currency)
    
    @api.depends('invoice_ids.amount_residual', 'invoice_ids.invoice_date_due')
    def _compute_postpay_aging(self):
        """Compute aging analysis by currency with company isolation."""
        from datetime import date
        
        for partner in self:
            aging_by_currency = {}
            today = date.today()
            
            # Get all posted unpaid customer invoices (company-scoped)
            invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('amount_residual', '>', 0),
                ('company_id', '=', self.env.company.id)
            ])
            
            for invoice in invoices:
                currency = invoice.currency_id
                if currency.id not in aging_by_currency:
                    aging_by_currency[currency.id] = {
                        'currency_name': currency.name,
                        'currency_symbol': currency.symbol,
                        '0_30': 0.0,
                        '31_60': 0.0,
                        '61_90': 0.0,
                        '90_plus': 0.0,
                    }
                
                # Calculate days overdue
                if invoice.invoice_date_due:
                    days_overdue = (today - invoice.invoice_date_due).days
                    if days_overdue <= 30:
                        aging_by_currency[currency.id]['0_30'] += invoice.amount_residual
                    elif days_overdue <= 60:
                        aging_by_currency[currency.id]['31_60'] += invoice.amount_residual
                    elif days_overdue <= 90:
                        aging_by_currency[currency.id]['61_90'] += invoice.amount_residual
                    else:
                        aging_by_currency[currency.id]['90_plus'] += invoice.amount_residual
                else:
                    # No due date - put in current bucket
                    aging_by_currency[currency.id]['0_30'] += invoice.amount_residual
            
            partner.postpay_aging_json = json.dumps(aging_by_currency)
    
    def _compute_payment_timing_metrics(self):
        """Compute simple payment timing metrics."""
        for partner in self:
            # Get paid invoices from the last year (company-scoped)
            paid_invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('company_id', '=', self.env.company.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('amount_residual', '=', 0),
                ('invoice_date', '>=', fields.Date.today() - timedelta(days=365))
            ])
            
            if paid_invoices:
                # Simple average calculation
                total_days = 0
                count = 0
                for invoice in paid_invoices:
                    if invoice.invoice_date_due and invoice.payment_ids:
                        payment_date = max(invoice.payment_ids.mapped('date'))
                        days_to_pay = (payment_date - invoice.invoice_date_due).days
                        if days_to_pay >= 0:  # Only count positive payment periods
                            total_days += days_to_pay
                            count += 1
                
                partner.avg_days_to_pay = total_days / count if count > 0 else 0.0
            else:
                partner.avg_days_to_pay = 0.0