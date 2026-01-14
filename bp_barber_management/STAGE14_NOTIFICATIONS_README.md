# Stage 14: Notifications & Reminders System

## Overview

The Barber Management Notifications & Reminders system provides comprehensive email communication for appointment lifecycle management. This system handles confirmation emails, automated reminders, no-show follow-ups, and tokenized appointment management through public links.

## Components Implemented

### 1. Core Models

#### Notification Settings (`models/notification_settings.py`)
- **Purpose**: Centralized configuration for all notification preferences
- **Features**:
  - Toggle confirmation emails on/off
  - Configure reminder timing (primary/secondary hours)
  - Enable/disable ICS calendar attachments
  - No-show follow-up settings
  - Input validation for reminder hours

#### Enhanced Appointment Model
- **New Fields**:
  - `appointment_token`: UUID-based security token
  - `email_opt_out`: Per-appointment email preference
  - `reminder_primary_sent`: Tracking flag
  - `reminder_secondary_sent`: Tracking flag
- **New Methods**:
  - `_build_ics_payload()`: Generate calendar invites
  - `_send_mail_template()`: Centralized email sending
  - `cron_send_reminders()`: Automated reminder processing

### 2. Email Templates (`data/mail_templates.xml`)

#### Appointment Confirmation Email
- **Template ID**: `bp_barber_appointment_confirmation_email`
- **Features**:
  - Responsive HTML design
  - Company branding integration
  - Appointment details display
  - Tokenized confirm/cancel links
  - Optional ICS calendar attachment

#### Primary Reminder Email
- **Template ID**: `bp_barber_appointment_reminder_primary_email`
- **Features**:
  - 24-hour default reminder (configurable)
  - Appointment preparation instructions
  - Easy reschedule/cancel options
  - Contact information

#### Secondary Reminder Email
- **Template ID**: `bp_barber_appointment_reminder_secondary_email`
- **Features**:
  - 2-hour default reminder (configurable)
  - Final reminder urgency
  - Last-minute change options
  - Direct contact details

#### No-Show Follow-up Email
- **Template ID**: `bp_barber_appointment_noshow_followup_email`
- **Features**:
  - Professional follow-up message
  - Rebooking encouragement
  - Customer service contact
  - Feedback collection

### 3. Automation (`data/ir_cron_barber_notifications.xml`)

#### Reminder Cron Job
- **Frequency**: Every 15 minutes
- **Function**: `cron_send_reminders()`
- **Logic**:
  - Finds confirmed appointments in reminder windows
  - Respects email opt-out preferences
  - Prevents duplicate reminder sends
  - Logs all notification activities

### 4. Public Portal (`controllers/notification_portal.py`)

#### Tokenized Endpoints
- **Test Route**: `/barber/apt/test`
- **Confirm Route**: `/barber/apt/<apt_name>/<token>/confirm`
- **Cancel Route**: `/barber/apt/<apt_name>/<token>/cancel`

#### Security Features
- UUID-based token validation
- Appointment state verification
- Error handling for invalid tokens
- Logging of all portal actions

### 5. Portal Templates (`views/notification_portal_templates.xml`)

#### Responsive Web Pages
- **Confirmed Page**: Success confirmation with details
- **Cancelled Page**: Cancellation confirmation with rebooking
- **Error Page**: User-friendly error handling

#### Design Features
- Bootstrap 5 responsive design
- Company branding consistency
- Clear call-to-action buttons
- Mobile-optimized layout

### 6. Settings Interface (`views/notification_settings_views.xml`)

#### Configuration Form
- **Location**: Settings > Barber Notifications
- **Sections**:
  - Email Notifications (confirmation, ICS)
  - Reminder Notifications (timing, enable/disable)
  - Follow-up Notifications (no-show)

## Configuration

### 1. Enable Notifications
1. Go to **Settings > Barber Notifications**
2. Enable desired notification types:
   - ✅ Send confirmation emails
   - ✅ Include calendar invites (ICS)
   - ✅ Send reminder emails
   - ✅ No-show follow-up emails

### 2. Configure Reminder Timing
- **Primary Reminder**: 24 hours before (default)
- **Secondary Reminder**: 2 hours before (default)
- Both values are customizable in settings

### 3. Email Templates Customization
Templates can be customized through:
- **Settings > Technical > Email Templates**
- Search for "Barber Appointment" templates
- Modify content, styling, or add custom fields

