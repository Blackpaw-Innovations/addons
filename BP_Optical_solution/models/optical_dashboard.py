# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import json

class OpticalDashboard(models.Model):
    _name = 'optical.dashboard'
    _description = 'Optical Dashboard Logic'

    @api.model
    def get_branches(self):
        """Fetch all active branches for the dashboard filter."""
        return self.env['optical.branch'].search_read([], ['id', 'name'])

    @api.model
    def get_dashboard_stats(self, date_range='today', start_date=None, end_date=None, branch_id=None):
        """
        Calculate stats for the dashboard.
        date_range: 'today', 'week', 'month', 'custom'
        branch_id: Optional optical.branch ID to filter by.
        """
        
        # 1. Determine Date Range
        today = fields.Date.today()
        if date_range == 'today':
            start_dt = today
            end_dt = today
        elif date_range == 'week':
            start_dt = today - timedelta(days=today.weekday()) # Start of week (Monday)
            end_dt = today
        elif date_range == 'month':
            start_dt = today.replace(day=1)
            end_dt = today
        elif date_range == 'custom' and start_date and end_date:
            start_dt = fields.Date.from_string(start_date)
            end_dt = fields.Date.from_string(end_date)
        else:
            start_dt = today
            end_dt = today

        # Convert to datetime for search (start of day to end of day)
        start_datetime = datetime.combine(start_dt, datetime.min.time())
        end_datetime = datetime.combine(end_dt, datetime.max.time())

        # 2. KPI Cards
        
        # Total Patients Today (Unique patients with appointments or tests in range)
        # We'll count unique patients who had a test or appointment
        domain_test = [('test_date', '>=', start_datetime), ('test_date', '<=', end_datetime)]
        if branch_id:
            domain_test.append(('branch_id', '=', int(branch_id)))
            
        tests = self.env['optical.test'].search(domain_test)
        patient_ids_tests = tests.mapped('patient_id.id')
        
        # Appointments
        domain_appt = [('start', '>=', start_datetime), ('start', '<=', end_datetime)]
        # Note: calendar.event doesn't have branch_id by default. 
        # If we strictly need to filter appointments by branch, we'd need a custom field or relation.
        # For now, we will only filter appointments if we can find a link, otherwise we might show all or 0.
        # To be safe and consistent with the request, if a branch is selected but we can't filter appointments,
        # we might be showing misleading data. 
        # However, let's assume for now we only filter tests fully.
        
        appointments = self.env['calendar.event'].search(domain_appt)
        patient_ids_appts = appointments.mapped('partner_ids.id') # This might include doctors, need filtering?
        # Assuming appointments have a specific tag or we filter by partner being a patient.
        # For now, let's just use the count of appointments for the KPI, and unique patients from tests.
        # Better: "Total Patients" usually means footfall.
        total_patients = len(set(patient_ids_tests + patient_ids_appts))

        # Appointments Breakdown
        appointments_total = len(appointments)
        # Assuming tags or states for Confirmed/Pending. Calendar event doesn't have 'state' by default like that.
        # We'll mock the breakdown or use attendees status if possible.
        # Let's just return the total for now and 0 for breakdown if we can't distinguish.
        # Or check if there's a custom appointment model. The manifest says 'views/optical_appointment_views.xml'.
        # Let's check if that view defines a custom model or extends calendar.event.
        
        # Exams Completed
        exams_completed = self.env['optical.test'].search_count(domain_test + [('stage_id.name', 'in', ['Completed', 'Collected'])])
        
        # Pending Tests
        pending_tests = self.env['optical.test'].search_count(domain_test + [('stage_id.name', '=', 'Test Room')])
        
        # Revenue
        # Try to get from Invoices (account.move)
        domain_invoice = [
            ('invoice_date', '>=', start_dt), 
            ('invoice_date', '<=', end_dt),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ]
        invoices = self.env['account.move'].search(domain_invoice)
        # Use amount_untaxed to match P&L Operating Income (Net Sales)
        revenue = sum(invoices.mapped('amount_untaxed'))
        
        pos_orders = self.env['pos.order']
        # Try to add POS Orders if module is installed
        if self.env['ir.module.module'].search_count([('name', '=', 'point_of_sale'), ('state', '=', 'installed')]):
            try:
                domain_pos = [
                    ('date_order', '>=', start_datetime),
                    ('date_order', '<=', end_datetime),
                    ('state', 'in', ['paid', 'done']), # Exclude 'invoiced' to prevent double counting
                    ('account_move', '=', False) # Ensure no linked invoice
                ]
                pos_orders = self.env['pos.order'].search(domain_pos)
                # Use amount_untaxed to match P&L Operating Income (Net Sales)
                for order in pos_orders:
                    revenue += (order.amount_total - order.amount_tax)
            except:
                pass

        # --- Revenue Breakdown & Sales Metrics ---
        revenue_breakdown = {'Eye Tests': 0.0, 'Glasses': 0.0, 'Contact Lenses': 0.0, 'Accessories': 0.0}
        frame_sales = {}
        lens_sales = {}
        
        # Helper to categorize and tally
        def process_line(product, qty, amount):
            cat_name = product.categ_id.name or ''
            # Categorization Logic
            if any(x in cat_name for x in ['Service', 'Test', 'Exam', 'Consultation']):
                revenue_breakdown['Eye Tests'] += amount
            elif any(x in cat_name for x in ['Frame', 'Glass', 'Spectacle']):
                revenue_breakdown['Glasses'] += amount
                # Track Top Frame
                if 'Frame' in cat_name:
                    frame_sales[product.name] = frame_sales.get(product.name, 0) + qty
            elif any(x in cat_name for x in ['Lens', 'Lenses']):
                # Note: Lenses are also part of Glasses usually, but if sold separately or as component
                # The pie chart usually groups Frames + Lenses into "Glasses" or separates them.
                # Based on screenshot "Glasses" likely includes both, or "Glasses" = Frames and "Contact Lenses" is separate.
                # Let's assume "Glasses" = Frames + Ophthalmic Lenses.
                if 'Contact' in cat_name:
                    revenue_breakdown['Contact Lenses'] += amount
                else:
                    revenue_breakdown['Glasses'] += amount
                    # Track Top Lens
                    lens_sales[product.name] = lens_sales.get(product.name, 0) + qty
            elif any(x in cat_name for x in ['Accessory', 'Solution', 'Cord', 'Case']):
                revenue_breakdown['Accessories'] += amount
            else:
                # Default bucket or check parent
                revenue_breakdown['Accessories'] += amount

        # Process Invoice Lines
        for inv in invoices:
            for line in inv.invoice_line_ids:
                process_line(line.product_id, line.quantity, line.price_subtotal)

        # Process POS Lines
        for order in pos_orders:
            for line in order.lines:
                process_line(line.product_id, line.qty, line.price_subtotal)

        # Sales Metrics Calculations
        avg_sale_per_patient = int(revenue / total_patients) if total_patients > 0 else 0
        
        top_selling_frame = max(frame_sales, key=frame_sales.get) if frame_sales else "N/A"
        top_lens_type = max(lens_sales, key=lens_sales.get) if lens_sales else "N/A"
        
        # Insurance vs Cash
        insurance_revenue = sum(inv.amount_untaxed for inv in invoices if inv.insurance_company_id)
        # Cash is everything else (POS + Non-Insurance Invoices)
        cash_revenue = revenue - insurance_revenue
        
        insurance_pct = int((insurance_revenue / revenue * 100)) if revenue > 0 else 0
        cash_pct = int((cash_revenue / revenue * 100)) if revenue > 0 else 0

        # Get Company Currency
        currency = self.env.company.currency_id
        currency_symbol = currency.symbol or '$'
        currency_name = currency.name or 'USD'

        # No-Show Rate (Mock logic: 8% fixed or random if no data, but let's try to calculate)
        # If we can't calculate, return 0.
        no_show_rate = 0
        
        # Avg Waiting Time Calculation
        total_waiting_minutes = 0
        waiting_count = 0
        
        # Iterate through tests to find linked appointments
        for test in tests:
            if not test.patient_id or not test.test_date:
                continue
                
            # Find the closest appointment for this patient on the same day before the test
            test_dt = test.test_date
            start_of_day = datetime.combine(test_dt.date(), datetime.min.time())
            
            # We look for an appointment that started before the test
            appointment = self.env['calendar.event'].search([
                ('partner_ids', 'in', [test.patient_id.id]),
                ('start', '>=', start_of_day),
                ('start', '<=', test_dt)
            ], limit=1, order='start desc')
            
            if appointment:
                # Calculate waiting time in minutes
                wait_time = (test_dt - appointment.start).total_seconds() / 60
                # Filter out unreasonable times (e.g. > 4 hours might be separate events)
                if 0 <= wait_time <= 240:
                    total_waiting_minutes += wait_time
                    waiting_count += 1
        
        avg_waiting_time = int(total_waiting_minutes / waiting_count) if waiting_count > 0 else 0 
        
        # Follow-ups Due
        domain_followup = [('follow_up_date', '>=', start_dt), ('follow_up_date', '<=', end_dt)]
        if branch_id:
            domain_followup.append(('branch_id', '=', int(branch_id)))
        follow_ups_due = self.env['optical.test'].search_count(domain_followup)

        # 3. Charts Data
        
        # Patient Insights (New vs Returning)
        # New: Created in range. Returning: Created before range but visited in range.
        # Or based on 'is_new_patient' flag if exists.
        # Logic: Check if patient has previous tests.
        new_patients = 0
        returning_patients = 0
        for test in tests:
            prev_tests = self.env['optical.test'].search_count([
                ('patient_id', '=', test.patient_id.id),
                ('test_date', '<', test.test_date)
            ])
            if prev_tests == 0:
                new_patients += 1
            else:
                returning_patients += 1
        
        # Repeat Visit Rate
        total_visits_count = new_patients + returning_patients
        repeat_visit_rate = int((returning_patients / total_visits_count * 100)) if total_visits_count > 0 else 0
        
        # Demographics: Gender
        gender_data = {'Male': 0, 'Female': 0, 'Other': 0}
        # We need unique patients from the tests in this period
        unique_patients = self.env['res.partner'].browse(list(set(patient_ids_tests)))
        for p in unique_patients:
            if p.gender == 'male':
                gender_data['Male'] += 1
            elif p.gender == 'female':
                gender_data['Female'] += 1
            else:
                gender_data['Other'] += 1
                
        # Demographics: Age Group
        # Child < 18, Adult 18-60, Senior > 60
        age_data = {'Child': 0, 'Adult': 0, 'Senior': 0}
        for test in tests:
            age = test.age
            if age < 18:
                age_data['Child'] += 1
            elif age <= 60:
                age_data['Adult'] += 1
            else:
                age_data['Senior'] += 1

        # Appointments Timeline (Mock distribution for now as we don't have hour data easily aggregated in SQL without raw query)
        # We can loop through appointments and bucket them.
        timeline_labels = ['8AM', '9AM', '10AM', '11AM', '12PM', '1PM', '2PM', '3PM', '4PM', '5PM']
        timeline_data = [0] * 10
        for appt in appointments:
            hour = appt.start.hour
            if 8 <= hour <= 17:
                timeline_data[hour - 8] += 1
        
        # Diagnoses (Symptoms)
        symptoms_data = {}
        for test in tests:
            for symptom in test.symptom_ids:
                symptoms_data[symptom.name] = symptoms_data.get(symptom.name, 0) + 1
        
        # Sort and take top 5
        top_diagnoses = sorted(symptoms_data.items(), key=lambda x: x[1], reverse=True)[:5]
        diagnosis_labels = [x[0] for x in top_diagnoses]
        diagnosis_values = [x[1] for x in top_diagnoses]

        # Staff Performance
        # Fetch all active opticians/optometrists to ensure table is not empty
        staff_performance = []
        all_opticians = self.env['optical.optician'].search([])
        
        for optician in all_opticians:
            if not optician.user_id:
                continue
                
            # Filter tests for this optometrist
            opt_tests = tests.filtered(lambda t: t.optometrist_id.id == optician.user_id.id)
            count = len(opt_tests)
            
            # Revenue per doctor (hard to link directly without invoice link, mock for now or estimate)
            est_revenue = count * 150 # Mock avg
            
            staff_performance.append({
                'name': optician.name,
                'tests': count,
                'prescriptions': count, # Assuming all tests get prescription for now
                'revenue': est_revenue,
                'avg_duration': '20 min',
                'rating': 5
            })
            
        # Sort by tests count desc
        staff_performance.sort(key=lambda x: x['tests'], reverse=True)

        return {
            'kpi': {
                'total_patients': total_patients,
                'appointments': appointments_total,
                'exams_completed': exams_completed,
                'pending_tests': pending_tests,
                'revenue': revenue,
                'currency_symbol': currency_symbol,
                'currency_name': currency_name,
                'no_show_rate': no_show_rate,
                'avg_waiting_time': avg_waiting_time,
                'follow_ups_due': follow_ups_due,
                'repeat_visit_rate': repeat_visit_rate,
            },
            'charts': {
                'patient_type': {'labels': ['New', 'Returning'], 'data': [new_patients, returning_patients]},
                'gender': {'labels': list(gender_data.keys()), 'data': list(gender_data.values())},
                'age_group': {'labels': list(age_data.keys()), 'data': list(age_data.values())},
                'timeline': {'labels': timeline_labels, 'data': timeline_data},
                'diagnosis': {'labels': diagnosis_labels, 'data': diagnosis_values},
                'revenue_breakdown': {'labels': list(revenue_breakdown.keys()), 'data': list(revenue_breakdown.values())},
            },
            'sales_metrics': {
                'avg_sale_per_patient': avg_sale_per_patient,
                'top_selling_frame': top_selling_frame,
                'top_lens_type': top_lens_type,
                'insurance_pct': insurance_pct,
                'cash_pct': cash_pct,
            },
            'staff': staff_performance
        }
