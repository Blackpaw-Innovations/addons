# -*- coding: utf-8 -*-

from odoo.tests.common import tagged, TransactionCase
from datetime import datetime, timedelta


@tagged('post_install', '-at_install')
class TestBookingSlotsEngine(TransactionCase):
    """Test the appointment slot generation engine from Stage 5"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Get demo barber with schedule
        cls.barber_mary = cls.env.ref('bp_barber_management.bp_barber_mary')
        cls.service_cut = cls.env.ref('bp_barber_management.bp_service_cut')
        
        # Create test customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Slot Test Customer',
            'phone': '+1-555-SLOT'
        })

    def test_available_slots_for_scheduled_barber(self):
        """Test slot generation for Mary who has Mon-Sat 09:00-18:00 schedule"""
        
        # Get a weekday for testing (Monday = 0)
        test_date = self._get_next_weekday(0)  # Next Monday
        
        # Request 30-minute slots for haircut service
        slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=30
        )
        
        # Should return non-empty slots since Mary works Mon-Sat 09:00-18:00
        self.assertGreater(len(slots), 0, "Should have available slots for scheduled day")
        
        # Verify slots are within working hours
        for slot in slots:
            slot_hour = slot['start'].hour
            self.assertGreaterEqual(slot_hour, 9, "Slots should start at or after 09:00")
            self.assertLessEqual(slot['end'].hour, 18, "Slots should end by 18:00")
            
            # Verify slot duration
            duration = slot['end'] - slot['start']
            self.assertEqual(duration.total_seconds() / 60, 30, "Slot should be 30 minutes")

    def test_no_slots_on_unscheduled_day(self):
        """Test that no slots are returned for Sunday (unscheduled day)"""
        
        # Get next Sunday (weekday = 6)
        test_date = self._get_next_weekday(6)
        
        # Request slots for Sunday
        slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=30
        )
        
        # Should be empty since Mary doesn't work Sundays
        self.assertEqual(len(slots), 0, "Should have no slots on unscheduled Sunday")

    def test_slot_conflicts_with_existing_appointments(self):
        """Test that slots are excluded when conflicting with existing appointments"""
        
        # Get next Monday for consistent testing
        test_date = self._get_next_weekday(0)
        conflict_time = test_date.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Get initial available slots
        initial_slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=30
        )
        
        initial_count = len(initial_slots)
        self.assertGreater(initial_count, 0, "Should have initial slots available")
        
        # Create conflicting confirmed appointment
        conflict_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'barber_id': self.barber_mary.id,
            'start_datetime': conflict_time,
            'service_ids': [(6, 0, [self.service_cut.id])],
            'state': 'confirmed'
        })
        
        # Get slots after creating conflict
        conflicted_slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=30
        )
        
        # Should have fewer slots due to conflict
        self.assertLess(len(conflicted_slots), initial_count, 
                       "Should have fewer slots after creating conflict")
        
        # Verify no slot overlaps with the appointment (including buffer)
        appointment_start = conflict_appointment.start_datetime
        appointment_end = conflict_appointment.end_datetime or (
            appointment_start + timedelta(minutes=conflict_appointment.duration_minutes)
        )
        
        # Add 5-minute buffer as per implementation
        buffer_start = appointment_start - timedelta(minutes=5)
        buffer_end = appointment_end + timedelta(minutes=5)
        
        for slot in conflicted_slots:
            slot_start = slot['start']
            slot_end = slot['end']
            
            # Ensure no overlap with buffered appointment time
            no_overlap = (slot_end <= buffer_start) or (slot_start >= buffer_end)
            self.assertTrue(no_overlap, 
                          f"Slot {slot_start}-{slot_end} overlaps with appointment buffer {buffer_start}-{buffer_end}")

    def test_slot_generation_with_different_durations(self):
        """Test slot generation for different service durations"""
        
        test_date = self._get_next_weekday(1)  # Tuesday
        
        # Test 15-minute service (should have more slots)
        short_slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=15
        )
        
        # Test 60-minute service (should have fewer slots)
        long_slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=60
        )
        
        # Longer services should generally have fewer available slots
        self.assertGreaterEqual(len(short_slots), len(long_slots), 
                               "Shorter services should have more available slots")
        
        # Verify slot durations are correct
        for slot in short_slots[:3]:  # Check first 3 slots
            duration = (slot['end'] - slot['start']).total_seconds() / 60
            self.assertEqual(duration, 15, "Short slot should be 15 minutes")
        
        for slot in long_slots[:3]:  # Check first 3 slots  
            duration = (slot['end'] - slot['start']).total_seconds() / 60
            self.assertEqual(duration, 60, "Long slot should be 60 minutes")

    def test_slot_engine_boundary_conditions(self):
        """Test slot generation at schedule boundaries"""
        
        test_date = self._get_next_weekday(2)  # Wednesday
        
        # Test with service that would extend past work hours
        slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=120  # 2 hours
        )
        
        # Verify no slot extends past 18:00
        for slot in slots:
            self.assertLessEqual(slot['end'].hour, 18, 
                               "No slot should extend past work hours")
            
            # For 2-hour service, last possible start time should be 16:00
            if slot['start'].hour >= 16:
                self.assertEqual(slot['start'].hour, 16,
                               "Last 2-hour slot should start at 16:00")

    def test_multiple_conflicting_appointments(self):
        """Test slot generation with multiple conflicting appointments"""
        
        test_date = self._get_next_weekday(3)  # Thursday
        
        # Create multiple appointments throughout the day
        appointments = []
        conflict_times = [
            test_date.replace(hour=10, minute=0),
            test_date.replace(hour=13, minute=0), 
            test_date.replace(hour=15, minute=30),
        ]
        
        for conflict_time in conflict_times:
            appointment = self.env['bp.barber.appointment'].create({
                'partner_id': self.customer.id,
                'barber_id': self.barber_mary.id,
                'start_datetime': conflict_time,
                'service_ids': [(6, 0, [self.service_cut.id])],
                'state': 'confirmed'
            })
            appointments.append(appointment)
        
        # Get available slots
        slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=30
        )
        
        # Verify slots don't conflict with any appointment
        for slot in slots:
            for appointment in appointments:
                apt_start = appointment.start_datetime
                apt_end = appointment.end_datetime or (
                    apt_start + timedelta(minutes=appointment.duration_minutes)
                )
                
                # Add buffer
                buffer_start = apt_start - timedelta(minutes=5)
                buffer_end = apt_end + timedelta(minutes=5)
                
                # Check no overlap
                no_overlap = (slot['end'] <= buffer_start) or (slot['start'] >= buffer_end)
                self.assertTrue(no_overlap, 
                              f"Slot conflicts with appointment at {apt_start}")

    def test_slot_engine_performance_and_limits(self):
        """Test that slot engine performs reasonably with realistic constraints"""
        
        test_date = self._get_next_weekday(4)  # Friday
        
        # Time the slot generation
        import time
        start_time = time.time()
        
        slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=30
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (< 1 second for single day)
        self.assertLess(execution_time, 1.0, 
                       "Slot generation should complete within 1 second")
        
        # Should return reasonable number of slots (not too many, not too few)
        # For 9-hour workday with 30-min slots, expect roughly 18 slots maximum
        self.assertLessEqual(len(slots), 25, "Should not return excessive slots")
        self.assertGreaterEqual(len(slots), 5, "Should return reasonable number of slots")

    def _get_next_weekday(self, weekday):
        """Helper to get next occurrence of specified weekday"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)

    def test_edge_case_same_day_past_appointments(self):
        """Test that past appointments on same day don't affect future slots"""
        
        test_date = self._get_next_weekday(5)  # Saturday
        
        # Create past appointment (earlier in the day)
        past_time = test_date.replace(hour=9, minute=0)
        past_appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.customer.id,
            'barber_id': self.barber_mary.id,
            'start_datetime': past_time,
            'service_ids': [(6, 0, [self.service_cut.id])],
            'state': 'done'  # Already completed
        })
        
        # Get slots for later in the day
        slots = self.barber_mary.get_available_slots(
            date=test_date.date(),
            duration_minutes=30
        )
        
        # Should still have slots for afternoon/evening
        afternoon_slots = [s for s in slots if s['start'].hour >= 12]
        self.assertGreater(len(afternoon_slots), 0, 
                          "Should have afternoon slots despite past appointment")