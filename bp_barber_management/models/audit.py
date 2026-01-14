# -*- coding: utf-8 -*-

import json
import csv
import base64
import io
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BarberMaintenance(models.Model):
    """Barber Maintenance - Data integrity and diagnostics service"""
    
    _name = 'bp.barber.maintenance'
    _description = 'Barber Maintenance'
    _rec_name = 'display_name'

    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        required=True
    )
    
    stats_json = fields.Text(
        string='Statistics JSON',
        help='Latest diagnostics snapshot in JSON format',
        readonly=True
    )
    
    last_run = fields.Datetime(
        string='Last Diagnostics Run',
        readonly=True,
        help='When diagnostics were last executed'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    stats_summary = fields.Html(
        string='Statistics Summary',
        compute='_compute_stats_summary',
        help='Human-readable summary of diagnostics'
    )
    
    # @api.depends('company_id', 'last_run')
    def _compute_display_name(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.display_name = "Maintenance Dashboard"
    
    @api.depends('stats_json')
    def _compute_stats_summary(self):
        """Convert JSON stats to HTML summary"""
        for record in self:
            if not record.stats_json:
                record.stats_summary = "<p>No diagnostics data available. Click 'Run Diagnostics' to generate.</p>"
                continue
                
            try:
                stats = json.loads(record.stats_json)
                html_parts = ["<div class='o_field_html'>"]
                
                # Appointments Summary
                if 'appointments' in stats:
                    appt_data = stats['appointments']
                    html_parts.append("<h3>📅 Appointments Overview</h3>")
                    html_parts.append(f"<p><strong>Total:</strong> {appt_data.get('total', 0)}</p>")
                    html_parts.append("<ul>")
                    for state, count in appt_data.get('by_state', {}).items():
                        html_parts.append(f"<li>{state.title()}: {count}</li>")
                    html_parts.append("</ul>")
                    
                    # Age buckets
                    if 'age_buckets' in appt_data:
                        html_parts.append("<h4>Age Distribution</h4>")
                        html_parts.append("<ul>")
                        for bucket, count in appt_data['age_buckets'].items():
                            html_parts.append(f"<li>{bucket}: {count}</li>")
                        html_parts.append("</ul>")
                
                # Issues
                if 'issues' in stats:
                    issues = stats['issues']
                    html_parts.append("<h3>⚠️ Data Issues</h3>")
                    if any(issues.values()):
                        html_parts.append("<ul>")
                        for issue_type, count in issues.items():
                            if count > 0:
                                html_parts.append(f"<li class='text-warning'>{issue_type.replace('_', ' ').title()}: {count}</li>")
                        html_parts.append("</ul>")
                    else:
                        html_parts.append("<p class='text-success'>✅ No data integrity issues found!</p>")
                
                # System Health
                if 'system' in stats:
                    system = stats['system']
                    html_parts.append("<h3>🔧 System Health</h3>")
                    html_parts.append("<ul>")
                    for metric, value in system.items():
                        html_parts.append(f"<li>{metric.replace('_', ' ').title()}: {value}</li>")
                    html_parts.append("</ul>")
                
                html_parts.append("</div>")
                record.stats_summary = ''.join(html_parts)
                
            except json.JSONDecodeError:
                record.stats_summary = "<p class='text-danger'>Error: Invalid JSON in statistics data</p>"

    def action_run_diagnostics(self):
        """Run comprehensive diagnostics and update stats"""
        self.ensure_one()
        
        _logger.info("Running maintenance diagnostics for company %s", self.company_id.name)
        
        stats = {
            'run_time': fields.Datetime.now().isoformat(),
            'company_id': self.company_id.id,
            'appointments': self._diagnose_appointments(),
            'barbers': self._diagnose_barbers(),
            'services': self._diagnose_services(),
            'wallets': self._diagnose_wallets(),
            'pos_data': self._diagnose_pos_data(),
            'issues': self._diagnose_issues(),
            'system': self._diagnose_system()
        }
        
        self.write({
            'stats_json': json.dumps(stats, indent=2),
            'last_run': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _diagnose_appointments(self):
        """Analyze appointment data"""
        domain = [('company_id', '=', self.company_id.id)]
        appointments = self.env['bp.barber.appointment'].search(domain)
        
        # Count by state
        by_state = {}
        for state in ['draft', 'confirmed', 'in_service', 'done', 'cancelled', 'no_show']:
            by_state[state] = self._count('bp.barber.appointment', domain + [('state', '=', state)])
        
        # Age buckets
        today = fields.Date.today()
        age_buckets = {
            'Last 30 days': self._count('bp.barber.appointment', 
                domain + [('start_datetime', '>=', today - timedelta(days=30))]),
            '31-180 days': self._count('bp.barber.appointment',
                domain + [
                    ('start_datetime', '<', today - timedelta(days=30)),
                    ('start_datetime', '>=', today - timedelta(days=180))
                ]),
            'Over 180 days': self._count('bp.barber.appointment',
                domain + [('start_datetime', '<', today - timedelta(days=180))])
        }
        
        return {
            'total': len(appointments),
            'by_state': by_state,
            'age_buckets': age_buckets
        }
    
    def _diagnose_barbers(self):
        """Analyze barber data"""
        domain = [('company_id', '=', self.company_id.id)]
        barbers = self.env['bp.barber.barber'].search(domain)
        
        # Barbers without chairs
        barbers_no_chair = self._count('bp.barber.barber', 
            domain + [('chair_ids', '=', False)])
        
        return {
            'total': len(barbers),
            'without_chairs': barbers_no_chair,
            'active': self._count('bp.barber.barber', domain + [('active', '=', True)])
        }
    
    def _diagnose_services(self):
        """Analyze service data"""
        domain = [('company_id', '=', self.company_id.id)]
        services = self.env['bp.barber.service'].search(domain)
        
        # Services without product links (should be rare after Stage 2)
        services_no_product = self._count('bp.barber.service',
            domain + [('product_id', '=', False)])
        
        return {
            'total': len(services),
            'without_products': services_no_product,
            'active': self._count('bp.barber.service', domain + [('active', '=', True)])
        }
    
    def _diagnose_wallets(self):
        """Analyze wallet data"""
        domain = [('company_id', '=', self.company_id.id)]
        wallets = self.env['bp.barber.package.wallet'].search(domain)
        
        # Expired wallets
        today = fields.Date.today()
        expired_wallets = self._count('bp.barber.package.wallet',
            domain + [('expiry_date', '<', today)])
        
        # Near expiry (7 days)
        near_expiry = self._count('bp.barber.package.wallet',
            domain + [
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', today + timedelta(days=7))
            ])
        
        return {
            'total': len(wallets),
            'expired': expired_wallets,
            'expiring_soon': near_expiry,
            'active': self._count('bp.barber.package.wallet', domain + [('active', '=', True)])
        }
    
    def _diagnose_pos_data(self):
        """Analyze POS integration data"""
        # POS lines without barber_id (informational)
        pos_lines_no_barber = 0
        try:
            pos_lines_no_barber = self._count('pos.order.line', [('barber_id', '=', False)])
        except Exception:
            pass  # POS extension may not be active
        
        return {
            'pos_lines_without_barber': pos_lines_no_barber
        }
    
    def _diagnose_issues(self):
        """Identify data integrity issues"""
        domain = [('company_id', '=', self.company_id.id)]
        
        issues = {
            'appointments_missing_barber': self._count('bp.barber.appointment',
                domain + [('barber_id', '=', False)]),
            'appointments_missing_services': self._count('bp.barber.appointment',
                domain + [('service_ids', '=', False)]),
            'appointments_missing_partner': self._count('bp.barber.appointment',
                domain + [('partner_id', '=', False)])
        }
        
        return issues
    
    def _diagnose_system(self):
        """System health metrics"""
        return {
            'database_size': 'Unknown',  # Could add pg_database_size query
            'total_companies': self._count('res.company', []),
            'active_users': self._count('res.users', [('active', '=', True)]),
            'maintenance_run': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _count(self, model_name, domain):
        """Helper to count records safely"""
        try:
            return self.env[model_name].search_count(domain)
        except Exception as e:
            _logger.warning("Error counting %s with domain %s: %s", model_name, domain, e)
            return 0
    
    def _age_buckets(self, records, date_field='start_datetime'):
        """Helper to categorize records by age"""
        today = fields.Date.today()
        buckets = {'recent': 0, 'medium': 0, 'old': 0}
        
        for record in records:
            date_val = getattr(record, date_field, None)
            if not date_val:
                continue
                
            if isinstance(date_val, datetime):
                date_val = date_val.date()
                
            age_days = (today - date_val).days
            
            if age_days <= 30:
                buckets['recent'] += 1
            elif age_days <= 180:
                buckets['medium'] += 1
            else:
                buckets['old'] += 1
                
        return buckets

    def export_csv(self, model_name, domain=None, fields=None):
        """Export model data as CSV"""
        if not domain:
            domain = []
        
        # Add company filter
        domain = domain + [('company_id', '=', self.company_id.id)]
        
        try:
            records = self.env[model_name].search(domain)
            
            if not fields:
                # Default field selection based on model
                if model_name == 'bp.barber.appointment':
                    fields = ['name', 'partner_id', 'barber_id', 'state', 'start_datetime']
                elif model_name == 'bp.barber.package.wallet':
                    fields = ['name', 'partner_id', 'package_id', 'purchase_date', 'expiry_date']
                else:
                    fields = ['name', 'create_date']
            
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(fields)
            
            # Data rows
            for record in records:
                row = []
                for field in fields:
                    try:
                        value = getattr(record, field, '')
                        if hasattr(value, 'name'):  # Many2one field
                            value = value.name
                        elif isinstance(value, (list, tuple)):  # One2many/Many2many
                            value = ', '.join([v.name for v in value if hasattr(v, 'name')])
                        row.append(str(value) if value else '')
                    except Exception:
                        row.append('')
                writer.writerow(row)
            
            # Encode as base64
            csv_data = output.getvalue().encode('utf-8')
            return base64.b64encode(csv_data).decode('utf-8')
            
        except Exception as e:
            _logger.error("Error exporting CSV for %s: %s", model_name, e)
            raise UserError(_("Error exporting CSV: %s") % str(e))

    @api.model
    def get_or_create_dashboard(self, company_id=None):
        """Get or create maintenance dashboard for company"""
        if not company_id:
            company_id = self.env.company.id
            
        dashboard = self.search([('company_id', '=', company_id)], limit=1)
        if not dashboard:
            dashboard = self.create({
                'company_id': company_id
            })
        
        return dashboard