## Testing

### Comprehensive Test Suite (`tests/test_notifications.py`)

#### Unit Tests
- Notification settings validation
- Token generation and uniqueness
- ICS calendar file generation
- Email opt-out functionality
- Cron reminder logic

#### HTTP Tests
- Portal endpoint validation
- Token-based confirmation/cancellation
- Invalid token handling
- Appointment state restrictions

### Running Tests
```bash
# Syntax validation
python3 -m py_compile models/notification_settings.py
python3 -m py_compile controllers/notification_portal.py

# XML validation
xmllint --noout data/mail_templates.xml
xmllint --noout views/notification_settings_views.xml

# Full validation
./validate_stage14_notifications.sh
```

## Usage Workflow

### 1. Appointment Creation
1. Customer books appointment (web/POS/manual)
2. Appointment gets unique token generated
3. State remains 'draft' until confirmed

### 2. Appointment Confirmation
1. Staff confirms appointment
2. `action_confirm()` triggers notification
3. Confirmation email sent with tokenized links
4. ICS calendar invite attached (if enabled)

### 3. Automated Reminders
1. Cron job runs every 15 minutes
2. Finds appointments in reminder windows
3. Sends primary reminder (24h before)
4. Sends secondary reminder (2h before)
5. Updates tracking flags to prevent duplicates

### 4. Customer Portal Actions
1. Customer clicks confirm/cancel in email
2. Portal validates token and appointment
3. Updates appointment state accordingly
4. Shows confirmation page with next steps

### 5. No-Show Handling
1. Staff marks appointment as no-show
2. `action_no_show()` triggers follow-up
3. Follow-up email sent to customer
4. Activity created for staff follow-up

## Email Opt-Out Handling

### Per-Appointment Opt-Out
- Checkbox on appointment form
- Respected by all email functions
- Logs opt-out notifications instead

### Partner-Level Opt-Out
- Uses partner `email` field validation
- Prevents emails to invalid addresses
- Logs skipped notifications

## Security Considerations

### Token-Based Access
- UUID4 tokens (128-bit entropy)
- One-time use recommended
- No sensitive data in URLs
- Automatic token validation

### Portal Security
- No authentication required
- Limited to specific appointment actions
- State validation prevents misuse
- All actions logged for audit

## Troubleshooting

### Email Not Sending
1. Check notification settings enabled
2. Verify partner has valid email
3. Check email opt-out status
4. Review mail server configuration

### Reminders Not Working
1. Verify cron job is active
2. Check reminder hour settings
3. Confirm appointments are 'confirmed' state
4. Review tracking flags on appointments

### Portal Links Not Working
1. Verify token exists on appointment
2. Check URL format matches controller
3. Confirm appointment state allows action
4. Check server logs for errors

## Integration Points

### Mail System
- Uses Odoo's `mail.template` framework
- Integrates with `mail.mail` queue
- Supports attachments (ICS files)
- Activity logging through `mail.activity`

### Website Framework
- Portal controllers extend `http.Controller`
- QWeb templates for responsive design
- Bootstrap integration for styling
- Mobile-optimized user experience

### Cron System
- Uses `ir.cron` for automation
- Configurable frequency and timing
- Error handling and logging
- Safe for high-frequency execution

## Future Enhancements

### Potential Additions
1. **SMS Notifications**: Text message reminders
2. **Push Notifications**: Browser/mobile push
3. **Template Localization**: Multi-language support
4. **Advanced Scheduling**: Conditional reminder timing
5. **Analytics Dashboard**: Email performance metrics

### Extension Points
- Custom mail template inheritance
- Additional portal actions
- Webhook integrations
- Third-party notification services

## Performance Considerations

### Cron Optimization
- 15-minute intervals balance timeliness/load
- Window-based selection reduces queries
- Tracking flags prevent duplicate processing
- Batch processing for multiple appointments

### Email Queue Management
- Asynchronous sending through mail queue
- Error retry handling built-in
- Large attachment handling (ICS files)
- Delivery status tracking

## Compliance Notes

### Data Privacy
- Tokenized links minimize data exposure
- Email opt-out respects privacy preferences
- No personal data in URL parameters
- Audit trail for all communications

### Email Standards
- HTML emails with plain text fallback
- Responsive design for mobile devices
- Professional styling and branding
- Accessible content structure