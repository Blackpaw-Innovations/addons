# -*- coding: utf-8 -*-
import datetime
from odoo import api, models


class BpPersonalDashboard(models.TransientModel):
    _name = "bp.personal.dashboard"
    _description = "Blackpaw Personal Cockpit"

    @api.model
    def get_my_data(self):
        today = datetime.date.today()
        uid = self.env.uid
        user = self.env.user
        company_id = self.env.company.id

        # ── My Tasks ─────────────────────────────────────────────────────────
        my_tasks = []
        try:
            Task = self.env["project.task"]
            tasks = Task.search([
                ("user_ids", "in", [uid]),
                ("stage_id.fold", "=", False),
                ("company_id", "in", [False, company_id]),
            ], order="date_deadline asc, priority desc", limit=10)
            for t in tasks:
                overdue = False
                if t.date_deadline:
                    dl = t.date_deadline.date() if hasattr(t.date_deadline, "date") else t.date_deadline
                    overdue = dl < today
                my_tasks.append({
                    "id": t.id,
                    "name": t.name,
                    "project": t.project_id.name if t.project_id else "—",
                    "deadline": t.date_deadline.strftime("%d %b") if t.date_deadline else "",
                    "overdue": overdue,
                    "priority": t.priority,
                })
        except Exception:
            pass

        # ── Pending Approvals (my outgoing) ──────────────────────────────────
        pending_approvals = []
        try:
            # Leave requests waiting validation
            Leave = self.env["hr.leave"]
            my_leaves = Leave.search([
                ("employee_id.user_id", "=", uid),
                ("state", "in", ["confirm", "validate1"]),
            ], limit=5)
            for l in my_leaves:
                pending_approvals.append({
                    "type": "Leave",
                    "name": f"{l.holiday_status_id.name} — {l.number_of_days:.0f}d",
                    "state": dict(l._fields["state"].selection).get(l.state, l.state),
                })
        except Exception:
            pass

        try:
            # Expense sheets awaiting approval
            Expense = self.env["hr.expense.sheet"]
            my_expenses = Expense.search([
                ("user_id", "=", uid),
                ("state", "in", ["submit", "approve"]),
            ], limit=5)
            for e in my_expenses:
                pending_approvals.append({
                    "type": "Expense",
                    "name": e.name,
                    "state": dict(e._fields["state"].selection).get(e.state, e.state),
                })
        except Exception:
            pass

        # ── My Leave Balance ──────────────────────────────────────────────────
        leave_balance = []
        try:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", uid), ("company_id", "=", company_id)], limit=1)
            if employee:
                Alloc = self.env["hr.leave.allocation"]
                allocs = Alloc.search([
                    ("employee_id", "=", employee.id),
                    ("state", "=", "validate"),
                ], limit=8)
                for a in allocs:
                    leave_balance.append({
                        "type": a.holiday_status_id.name,
                        "allocated": a.number_of_days,
                        "remaining": a.number_of_days_display if hasattr(a, "number_of_days_display") else a.number_of_days,
                    })
        except Exception:
            pass

        # ── Last Payslip ──────────────────────────────────────────────────────
        last_payslip = None
        try:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", uid), ("company_id", "=", company_id)], limit=1)
            if employee:
                Payslip = self.env["hr.payslip"]
                slip = Payslip.search([
                    ("employee_id", "=", employee.id),
                    ("state", "=", "done"),
                ], order="date_to desc", limit=1)
                if slip:
                    last_payslip = {
                        "period": slip.date_from.strftime("%B %Y") if slip.date_from else "",
                        "net": slip.net_wage,
                        "currency": self.env.company.currency_id.name,
                    }
        except Exception:
            pass

        # ── Upcoming Meetings (today + next 3 days) ───────────────────────────
        upcoming_meetings = []
        try:
            CalEvent = self.env["calendar.event"]
            window_end = datetime.datetime.combine(
                today + datetime.timedelta(days=3), datetime.time.max)
            meetings = CalEvent.search([
                ("partner_ids", "in", [user.partner_id.id]),
                ("start", ">=", datetime.datetime.now()),
                ("start", "<=", window_end),
            ], order="start asc", limit=5)
            for m in meetings:
                upcoming_meetings.append({
                    "name": m.name,
                    "start": m.start.strftime("%d %b %H:%M") if m.start else "",
                    "duration": round(m.duration, 1) if m.duration else 0,
                })
        except Exception:
            pass

        # ── Quick stats ───────────────────────────────────────────────────────
        overdue_task_count = sum(1 for t in my_tasks if t["overdue"])
        high_priority_count = sum(1 for t in my_tasks if t["priority"] == "1")

        return {
            "user_name": user.name,
            "company_name": self.env.company.name,
            "period": today.strftime("%A, %d %B %Y"),
            "my_tasks": my_tasks,
            "overdue_task_count": overdue_task_count,
            "high_priority_count": high_priority_count,
            "pending_approvals": pending_approvals,
            "leave_balance": leave_balance,
            "last_payslip": last_payslip,
            "upcoming_meetings": upcoming_meetings,
        }
