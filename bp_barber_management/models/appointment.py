# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import uuid
import logging

_logger = logging.getLogger(__name__)


class BarberAppointment(models.Model):
    _name = 'bp.barber.appointment'
    _description = 'Barber Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc, id desc'

    name = fields.Char(
        string='Appointment Number',
        required=True,
        readonly=True,
        copy=False,
        default='New'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_service', 'In Service'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], string='State', default='draft', tracking=True)
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        help="Customer"
    )
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    
    barber_id = fields.Many2one(
        'bp.barber.barber',
        string='Barber',
        index=True,
        tracking=True
    )
    chair_id = fields.Many2one(
        'bp.barber.chair',
        string='Chair',
        compute='_compute_chair_id',
        inverse='_inverse_chair_id',
        store=True
    )
    
    service_ids = fields.Many2many(
        'bp.barber.service',
        string='Services',
        required=True
    )
    
    duration_minutes = fields.Integer(
        string='Duration (Minutes)',
        compute='_compute_duration_minutes',
        store=True
    )
    
    start_datetime = fields.Datetime(
        string='Start Time',
        index=True
    )
    end_datetime = fields.Datetime(
        string='End Time',
        compute='_compute_end_datetime',
        store=True
    )
    
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_price_subtotal',
        store=True
    )
    discount_percent = fields.Float(
        string='Discount (%)',
        default=0.0
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_price_total',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True
    )
    
    note = fields.Html(string='Notes')
    active = fields.Boolean(string='Active', default=True)
    
    # Notification fields (Stage 14)
    email_opt_out = fields.Boolean(
        string='Email Opt-out',
        default=False,
        help='Customer opted out of email notifications'
    )
    reminder_primary_sent = fields.Boolean(
        string='Primary Reminder Sent',
        default=False,
        help='Primary reminder email has been sent'
    )
    reminder_secondary_sent = fields.Boolean(
        string='Secondary Reminder Sent', 
        default=False,
        help='Secondary reminder email has been sent'
    )
    appointment_token = fields.Char(
        string='Appointment Token',
        index=True,
        copy=False,
        help='Token for public confirmation/cancellation links'
    )
    
    # POS Integration (Stage 6)
    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        ondelete='set null',
        help="POS order that completed this appointment"
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('bp_barber.sequence_appointment') or 'New'
        
        # Generate appointment token if not provided
        if not vals.get('appointment_token'):
            vals['appointment_token'] = uuid.uuid4().hex
        
        # Set duration_minutes if not provided and service_ids are given
        if 'service_ids' in vals and not vals.get('duration_minutes'):
            service_ids = []
            if vals['service_ids']:
                for cmd in vals['service_ids']:
                    if cmd[0] == 6:  # (6, 0, ids) format
                        service_ids.extend(cmd[2])
                    elif cmd[0] == 4:  # (4, id) format
                        service_ids.append(cmd[1])
                
                if service_ids:
                    services = self.env['bp.barber.service'].browse(service_ids)
                    vals['duration_minutes'] = sum(services.mapped('duration_minutes')) or 30
        
        # Set default values for computed fields
        if not vals.get('price_subtotal'):
            vals['price_subtotal'] = 0.0
        if not vals.get('price_total'):
            vals['price_total'] = 0.0
        
        # Calculate end_datetime if start_datetime and duration_minutes are provided
        if vals.get('start_datetime') and vals.get('duration_minutes'):
            from datetime import datetime, timedelta
            start_dt = vals['start_datetime']
            if isinstance(start_dt, str):
                start_dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
            vals['end_datetime'] = start_dt + timedelta(minutes=vals['duration_minutes'])
            
        return super().create(vals)

    # @api.depends('barber_id', 'barber_id.chair_id')
    def _compute_chair_id(self):
        """Auto-set chair from barber's default chair - DISABLED to prevent _unknown object errors"""
        for appointment in self:
            appointment.chair_id = False
            
    def _inverse_chair_id(self):
        # Allow manual chair assignment even if different from barber's default
        pass

    # @api.depends('service_ids', 'service_ids.duration_minutes')
    def _compute_duration_minutes(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.duration_minutes = 0 or 0

    # @api.depends('start_datetime', 'duration_minutes')
    def _compute_end_datetime(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.end_datetime = False

    # @api.depends('service_ids', 'service_ids.list_price')
    def _compute_price_subtotal(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.price_subtotal = 0.0

    # @api.depends('price_subtotal', 'discount_percent')
    def _compute_price_total(self):
        """DISABLED to prevent _unknown object errors"""
        for record in self:
            record.price_total = 0.0    # Temporarily disabled to fix _unknown object error
    # @api.onchange('barber_id')
    # def _onchange_barber_id(self):
    #     if self.barber_id:
    #         try:
    #             # Safely check if barber has a valid chair
    #             if self.barber_id.chair_id and self.barber_id.chair_id.id:
    #                 self.chair_id = self.barber_id.chair_id
    #             else:
    #                 self.chair_id = False
    #         except:
    #             # If there's any error accessing the chair, clear the field
    #             self.chair_id = False
    pass

    def write(self, vals):
        # Block modifications when state is 'done' except chatter/activity fields
        if any(record.state == 'done' for record in self):
            protected_fields = set(vals.keys()) - {
                'message_follower_ids', 'message_ids', 'activity_ids',
                'message_main_attachment_id', 'website_message_ids'
            }
            if protected_fields:
                raise UserError(_("Done appointments are locked and cannot be modified."))
        return super().write(vals)

    def action_confirm(self):
        """Confirm the appointment"""
        for record in self:
            if not record.start_datetime:
                raise UserError(_("Start time is required to confirm appointment."))
            if not record.barber_id:
                raise UserError(_("Barber is required to confirm appointment."))
            record.state = 'confirmed'
            
            # Send confirmation email if enabled
            notification_service = record.env['bp.barber.notification.service']
            settings = notification_service.get_notification_settings()
            
            if settings['notify_on_confirm'] and record.partner_id and record.partner_id.email and not record.email_opt_out:
                # Prepare ICS attachment if enabled
                attachments = None
                if settings['send_ics']:
                    ics_content = record._build_ics_payload()
                    if ics_content:
                        attachments = [(
                            f'appointment_{record.name}.ics',
                            ics_content,
                            'text/calendar'
                        )]
                
                record._send_mail_template('bp_barber_management.mail_tmpl_appt_confirm', attachments)

    def action_start_service(self):
        """Start the service"""
        for record in self:
            record.state = 'in_service'

    def action_finish_service(self):
        """Finish the service and lock the record"""
        for record in self:
            record.state = 'done'
            
            # Try to redeem from packages if no POS order and customer has packages (Stage 10)
            if record.partner_id and not record.pos_order_id:
                record._try_package_redemption()
            
            # Log consumable usage from appointment services (Stage 11)
            if record.barber_id and record.service_ids:
                try:
                    usage = self.env['bp.barber.consumable.usage'].create_from_services(
                        self.env, record.barber_id, record.service_ids, 'appointment', record
                    )
                    if usage:
                        # Post usage summary to appointment
                        usage_summary = []
                        for line in usage.line_ids:
                            usage_summary.append(f"• {line.product_id.name}: {line.qty} {line.uom_id.name}")
                        
                        if usage_summary:
                            message = "Consumables used:\n" + "\n".join(usage_summary)
                            record.message_post(
                                body=message,
                                subject="Consumable Usage",
                                message_type='comment'
                            )
                except Exception as e:
                    # Log error but don't block the finish operation
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(
                        "Failed to create consumable usage for appointment %s: %s",
                        record.name, str(e)
                    )
            
            # Commission creation removed

    def action_cancel(self):
        """Cancel the appointment"""
        for record in self:
            record.state = 'cancelled'

    def action_no_show(self):
        """Mark as no-show and create follow-up activity"""
        for record in self:
            record.state = 'no_show'
            
            # Send follow-up email if enabled
            notification_service = record.env['bp.barber.notification.service']
            settings = notification_service.get_notification_settings()
            
            if settings['followup_noshow'] and record.partner_id and record.partner_id.email and not record.email_opt_out:
                record._send_mail_template('bp_barber_management.mail_tmpl_appt_noshow_followup')
            
            # Create follow-up activity
            if record.partner_id:
                # Try to assign to barber manager or leave unassigned
                manager_user = None
                try:
                    manager_group = record.env.ref('bp_barber_management.group_bp_barber_manager')
                    if manager_group and manager_group.users:
                        manager_user = manager_group.users[0]
                except:
                    pass
                    
                record.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f'Follow up on no-show: {record.partner_id.name}',
                    note=f'Customer did not show up for appointment {record.name}. Consider following up to reschedule.',
                    user_id=manager_user.id if manager_user else record.env.user.id,
                    date_deadline=fields.Date.today()
                )

    @api.model
    def get_available_slots(self, barber_id, date_str, duration_minutes, tz=None):
        """
        Get available time slots for a barber on a specific date
        
        :param barber_id: ID of the barber
        :param date_str: Date in YYYY-MM-DD format
        :param duration_minutes: Required duration in minutes
        :param tz: Timezone (optional)
        :return: List of available slots with start/end datetime
        """
        from datetime import datetime, timedelta
        import pytz
        
        # Parse the date
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return []
        
        # Get the barber
        barber = self.env['bp.barber.barber'].browse(barber_id)
        if not barber.exists():
            return []
        
        # Get weekday (0=Monday, 6=Sunday)
        weekday = str(booking_date.weekday())
        
        # Find the barber's schedule for this weekday
        schedule = self.env['bp.barber.schedule'].search([
            ('barber_id', '=', barber_id),
            ('weekday', '=', weekday),
            ('active', '=', True)
        ], limit=1)
        
        if not schedule:
            return []
        
        # Convert working hours to datetime
        start_hour = int(schedule.start_time)
        start_minute = int((schedule.start_time % 1) * 60)
        end_hour = int(schedule.end_time)
        end_minute = int((schedule.end_time % 1) * 60)
        
        work_start = datetime.combine(booking_date, datetime.min.time().replace(
            hour=start_hour, minute=start_minute))
        work_end = datetime.combine(booking_date, datetime.min.time().replace(
            hour=end_hour, minute=end_minute))
        
        # Get existing appointments for this barber on this date
        existing_appointments = self.search([
            ('barber_id', '=', barber_id),
            ('start_datetime', '>=', work_start),
            ('start_datetime', '<', work_start + timedelta(days=1)),
            ('state', 'in', ['confirmed', 'in_service'])
        ])
        
        # Generate 15-minute slots
        slots = []
        current_time = work_start
        slot_duration = timedelta(minutes=15)  # 15-minute intervals
        required_duration = timedelta(minutes=duration_minutes)
        buffer_time = timedelta(minutes=5)  # 5-minute buffer between appointments
        
        while current_time + required_duration <= work_end:
            slot_end = current_time + required_duration
            
            # Check if this slot conflicts with existing appointments
            conflict = False
            for appointment in existing_appointments:
                apt_start = appointment.start_datetime
                apt_end = appointment.end_datetime or (apt_start + timedelta(minutes=appointment.duration_minutes))
                
                # Add buffer time to existing appointments
                apt_start_buffered = apt_start - buffer_time
                apt_end_buffered = apt_end + buffer_time
                
                # Check for overlap
                if (current_time < apt_end_buffered and slot_end > apt_start_buffered):
                    conflict = True
                    break
            
            if not conflict:
                slots.append({
                    'start': current_time,
                    'end': slot_end
                })
            
            current_time += slot_duration
        
        return slots
    
    def _try_package_redemption(self):
        """Try to redeem services from customer's package wallets - DISABLED"""
        return  # Package functionality removed
        
        # if not self.partner_id:
        #     return
        
        # # Find active, non-expired wallets for this customer
        # wallets = self.env['bp.barber.package.wallet'].search([
        #     ('partner_id', '=', self.partner_id.id),
        #     ('active', '=', True),
        #     ('company_id', '=', self.company_id.id)
        # ])
        
        # Package functionality removed - early return
        return
        
        redemption_messages = []
        total_value_redeemed = 0.0
        
        # Try to redeem each service
        for service in self.service_ids:
            service_redeemed = False
            
            # First try quantity/bundle wallets (FIFO - oldest first)
            qty_wallets = available_wallets.filtered(
                lambda w: w.package_type in ('qty', 'bundle')
            ).sorted('purchase_date')
            
            for wallet in qty_wallets:
                available_units = wallet.get_available_units(service)
                if available_units >= 1.0:
                    try:
                        # Consume 1 unit
                        wallet.consume_units(service, 1.0, self, f"Appointment {self.name}")
                        
                        # Create redemption record
                        self.env['bp.barber.package.redemption'].create({
                            'wallet_id': wallet.id,
                            'partner_id': self.partner_id.id,
                            'origin_type': 'appointment',
                            'service_id': service.id,
                            'qty': 1.0,
                            'appointment_id': self.id,
                            'date': fields.Datetime.now(),
                        })
                        
                        redemption_messages.append(f"✓ {service.name} (1 unit from {wallet.package_id.name})")
                        service_redeemed = True
                        break
                        
                    except UserError:
                        continue  # Try next wallet
        
        # Try value wallets for any remaining unpaid services
        if not service_redeemed:
            value_wallets = available_wallets.filtered(
                lambda w: w.package_type == 'value' and w.balance_amount > 0
            ).sorted('purchase_date')
            
            # Calculate total service value
            total_service_value = sum(service.list_price for service in self.service_ids)
            
            for wallet in value_wallets:
                available_amount = wallet.balance_amount
                amount_to_redeem = min(available_amount, total_service_value - total_value_redeemed)
                
                if amount_to_redeem > 0:
                    try:
                        # Consume value
                        wallet.consume_value(amount_to_redeem, self, f"Appointment {self.name}")
                        
                        # Create redemption record
                        self.env['bp.barber.package.redemption'].create({
                            'wallet_id': wallet.id,
                            'partner_id': self.partner_id.id,
                            'origin_type': 'appointment',
                            'amount': amount_to_redeem,
                            'appointment_id': self.id,
                            'date': fields.Datetime.now(),
                        })
                        
                        total_value_redeemed += amount_to_redeem
                        redemption_messages.append(
                            f"✓ {self.currency_id.symbol}{amount_to_redeem:,.2f} credit from {wallet.package_id.name}"
                        )
                        
                        if total_value_redeemed >= total_service_value:
                            break
                            
                    except UserError:
                        continue  # Try next wallet
        
        # Post redemption summary message
        if redemption_messages:
            message = "Package redemptions applied:\n" + "\n".join(redemption_messages)
            self.message_post(body=message, message_type='comment')

    def action_view_partner_wallets(self):
        """Smart button action to view customer's package wallets"""
        if not self.partner_id:
            return
        
        return {
            'name': _('Customer Wallets'),
            'type': 'ir.actions.act_window',
            'res_model': 'bp.barber.package.wallet',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id}
        }

    def action_print_visit_summary(self):
        """Generate and return visit summary report"""
        self.ensure_one()
        return self.env.ref('bp_barber_management.action_report_bp_appointment_visit').report_action(self)

    # ========== NOTIFICATION METHODS (Stage 14) ==========
    
    def _build_ics_payload(self):
        """Generate ICS calendar file content"""
        self.ensure_one()
        
        if not self.start_datetime or not self.end_datetime:
            return None
            
        # Convert to UTC
        start_utc = self.start_datetime.strftime('%Y%m%dT%H%M%SZ')
        end_utc = self.end_datetime.strftime('%Y%m%dT%H%M%SZ')
        now_utc = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        
        # Build service summary
        services = ', '.join(self.service_ids.mapped('name'))
        summary = f"Barber Appointment: {services}"
        
        # Company location
        location = self.company_id.name or "Barber Shop"
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Odoo//Barber Management//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{self.appointment_token}@{self.company_id.name.replace(' ', '').lower()}.com
DTSTAMP:{now_utc}
DTSTART:{start_utc}
DTEND:{end_utc}
SUMMARY:{summary}
DESCRIPTION:Appointment {self.name} with {self.barber_id.name}\\nServices: {services}
LOCATION:{location}
ORGANIZER:mailto:{self.company_id.email or 'noreply@barbershop.com'}
ATTENDEE:mailto:{self.partner_id.email if self.partner_id else ''}
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""
        
        return ics_content.encode('utf-8')

    def _send_mail_template(self, template_xmlid, attachments=None):
        """Send templated email with optional attachments"""
        self.ensure_one()
        
        # Check if customer has email and hasn't opted out
        if not self.partner_id or not self.partner_id.email or self.email_opt_out:
            self.message_post(
                body=f"Email notification skipped - no email address or opted out",
                message_type='comment'
            )
            return False
            
        try:
            template = self.env.ref(template_xmlid)
            if not template:
                _logger.error(f"Email template {template_xmlid} not found")
                return False
                
            # Prepare email values
            email_values = {}
            if attachments:
                email_values['attachments'] = attachments
                
            # Send email
            template.send_mail(
                self.id,
                force_send=True,
                email_values=email_values,
                notif_layout='mail.mail_notification_light'
            )
            
            self.message_post(
                body=f"Email sent using template: {template.name}",
                message_type='comment'
            )
            return True
            
        except Exception as e:
            _logger.error(f"Failed to send email template {template_xmlid}: {e}")
            self.message_post(
                body=f"Failed to send email: {str(e)}",
                message_type='comment'
            )
            return False

    @api.model
    def cron_send_reminders(self):
        """Cron job to send appointment reminders"""
        notification_service = self.env['bp.barber.notification.service']
        settings = notification_service.get_notification_settings()
        
        if not settings['reminder_enabled']:
            return
            
        now = datetime.utcnow()
        
        # Primary reminder window
        primary_hours = settings['reminder_hours_primary']
        primary_start = now + timedelta(hours=primary_hours - 0.25)  # 15 min before
        primary_end = now + timedelta(hours=primary_hours + 0.25)    # 15 min after
        
        # Find appointments for primary reminder
        primary_appointments = self.search([
            ('state', '=', 'confirmed'),
            ('start_datetime', '>=', primary_start),
            ('start_datetime', '<=', primary_end),
            ('reminder_primary_sent', '=', False),
            ('partner_id', '!=', False),
            ('email_opt_out', '=', False)
        ])
        
        for appointment in primary_appointments:
            if appointment.partner_id.email:
                if appointment._send_mail_template('bp_barber_management.mail_tmpl_appt_reminder'):
                    appointment.reminder_primary_sent = True
                    
        # Secondary reminder (if enabled)
        secondary_hours = settings['reminder_hours_secondary']
        if secondary_hours > 0:
            secondary_start = now + timedelta(hours=secondary_hours - 0.25)
            secondary_end = now + timedelta(hours=secondary_hours + 0.25)
            
            secondary_appointments = self.search([
                ('state', '=', 'confirmed'),
                ('start_datetime', '>=', secondary_start),
                ('start_datetime', '<=', secondary_end),
                ('reminder_secondary_sent', '=', False),
                ('partner_id', '!=', False),
                ('email_opt_out', '=', False)
            ])
            
            for appointment in secondary_appointments:
                if appointment.partner_id.email:
                    if appointment._send_mail_template('bp_barber_management.mail_tmpl_appt_reminder'):
                        appointment.reminder_secondary_sent = True
                        
        _logger.info(f"Sent {len(primary_appointments)} primary and {len(secondary_appointments) if secondary_hours > 0 else 0} secondary reminders")