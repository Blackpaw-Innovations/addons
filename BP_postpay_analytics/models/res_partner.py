# -*- coding: utf-8 -*-
# Part of BP Fuel Solution. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from datetime import timedelta
import json
import logging

_logger = logging.getLogger(__name__)
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_type = fields.Selection([
        ('adhock', _('Adhock')),
        ('drawdown', _('Drawdown')),
        ('post_pay', _('Post pay')),
        ('hybrid', _('Hybrid')),
    ], string=_('Customer Type'), default='adhock', tracking=True,
       help=_("Customer billing type: Adhock (standard), Drawdown (credit-based), "
              "Post pay (invoice after delivery), Hybrid (mixed payment)"))
    
    user_has_contact_manager_rights = fields.Boolean(
        compute='_compute_user_has_contact_manager_rights',
        help=_("Technical field to check if current user has Contact Manager rights")
    )
    
    # Additional pricelists field for multiple selections
    additional_pricelist_ids = fields.Many2many(
        'product.pricelist',
        'partner_additional_pricelist_rel',
        'partner_id',
        'pricelist_id',
        string='Additional Pricelists',
        help='Additional pricelists available for this customer. Main pricelist will be used as default.'
    )
    
    # Contract relationship - DISABLED (model not loaded)
    # fuel_contract_ids = fields.One2many(
    #     'fuel.contract',
    #     'partner_id',
    #     string='Fuel Contracts',
    #     help='Fuel contracts associated with this partner'
    # )
    
    # Smart button counts - DISABLED (depends on fuel_contract_ids)
    # confirmed_contract_count = fields.Integer(
    #     string='Confirmed Contracts',
    #     compute='_compute_contract_counts',
    #     help='Number of confirmed contracts for this partner'
    # )
    
    # expired_contract_count = fields.Integer(
    #     string='Expired Contracts',
    #     compute='_compute_contract_counts',
    #     help='Number of expired contracts for this partner'
    # )
    # 
    # total_contract_count = fields.Integer(
    #     string='Total Contracts',
    #     compute='_compute_contract_counts',
    #     help='Total number of contracts for this partner'
    # )
    
    # Drawdown deposit fields - DISABLED (depends on deposit_ids)
    # drawdown_balance = fields.Monetary(
    #     string='Current Drawdown Balance',
    #     compute='_compute_drawdown_balance',
    #     help='Current available drawdown balance (sum of all deposits in their currencies)'
    # )
    # 
    # drawdown_balance_company_currency = fields.Monetary(
    #     string='Balance (Company Currency)',
    #     compute='_compute_drawdown_balance',
    #     currency_field='company_currency_id',
    #     help='Total drawdown balance converted to company currency'
    # )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        compute='_compute_company_currency',
        help='Currency of the default company'
    )
    
    # Currency-specific deposit totals - DISABLED (depends on deposit_ids)
    # deposit_balances_by_currency = fields.Text(
    #     string='Deposit Balances by Currency',
    #     compute='_compute_drawdown_balance',
    #     help='JSON storage of deposit totals grouped by currency'
    # )
    # 
    # deposit_currencies_display = fields.Html(
    #     string='Currency Breakdown',
    #     compute='_compute_drawdown_balance',
    #     help='HTML display of deposit totals by currency'
    # )
    
    # deposit_ids = fields.One2many(
    #     'bp.drawdown.deposit',
    #     'partner_id',
    #     string='Deposits',
    #     help='Drawdown deposits for this partner'
    # )
    # 
    # active_deposit_ids = fields.One2many(
    #     'bp.drawdown.deposit',
    #     'partner_id',
    #     string='Active Deposits',
    #     domain=[('state', '!=', 'closed')],
    #     help='Active (non-closed) drawdown deposits for this partner'
    # )
    
    # Deposit Eligibility Status - DISABLED (depends on fuel_contract_ids)
    # can_create_deposits = fields.Boolean(
    #     string='Can Create Deposits',
    #     compute='_compute_deposit_eligibility',
    #     help='Whether this customer is eligible to create new deposits'
    # )
    
    deposit_eligibility_reason = fields.Char(
        string='Deposit Eligibility Reason',
        compute='_compute_deposit_eligibility',
        help='Reason why deposits can or cannot be created'
    )
    
    active_contract_count = fields.Integer(
        string='Active Contracts',
        compute='_compute_deposit_eligibility',
        help='Number of active (confirmed) fuel contracts'
    )
    
    # Invoice fields
    unpaid_invoice_ids = fields.One2many(
        'account.move',
        'partner_id',
        string='Unpaid Invoices',
        domain=[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('amount_residual', '>', 0)],
        help='Customer invoices that are unpaid or partially paid'
    )
    
    unpaid_invoice_count = fields.Integer(
        string='Unpaid Invoices',
        compute='_compute_unpaid_invoice_info',
        store=True,
        help='Number of unpaid or partially paid invoices'
    )
    
    total_unpaid_amount = fields.Monetary(
        string='Total Unpaid Amount',
        compute='_compute_unpaid_invoice_info',
        help='Total amount of unpaid invoices'
    )
    
    overdue_invoice_count = fields.Integer(
        string='Overdue Invoices',
        compute='_compute_unpaid_invoice_info',
        store=True,
        help='Number of invoices overdue by more than 30 days'
    )
    
    minimum_required_deposit = fields.Monetary(
        string='Minimum Required Deposit',
        compute='_compute_minimum_required_deposit',
        help='Minimum deposit required from active contract'
    )
    
    # Smart button and warning fields - DISABLED (depends on deposit_ids)
    # deposit_count = fields.Integer(
    #     string='Deposit Count',
    #     compute='_compute_deposit_info',
    #     help='Number of deposits for this partner'
    # )
    
    # balance_warning_level = fields.Selection([
    #     ('none', 'No Warning'),
    #     ('low', 'Below Minimum'),
    #     ('critical', 'Critically Low'),
    #     ('empty', 'Empty Balance')
    # ], string='Balance Warning',
    #    compute='_compute_balance_warning',
    #    help='Warning level for deposit balance monitoring')
    
    # Postpay Credit Management Fields
    agreed_credit_limit = fields.Monetary(
        string='Agreed Credit Limit',
        compute='_compute_postpay_credit_info',
        help='Credit limit from active confirmed contract'
    )
    
    credit_limit_currency_id = fields.Many2one(
        'res.currency',
        string='Credit Limit Currency',
        compute='_compute_postpay_credit_info',
        help='Currency of the credit limit from contract'
    )
    
    current_exposure_json = fields.Text(
        string='Current Exposure by Currency',
        compute='_compute_postpay_exposure',
        help='JSON storage of exposure amounts by currency'
    )
    
    available_credit = fields.Monetary(
        string='Available Credit',
        compute='_compute_postpay_credit_availability',
        currency_field='credit_limit_currency_id',
        help='Available credit in limit currency'
    )
    
    credit_utilization_percentage = fields.Float(
        string='Credit Utilization %',
        compute='_compute_postpay_credit_availability',
        help='Percentage of credit limit utilized'
    )
    
    overlimit_amount = fields.Monetary(
        string='Overlimit Amount',
        compute='_compute_postpay_credit_availability',
        currency_field='credit_limit_currency_id',
        help='Amount over the credit limit'
    )
    
    aging_analysis_json = fields.Text(
        string='Aging Analysis by Currency',
        compute='_compute_postpay_aging',
        help='JSON storage of aging analysis by currency'
    )
    
    has_active_postpay_contract = fields.Boolean(
        string='Has Active Postpay Contract',
        compute='_compute_postpay_credit_info',
        help='Whether partner has an active confirmed contract with credit limit'
    )
    
    is_accounting_manager = fields.Boolean(
        string='Is Accounting Manager',
        compute='_compute_is_accounting_manager',
        help='Whether current user has Accounting Manager access'
    )
    
    # Credit Policy Fields
    is_over_credit_limit = fields.Boolean(
        string='Over Credit Limit',
        compute='_compute_postpay_credit_availability',
        store=True,
        help='Whether customer is currently over their credit limit'
    )
    
    overlimit_activity_id = fields.Many2one(
        'mail.activity',
        string='Overlimit Activity',
        help='Activity created when customer goes over credit limit'
    )
    
    # Payment Time-to-Clear Metrics
    payment_metrics_days = fields.Integer(
        string='Analysis Period (Days)',
        default=90,
        help='Number of days to look back for payment analysis'
    )
    
    avg_days_to_pay = fields.Float(
        string='Average Days to Pay',
        compute='_compute_payment_timing_metrics',
        help='Average days from invoice date to payment date for paid invoices in the analysis period'
    )
    
    median_days_to_pay = fields.Float(
        string='Median Days to Pay',
        compute='_compute_payment_timing_metrics',
        help='Median days from invoice date to payment date for paid invoices in the analysis period'
    )
    
    avg_days_open = fields.Float(
        string='Average Days Open',
        compute='_compute_payment_timing_metrics',
        help='Average days from invoice date to today for current unpaid invoices'
    )
    
    paid_invoices_count = fields.Integer(
        string='Paid Invoices (Period)',
        compute='_compute_payment_timing_metrics',
        help='Number of paid invoices in the analysis period'
    )
    
    unpaid_invoices_count = fields.Integer(
        string='Unpaid Invoices',
        compute='_compute_payment_timing_metrics', 
        help='Number of current unpaid invoices'
    )
    
    # -------------------------------------------------------------------------
    # COMPUTED METHODS
    # -------------------------------------------------------------------------
    
    # @api.depends('customer_type', 'fuel_contract_ids.status')
    # def _compute_deposit_eligibility(self):
    #     """Compute deposit eligibility based on customer type and active contracts."""
    #     for partner in self:
    #         # Check customer type
    #         if partner.customer_type not in ('drawdown', 'hybrid'):
    #             partner.can_create_deposits = False
    #             partner.deposit_eligibility_reason = f'Customer type "{partner.customer_type}" cannot create deposits'
    #             partner.active_contract_count = 0
    #             continue
    #         
    #         # Check active contracts
    #         active_contracts = partner.fuel_contract_ids.filtered(lambda c: c.status == 'confirmed')
    #         partner.active_contract_count = len(active_contracts)
    #         
    #         if active_contracts:
    #             partner.can_create_deposits = True
    #             partner.deposit_eligibility_reason = f'Eligible - {len(active_contracts)} active contract(s)'
    #         else:
    #             partner.can_create_deposits = False
    #             partner.deposit_eligibility_reason = 'No active (confirmed) fuel contracts'
    
    @api.depends('payment_metrics_days')
    def _compute_payment_timing_metrics(self):
        """Compute payment timing metrics for Postpay customers"""
        for partner in self:
            if partner.customer_type not in ('post_pay', 'hybrid'):
                partner.avg_days_to_pay = 0.0
                partner.median_days_to_pay = 0.0
                partner.avg_days_open = 0.0
                partner.paid_invoices_count = 0
                partner.unpaid_invoices_count = 0
                continue
                
            analysis_days = partner.payment_metrics_days or 90
            cutoff_date = fields.Date.today() - timedelta(days=analysis_days)
            today = fields.Date.today()
            
            # Get paid invoices in the analysis period
            paid_invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', cutoff_date),
                ('payment_state', 'in', ('paid', 'in_payment'))
            ])
            
            # Calculate days to pay for paid invoices
            days_to_pay_list = []
            for invoice in paid_invoices:
                if invoice.invoice_date and invoice.invoice_payments_widget:
                    try:
                        # Parse payment info to get payment date
                        payment_info = json.loads(invoice.invoice_payments_widget)
                        if payment_info and 'content' in payment_info:
                            for payment in payment_info['content']:
                                if payment.get('date'):
                                    payment_date = fields.Date.from_string(payment['date'])
                                    days_to_pay = (payment_date - invoice.invoice_date).days
                                    if days_to_pay >= 0:  # Ensure positive values
                                        days_to_pay_list.append(days_to_pay)
                                    break  # Use first payment date
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            # Calculate averages for paid invoices
            partner.paid_invoices_count = len(paid_invoices)
            if days_to_pay_list:
                partner.avg_days_to_pay = sum(days_to_pay_list) / len(days_to_pay_list)
                # Calculate median
                sorted_days = sorted(days_to_pay_list)
                n = len(sorted_days)
                if n % 2 == 0:
                    partner.median_days_to_pay = (sorted_days[n//2 - 1] + sorted_days[n//2]) / 2
                else:
                    partner.median_days_to_pay = sorted_days[n//2]
            else:
                partner.avg_days_to_pay = 0.0
                partner.median_days_to_pay = 0.0
            
            # Get current unpaid invoices
            unpaid_invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial'))
            ])
            
            # Calculate average days open for unpaid invoices
            partner.unpaid_invoices_count = len(unpaid_invoices)
            if unpaid_invoices:
                days_open_list = []
                for invoice in unpaid_invoices:
                    if invoice.invoice_date:
                        days_open = (today - invoice.invoice_date).days
                        if days_open >= 0:
                            days_open_list.append(days_open)
                
                if days_open_list:
                    partner.avg_days_open = sum(days_open_list) / len(days_open_list)
                else:
                    partner.avg_days_open = 0.0
            else:
                partner.avg_days_open = 0.0

    @api.depends('invoice_ids.amount_residual', 'invoice_ids.state', 'invoice_ids.move_type', 'invoice_ids.invoice_date_due')
    def _compute_unpaid_invoice_info(self):
        """Compute unpaid invoice count and total amount."""
        from datetime import date
        
        for partner in self:
            # Get unpaid invoices (posted customer invoices with remaining balance)
            unpaid_invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('company_id', '=', self.env.company.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('amount_residual', '>', 0)
            ])
            
            partner.unpaid_invoice_count = len(unpaid_invoices)
            partner.total_unpaid_amount = sum(unpaid_invoices.mapped('amount_residual'))
            
            # Count overdue invoices (past due date)
            today = date.today()
            overdue_invoices = unpaid_invoices.filtered(
                lambda inv: inv.invoice_date_due and inv.invoice_date_due < today
            )
            partner.overdue_invoice_count = len(overdue_invoices)

    def action_view_unpaid_invoices(self):
        """Action to view unpaid invoices for this partner."""
        self.ensure_one()
        return {
            'name': _('Unpaid Invoices - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('company_id', '=', self.env.company.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('amount_residual', '>', 0)
            ],
            'context': {
                'default_partner_id': self.id,
                'default_move_type': 'out_invoice',
                'partner_customer_type': self.customer_type,
            },
            'target': 'current',
        }

    # @api.depends('fuel_contract_ids.status')
    # def _compute_contract_counts(self):
    #     """Compute contract counts by status."""
    #     for partner in self:
    #         contracts = partner.fuel_contract_ids
    #         partner.confirmed_contract_count = len(contracts.filtered(lambda c: c.status == 'confirmed'))
    #         partner.expired_contract_count = len(contracts.filtered(lambda c: c.status in ('expired', 'terminated')))
    #         partner.total_contract_count = len(contracts)

    # @api.depends('deposit_ids.remaining_amount', 'deposit_ids.state', 'deposit_ids.currency_id')
    # def _compute_drawdown_balance(self):
    #     """Compute current drawdown balance from confirmed deposits."""
    #     import json
    #     
    #     for partner in self:
    #         confirmed_deposits = partner.deposit_ids.filtered(lambda d: d.state == 'confirmed')
    #         
    #         # Initialize balances
    #         currency_balances = {}
    #         total_balance_company = 0.0
    #         company = self.env.company
    #         today = fields.Date.today()
    #         
    #         if confirmed_deposits:
    #             # Group deposits by currency
    #             for deposit in confirmed_deposits:
    #                 currency = deposit.currency_id
    #                 if currency.id not in currency_balances:
    #                     currency_balances[currency.id] = {
    #                         'currency_name': currency.name,
    #                         'currency_symbol': currency.symbol,
    #                         'total_amount': 0.0,
    #                     }
    #                 
    #                 currency_balances[currency.id]['total_amount'] += deposit.remaining_amount
    #                 
    #                 # Add to company currency total
    #                 company_amount = deposit.currency_id._convert(
    #                     deposit.remaining_amount, company.currency_id, company, today
    #                 )
    #                 total_balance_company += company_amount
    #             
    #             # Set partner currency balance (use partner's pricelist currency or first deposit currency)
    #             partner_currency = partner.property_product_pricelist.currency_id or confirmed_deposits[0].currency_id
    #             total_balance = 0.0
    #             
    #             for deposit in confirmed_deposits:
    #                 if deposit.currency_id == partner_currency:
    #                     amount = deposit.remaining_amount
    #                 else:
    #                     amount = deposit.currency_id._convert(
    #                         deposit.remaining_amount, partner_currency, company, today
    #                     )
    #                 total_balance += amount
    #             
    #             partner.drawdown_balance = total_balance
    #             partner.drawdown_balance_company_currency = total_balance_company
    #             
    #             # Store currency balances as JSON
    #             partner.deposit_balances_by_currency = json.dumps(currency_balances)
    #             
    #             # Create HTML display for currencies with unique IDs
    #             html_parts = []
    #             for curr_id, balance_info in currency_balances.items():
    #                 formatted_amount = "{:,.2f}".format(balance_info['total_amount'])
    #                 unique_id = f"partner_{partner.id}_curr_{curr_id}"
    #                 html_parts.append(
    #                     f"<div class='d-flex justify-content-between mb-1' id='{unique_id}'>"
    #                     f"<span class='text-muted'>{balance_info['currency_name']}:</span>"
    #                     f"<span class='fw-bold'>{formatted_amount} {balance_info['currency_symbol']}</span>"
    #                     f"</div>"
    #                 )
    #             
    #             if html_parts:
    #                 partner.deposit_currencies_display = f"<div class='small' id='deposits_{partner.id}'>{''.join(html_parts)}</div>"
    #             else:
    #                 partner.deposit_currencies_display = f"<div class='small text-muted' id='no_deposits_{partner.id}'>No deposits</div>"
    #             
    #         else:
    #             partner.drawdown_balance = 0.0
    #             partner.drawdown_balance_company_currency = 0.0
    #             partner.deposit_balances_by_currency = json.dumps({})
    #             partner.deposit_currencies_display = f"<div class='small text-muted' id='no_deposits_{partner.id}'>No deposits</div>"
    
    def _compute_company_currency(self):
        """Set company currency for display."""
        for partner in self:
            partner.company_currency_id = self.env.company.currency_id
    
    @api.model
    def _run_balance_monitoring(self, company_id=None):
        """Run automated balance monitoring for partners."""
        if not company_id:
            company_id = self.env.company.id
            
        # Get monitoring configuration
        config = self.env['bp.monitoring.config'].get_config_for_company(company_id)
        if not config.active:
            return {'status': 'disabled', 'message': 'Monitoring is disabled for this company'}
            
        # Get all drawdown partners for the company
        partners = self.search([
            ('customer_type', 'in', ['drawdown', 'hybrid']),
            ('company_id', '=', company_id),
            ('is_company', '=', False)
        ])
        
        results = {
            'status': 'success',
            'partners_processed': len(partners),
            'critical_alerts': 0,
            'low_alerts': 0,
            'activities_created': 0,
            'emails_sent': 0
        }
        
        for partner in partners:
            # Force recomputation of balance - DISABLED
            # partner._compute_drawdown_balance()
            # partner._compute_balance_warning()
            
            # Check if we need to create alerts
            previous_warning_level = partner._origin.balance_warning_level if hasattr(partner, '_origin') else 'none'
            current_warning_level = partner.balance_warning_level
            
            # Only create alerts if warning level changed to worse or first time
            if self._should_create_alert(previous_warning_level, current_warning_level):
                if current_warning_level == 'critical':
                    self._create_balance_alert(partner, 'critical', config)
                    results['critical_alerts'] += 1
                elif current_warning_level == 'low':
                    self._create_balance_alert(partner, 'low', config)
                    results['low_alerts'] += 1
        
        # Update last run timestamp
        config.write({'last_run_date': fields.Datetime.now()})
        
        return results
    
    def _should_create_alert(self, previous_level, current_level):
        """Determine if an alert should be created based on warning level change."""
        # Alert priority: none < low < critical
        level_priority = {'none': 0, 'low': 1, 'critical': 2}
        
        prev_priority = level_priority.get(previous_level, 0)
        curr_priority = level_priority.get(current_level, 0)
        
        # Create alert if current level is worse than previous
        return curr_priority > prev_priority
    
    def _create_balance_alert(self, partner, alert_type, config):
        """Create activity and/or email alert for low balance."""
        # Create activity if enabled
        if config.enable_activities:
            self._create_balance_activity(partner, alert_type, config)
            
        # Send email if enabled
        if config.enable_email_notifications:
            self._send_balance_email(partner, alert_type, config)
    
    def _create_balance_activity(self, partner, alert_type, config):
        """Create activity for balance alert."""
        # Determine activity type
        if alert_type == 'critical' and config.critical_activity_type_id:
            activity_type = config.critical_activity_type_id
        elif alert_type == 'low' and config.low_activity_type_id:
            activity_type = config.low_activity_type_id
        else:
            # Use default activity type
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                return False
        
        # Determine assignee
        assignee = partner.user_id or config.activity_user_id
        if not assignee:
            return False
            
        # Create activity
        self.env['mail.activity'].create({
            'res_model_id': self.env.ref('base.model_res_partner').id,
            'res_id': partner.id,
            'activity_type_id': activity_type.id,
            'user_id': assignee.id,
            'summary': self._get_activity_summary(partner, alert_type),
            'note': self._get_activity_note(partner, alert_type),
            'date_deadline': fields.Date.today()
        })
        return True
    
    def _send_balance_email(self, partner, alert_type, config):
        """Send email notification for balance alert."""
        # Determine email template
        if alert_type == 'critical' and config.critical_email_template_id:
            template = config.critical_email_template_id
        elif alert_type == 'low' and config.low_email_template_id:
            template = config.low_email_template_id
        else:
            return False
            
        # Determine recipients
        recipients = []
        if partner.user_id and partner.user_id.partner_id.email:
            recipients.append(partner.user_id.partner_id.email)
            
        # Add notification group users
        for group in config.notification_group_ids:
            for user in group.users:
                if user.partner_id.email and user.partner_id.email not in recipients:
                    recipients.append(user.partner_id.email)
        
        if not recipients:
            return False
            
        # Send email
        try:
            template.with_context(
                email_to=','.join(recipients),
                partner_balance=partner.drawdown_balance_company_currency,
                alert_type=alert_type.title()
            ).send_mail(partner.id, force_send=True)
            return True
        except Exception as e:
            # Log error but don't fail the monitoring
            _logger.warning(f'Failed to send balance alert email for partner {partner.name}: {e}')
            return False
    
    def _get_activity_summary(self, partner, alert_type):
        """Get activity summary for balance alert."""
        if alert_type == 'critical':
            return _(f'URGENT: {partner.name} - Critical Balance Alert')
        else:
            return _(f'{partner.name} - Low Balance Alert')
    
    def _get_activity_note(self, partner, alert_type):
        """Get activity note for balance alert."""
        balance = partner.drawdown_balance_company_currency
        min_required = partner.minimum_required_deposit
        
        if alert_type == 'critical':
            note = _(f'''CRITICAL BALANCE ALERT

Partner: {partner.name}
Current Balance: {balance} {partner.company_currency_id.symbol}
Minimum Required: {min_required} {partner.company_currency_id.symbol}

This partner's balance is at critical level. Immediate action required to:
1. Contact customer for deposit top-up
2. Suspend fuel deliveries if necessary
3. Review credit terms''')
        else:
            note = _(f'''LOW BALANCE ALERT

Partner: {partner.name}
Current Balance: {balance} {partner.company_currency_id.symbol}
Minimum Required: {min_required} {partner.company_currency_id.symbol}

This partner's balance is running low. Consider:
1. Contacting customer for deposit replenishment
2. Review upcoming delivery schedule
3. Prepare deposit invoice''')
        
        return note
    
        # @api.depends('fuel_contract_ids.agreed_deposit', 'fuel_contract_ids.status')
    # def _compute_minimum_required_deposit(self):
    #     """Compute minimum required deposit from active contracts."""
    #     for partner in self:
    #         active_contracts = partner.fuel_contract_ids.filtered(
    #             lambda c: c.status == 'confirmed'
    #         )
    #         partner.minimum_required_deposit = max(active_contracts.mapped('agreed_deposit')) if active_contracts else 0.0
    
    # @api.depends('deposit_ids')
    # def _compute_deposit_info(self):
    #     """Compute deposit count for smart buttons."""
    #     for partner in self:
    #         partner.deposit_count = len(partner.deposit_ids)
    
    # Overdraft tracking fields - DISABLED (depends on deposit_ids)
    # current_overdraft = fields.Monetary(
    #     string='Current Overdraft',
    #     compute='_compute_overdraft_summary',
    #     currency_field='currency_id',
    #     help='Total amount owed above available deposits'
    # )
    # 
    # overdraft_percentage = fields.Float(
    #     string='Overdraft %',
    #     compute='_compute_overdraft_summary',
    #     help='Percentage of overdraft above agreed deposit amount'
    # )
    
    # @api.depends('invoice_ids.amount_residual', 'deposit_ids.remaining_amount', 'minimum_required_deposit')
    # def _compute_overdraft_summary(self):
    #     """Compute overall overdraft summary for the customer."""
    #     for partner in self:
    #         # Get total unpaid invoice amounts for this customer
    #         unpaid_invoices = self.env['account.move'].search([
    #             ('partner_id', '=', partner.id),
    #             ('company_id', '=', self.env.company.id),
    #             ('move_type', '=', 'out_invoice'),
    #             ('state', '=', 'posted'),
    #             ('amount_residual', '>', 0)
    #         ])\n    #         total_unpaid = sum(unpaid_invoices.mapped('amount_residual'))\n    #         \n    #         # Get total available deposits (remaining amounts across all deposits)\n    #         total_deposits = sum(partner.deposit_ids.filtered(\n    #             lambda d: d.state == 'confirmed'\n    #         ).mapped('remaining_amount'))\n    #         \n    #         # Calculate overdraft (what they owe minus what they have in deposits)\n    #         overdraft = total_unpaid - total_deposits
    #         partner.current_overdraft = max(0.0, overdraft)  # Only show positive overdraft
    #         
    #         # Calculate percentage using new formula: 1 - (overdraft / (agreed - current_balance))
    #         agreed_deposit = partner.minimum_required_deposit or 0.0
    #         current_balance = total_deposits
    #         
    #         if agreed_deposit > current_balance and partner.current_overdraft > 0:
    #             shortfall = agreed_deposit - current_balance
    #             partner.overdraft_percentage = 1 - (partner.current_overdraft / shortfall)
    #         else:
    #             partner.overdraft_percentage = 0.0
    
    # @api.depends('drawdown_balance', 'minimum_required_deposit', 'customer_type')
    # def _compute_balance_warning(self):
    #     """Compute balance warning level for UI indicators using monitoring configuration."""
    #     for partner in self:
    #         if partner.customer_type not in ('drawdown', 'hybrid'):
    #             partner.balance_warning_level = 'none'
    #             continue
    #             
    #         # Get monitoring configuration for partner's company
    #         config = self.env['bp.monitoring.config'].get_config_for_company(
    #             partner.company_id.id if partner.company_id else None
    #         )
    #         
    #         balance = partner.drawdown_balance_company_currency
    #         min_required = partner.minimum_required_deposit
    #         
    #         # Check critical threshold (absolute value)
    #         if balance <= config.critical_threshold:
    #             partner.balance_warning_level = 'critical'
    #         # Check low threshold (percentage of minimum required)
    #         elif (min_required > 0 and 
    #               balance < (min_required * config.low_threshold_percentage / 100.0)):
    #             partner.balance_warning_level = 'low' 
    #         # Check warning threshold (percentage of minimum required)
    #         elif (min_required > 0 and 
    #               balance < (min_required * config.warning_threshold_percentage / 100.0)):
    #             partner.balance_warning_level = 'low'  # Map warning to low for now
    #         else:
    #             partner.balance_warning_level = 'none'
    
    def _compute_postpay_credit_info(self):
        """Compute credit limit - simplified version without fuel contracts."""
        for partner in self:
            # Set default values since fuel contracts are not loaded
            partner.agreed_credit_limit = 0.0
            partner.credit_limit_currency_id = False
            partner.has_active_postpay_contract = False
    
    @api.depends('invoice_ids.amount_residual', 'invoice_ids.state', 'invoice_ids.move_type', 'invoice_ids.currency_id')
    def _compute_postpay_exposure(self):
        """Compute current exposure by currency."""
        import json
        
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
                    exposure_by_currency[currency.id]['exposure_amount'] -= abs(move.amount_residual)
            
            # Remove currencies with zero exposure
            exposure_by_currency = {k: v for k, v in exposure_by_currency.items() if v['exposure_amount'] != 0}
            
            partner.current_exposure_json = json.dumps(exposure_by_currency)
    
    @api.depends('current_exposure_json')
    def _compute_postpay_credit_availability(self):
        """Compute available credit and utilization percentage."""
        import json
        
        for partner in self:
            # Skip if no active contract or no credit limit set
            if (not partner.has_active_postpay_contract or 
                not partner.credit_limit_currency_id or 
                partner.agreed_credit_limit <= 0):
                partner.available_credit = 0.0
                partner.credit_utilization_percentage = 0.0
                partner.overlimit_amount = 0.0
                partner.is_over_credit_limit = False
                continue
            
            try:
                exposure_data = json.loads(partner.current_exposure_json or '{}')
            except (json.JSONDecodeError, TypeError):
                exposure_data = {}
            
            # Find exposure in the same currency as credit limit
            limit_currency_exposure = 0.0
            limit_currency_id = str(partner.credit_limit_currency_id.id)
            
            if limit_currency_id in exposure_data:
                limit_currency_exposure = exposure_data[limit_currency_id]['exposure_amount']
            
            # Calculate availability and utilization
            available = partner.agreed_credit_limit - limit_currency_exposure
            partner.available_credit = max(0.0, available)
            
            if partner.agreed_credit_limit > 0:
                partner.credit_utilization_percentage = (limit_currency_exposure / partner.agreed_credit_limit) * 100
            else:
                partner.credit_utilization_percentage = 0.0
            
            # Calculate overlimit amount and status
            partner.overlimit_amount = max(0.0, limit_currency_exposure - partner.agreed_credit_limit)
            partner.is_over_credit_limit = partner.overlimit_amount > 0
    
    @api.depends('invoice_ids.amount_residual', 'invoice_ids.invoice_date_due', 'invoice_ids.state', 'invoice_ids.move_type', 'invoice_ids.currency_id')
    def _compute_postpay_aging(self):
        """Compute aging analysis by currency."""
        import json
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
                        'total': 0.0
                    }
                
                # Calculate days overdue
                if invoice.invoice_date_due:
                    days_overdue = (today - invoice.invoice_date_due).days
                else:
                    days_overdue = 0
                
                amount = invoice.amount_residual
                
                # Categorize by aging buckets
                if days_overdue <= 30:
                    aging_by_currency[currency.id]['0_30'] += amount
                elif days_overdue <= 60:
                    aging_by_currency[currency.id]['31_60'] += amount
                elif days_overdue <= 90:
                    aging_by_currency[currency.id]['61_90'] += amount
                else:
                    aging_by_currency[currency.id]['90_plus'] += amount
                
                aging_by_currency[currency.id]['total'] += amount
            
            partner.aging_analysis_json = json.dumps(aging_by_currency)
    
    # Payment Action Methods
    def action_pay_all_invoices(self):
        """Open payment wizard for all unpaid invoices - Accounting Manager only"""
        self._check_accounting_manager_access()
        return self._open_payment_wizard()
    
    def action_pay_selected_invoices(self, invoice_ids=None):
        """Open invoice selection wizard - Accounting Manager only"""
        self._check_accounting_manager_access()
        self.ensure_one()
        
        return {
            'name': _('Select Invoices to Pay'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.pay.selected.invoices.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            },
        }
    
    def _check_accounting_manager_access(self):
        """Verify user has Accounting Manager access"""
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError(_(
                'Access Denied: Only Accounting Managers can process payments. '
                'Please contact your administrator for the required permissions.'
            ))
    
    def _open_payment_wizard(self, selected_invoice_ids=None):
        """Open Odoo's Register Payment wizard with pre-populated data"""
        self.ensure_one()
        
        # Get invoices to pay
        if selected_invoice_ids:
            invoices = self.env['account.move'].browse(selected_invoice_ids)
            # Validate invoices belong to this partner and are unpaid
            invalid_invoices = invoices.filtered(
                lambda inv: inv.partner_id != self or inv.state != 'posted' or inv.amount_residual <= 0
            )
            if invalid_invoices:
                raise UserError(_(
                    'Some selected invoices are invalid for payment: {}'
                ).format(', '.join(invalid_invoices.mapped('name'))))
        else:
            # Get all unpaid invoices for this partner
            invoices = self.env['account.move'].search([
                ('partner_id', '=', self.id),
                ('company_id', '=', self.env.company.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('amount_residual', '>', 0)
            ])
        
        if not invoices:
            raise UserError(_('No unpaid invoices found for payment.'))
        
        # Calculate total amount to pay
        total_residual = sum(invoices.mapped('amount_residual'))
        
        # Get default inbound journal (bank or cash)
        default_journal = self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not default_journal:
            raise UserError(_('No bank or cash journal found. Please configure at least one payment journal.'))
        
        # Determine currency - use company currency if mixed, or single currency if all same
        invoice_currencies = invoices.mapped('currency_id')
        if len(invoice_currencies) == 1:
            payment_currency = invoice_currencies[0]
        else:
            payment_currency = self.env.company.currency_id
            # Convert total to company currency if mixed currencies
            total_residual = sum([
                inv.currency_id._convert(
                    inv.amount_residual,
                    payment_currency,
                    self.env.company,
                    fields.Date.today()
                ) for inv in invoices
            ])
        
        # Create payment wizard context
        ctx = {
            'active_model': 'account.move',
            'active_ids': invoices.ids,
            'default_partner_id': self.id,
            'default_amount': total_residual,
            'default_currency_id': payment_currency.id,
            'default_journal_id': default_journal.id,
            'default_payment_type': 'inbound',
            'default_partner_type': 'customer',
            'bp_postpay_payment': True,  # Flag to identify our payment flow
        }
        
        return {
            'name': _('Register Payment - {} invoices').format(len(invoices)),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
    
    def action_view_confirmed_contracts(self):
        """Open confirmed contracts for this partner."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmed Contracts',
            'res_model': 'fuel.contract',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id), ('status', '=', 'confirmed')],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_expired_contracts(self):
        """Open expired contracts for this partner."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expired Contracts',
            'res_model': 'fuel.contract',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id), ('status', '=', 'expired')],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_all_contracts(self):
        """View all contracts for this partner"""
        self.ensure_one()
        
        action = self.env.ref('BP_fuel_solution.action_fuel_contract').read()[0]
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action
    
    def action_view_postpay_exposure(self):
        """View unpaid invoices for Postpay/Hybrid customers (Postpay Exposure)"""
        self.ensure_one()
        
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['name'] = f'Postpay Exposure - {self.name}'
        action['domain'] = [
            ('partner_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial'))
        ]
        action['context'] = {
            'default_partner_id': self.id,
            'default_move_type': 'out_invoice',
            'search_default_unpaid': 1
        }
        return action
    
    def action_new_deposit(self):
        """Create a new drawdown deposit for this partner."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Deposit',
            'res_model': 'bp.drawdown.deposit',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_deposits(self):
        """View all deposits for this partner."""
        action = {
            'name': _('Drawdown Deposits'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.drawdown.deposit',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
        
        # If only one deposit, open form view directly - DISABLED
        # if self.deposit_count == 1:
        #     action.update({
        #         'view_mode': 'form',
        #         'res_id': self.deposit_ids[0].id,
        #     })
        
        return action

    @api.model
    def _get_available_pricelists(self):
        """Get all available pricelists for this customer"""
        pricelists = []
        
        # Add main pricelist if exists
        if self.property_product_pricelist:
            pricelists.append(self.property_product_pricelist)
            
        # Add additional pricelists
        pricelists.extend(self.additional_pricelist_ids)
        
        return pricelists
    
    def get_pricelist_for_currency(self, currency_id=False):
        """Get appropriate pricelist for given currency"""
        available_pricelists = self._get_available_pricelists()
        
        if currency_id:
            # Try to find pricelist matching currency
            for pricelist in available_pricelists:
                if pricelist.currency_id.id == currency_id:
                    return pricelist
        
        # Return main pricelist or first available
        return self.property_product_pricelist or (available_pricelists[0] if available_pricelists else False)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to enforce customer type permissions"""
        self._check_customer_type_permissions(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        """Override write to enforce customer type permissions"""
        if 'customer_type' in vals:
            # Check permissions for each record being modified
            for record in self:
                self._check_customer_type_permissions([vals])
        return super().write(vals)
    
    @api.model
    def load(self, fields, data):
        """Override load (used by CSV imports) to enforce customer type permissions"""
        if 'customer_type' in fields:
            customer_type_index = fields.index('customer_type')
            restricted_types = ['drawdown', 'post_pay', 'hybrid']
            
            # Check each row for restricted customer types
            for row_index, row_data in enumerate(data):
                if (len(row_data) > customer_type_index and 
                    row_data[customer_type_index] in restricted_types):
                    if not self._user_has_contact_manager_rights():
                        # Return error result in the format expected by import system
                        return {
                            'ids': [],
                            'messages': [{
                                'type': 'error',
                                'message': self._get_restricted_customer_type_error(),
                                'rows': {'from': row_index, 'to': row_index},
                                'record': row_index,
                            }]
                        }
        
        return super().load(fields, data)
    
    def _load_records_write(self, values):
        """Override batch write operations for imports"""
        # Check permissions before batch operations
        if values and 'customer_type' in values[0]:
            vals_list = [vals for vals in values if 'customer_type' in vals]
            if vals_list:
                self._check_customer_type_permissions(vals_list)
        return super()._load_records_write(values)
    
    def _load_records_create(self, values):
        """Override batch create operations for imports"""
        # Check permissions before batch operations
        if values:
            vals_list = [vals for vals in values if 'customer_type' in vals]
            if vals_list:
                self._check_customer_type_permissions(vals_list)
        return super()._load_records_create(values)

    @api.depends_context('uid')
    def _compute_user_has_contact_manager_rights(self):
        """Compute if current user has Contact Manager rights"""
        has_rights = self._user_has_contact_manager_rights()
        for record in self:
            record.user_has_contact_manager_rights = has_rights
    
    def _user_has_contact_manager_rights(self):
        """Check if current user has Contact Manager rights"""
        # Check if user has Contact Manager group using direct group lookup
        contact_manager_group = self.env.ref('BP_fuel_solution.group_contact_manager', raise_if_not_found=False)
        if not contact_manager_group:
            # Fallback to lowercase module name if not found
            contact_manager_group = self.env.ref('bp_fuel_solution.group_contact_manager', raise_if_not_found=False)
        
        if contact_manager_group:
            return contact_manager_group in self.env.user.groups_id
        return False
    
    def _get_restricted_customer_type_error(self):
        """Get standardized error message for restricted customer types"""
        return _(
            "Access Denied: Only Contact Managers can create or modify contacts with "
            "customer types Drawdown, Post pay, or Hybrid. "
            "Please contact your administrator to assign the Contact Manager role, "
            "or use the Adhock customer type instead."
        )
    
    @api.depends_context('uid')
    def _compute_is_accounting_manager(self):
        """Compute if current user has Accounting Manager access"""
        is_manager = self.env.user.has_group('account.group_account_manager')
        for partner in self:
            partner.is_accounting_manager = is_manager

    def _check_customer_type_permissions(self, vals_list):
        """Check if user has permission to create/modify restricted customer types"""
        restricted_types = ['drawdown', 'post_pay', 'hybrid']
        
        # Skip check if user has Contact Manager rights
        if self._user_has_contact_manager_rights():
            return
        
        # Check if any restricted customer type is being set
        for vals in vals_list:
            customer_type = vals.get('customer_type')
            if customer_type in restricted_types:
                raise AccessError(self._get_restricted_customer_type_error())