# -*- coding: utf-8 -*-
import datetime
from odoo import api, models


class BpHrDashboard(models.TransientModel):
    _name = "bp.hr.dashboard"
    _description = "HR Intelligence Dashboard"

    @api.model
    def get_dashboard_data(self):
        today = datetime.date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        company_id = self.env.company.id

        Employee = self.env["hr.employee"]

        # ── Headcount ─────────────────────────────────────────────────────────
        headcount = Employee.search_count([
            ("company_id", "=", company_id),
            ("active", "=", True),
        ])

        # ── On leave today ────────────────────────────────────────────────────
        on_leave = 0
        try:
            Leave = self.env["hr.leave"]
            on_leave = Leave.search_count([
                ("state", "=", "validate"),
                ("date_from", "<=", datetime.datetime.combine(today, datetime.time.max)),
                ("date_to", ">=", datetime.datetime.combine(today, datetime.time.min)),
                ("employee_id.company_id", "=", company_id),
            ])
        except (KeyError, AttributeError):
            pass

        # ── Open positions ────────────────────────────────────────────────────
        open_positions = 0
        try:
            Job = self.env["hr.job"]
            open_positions = sum(Job.search([
                ("company_id", "=", company_id),
                ("no_of_recruitment", ">", 0),
            ]).mapped("no_of_recruitment"))
        except (KeyError, AttributeError):
            pass

        # ── Overtime % MTD ────────────────────────────────────────────────────
        ot_pct = 0.0
        ot_hours = 0.0
        total_hours = 0.0
        try:
            Overtime = self.env["hr.attendance.overtime"]
            Attendance = self.env["hr.attendance"]
            ot_lines = Overtime.search([
                ("date", ">=", month_start),
                ("employee_id.company_id", "=", company_id),
            ])
            ot_hours = sum(l.duration for l in ot_lines if l.duration > 0)
            att_lines = Attendance.search([
                ("check_in", ">=", datetime.datetime.combine(month_start, datetime.time.min)),
                ("employee_id.company_id", "=", company_id),
            ])
            total_hours = sum(att_lines.mapped("worked_hours"))
            ot_pct = round(ot_hours / total_hours * 100, 1) if total_hours else 0.0
        except (KeyError, AttributeError, Exception):
            pass

        # ── Monthly payroll ───────────────────────────────────────────────────
        payroll_total = 0.0
        try:
            Payslip = self.env["hr.payslip"]
            slips = Payslip.search([
                ("state", "=", "done"),
                ("date_from", ">=", month_start),
                ("company_id", "=", company_id),
            ])
            payroll_total = sum(slips.mapped("net_wage"))
        except (KeyError, AttributeError, Exception):
            pass

        # ── Attrition YTD ─────────────────────────────────────────────────────
        attrition_ytd = 0
        try:
            attrition_ytd = Employee.with_context(active_test=False).search_count([
                ("active", "=", False),
                ("departure_date", ">=", year_start),
                ("company_id", "=", company_id),
            ])
        except (KeyError, AttributeError, Exception):
            pass

        # ── Appraisals overdue ────────────────────────────────────────────────
        appraisals_overdue = 0
        try:
            Appraisal = self.env["hr.appraisal"]
            cutoff = today - datetime.timedelta(days=60)
            appraisals_overdue = Appraisal.search_count([
                ("state", "not in", ["done", "cancel"]),
                ("date_close", "<", cutoff),
                ("company_id", "=", company_id),
            ])
        except (KeyError, AttributeError, Exception):
            pass

        # ── Overtime trend (6 months) ─────────────────────────────────────────
        ot_trend = []
        try:
            Overtime = self.env["hr.attendance.overtime"]
            for i in range(5, -1, -1):
                ref = today.replace(day=1) - datetime.timedelta(days=1)
                for _ in range(i):
                    ref = ref.replace(day=1) - datetime.timedelta(days=1)
                ms = ref.replace(day=1)
                me = ref
                lines = Overtime.search([
                    ("date", ">=", ms), ("date", "<=", me),
                    ("employee_id.company_id", "=", company_id),
                ])
                ot_trend.append({
                    "label": ms.strftime("%b"),
                    "ot_hours": round(sum(l.duration for l in lines if l.duration > 0), 1),
                })
        except (KeyError, AttributeError, Exception):
            ot_trend = []

        # ── Leave liability by department ─────────────────────────────────────
        leave_liability = []
        try:
            Allocation = self.env["hr.leave.allocation"]
            allocs = Allocation.search([
                ("state", "=", "validate"),
                ("employee_id.company_id", "=", company_id),
            ])
            dept_data = {}
            for a in allocs:
                dept = a.employee_id.department_id.name if a.employee_id.department_id else "No Department"
                wage = a.employee_id.contract_id.wage if a.employee_id.contract_id else 0
                daily_rate = wage / 26 if wage else 0
                liability = a.number_of_days * daily_rate
                dept_data.setdefault(dept, 0.0)
                dept_data[dept] += liability
            leave_liability = [
                {"dept": k, "liability": v}
                for k, v in sorted(dept_data.items(), key=lambda x: -x[1])[:8]
            ]
        except (KeyError, AttributeError, Exception):
            pass

        # ── Attrition detail ──────────────────────────────────────────────────
        attrition_detail = []
        try:
            departed = Employee.with_context(active_test=False).search([
                ("active", "=", False),
                ("departure_date", ">=", year_start),
                ("company_id", "=", company_id),
            ], limit=8)
            for e in departed:
                tenure = 0
                try:
                    tenure = round((e.departure_date - e.create_date.date()).days / 30, 0)
                except Exception:
                    pass
                attrition_detail.append({
                    "name": e.name,
                    "dept": e.department_id.name if e.department_id else "—",
                    "reason": e.departure_reason_id.name if e.departure_reason_id else "—",
                    "tenure_mo": int(tenure),
                })
        except (KeyError, AttributeError, Exception):
            pass

        # ── Department breakdown ──────────────────────────────────────────────
        dept_breakdown = []
        try:
            dept_employees = {}
            for emp in Employee.search([("company_id", "=", company_id), ("active", "=", True)]):
                dept = emp.department_id.name if emp.department_id else "No Department"
                dept_employees.setdefault(dept, 0)
                dept_employees[dept] += 1
            dept_breakdown = sorted(
                [{"dept": k, "count": v} for k, v in dept_employees.items()],
                key=lambda x: -x["count"]
            )[:8]
        except Exception:
            pass

        # ── Signals ───────────────────────────────────────────────────────────
        signals = []

        if ot_pct > 20:
            signals.append({
                "code": "CHK",
                "color": "#f59e0b",
                "name": "Team Is Running Above Sustainable Capacity",
                "desc": f"Overtime is at {ot_pct}% of total hours this month. Sustained above 20% leads to burnout, errors and eventual attrition.",
                "nums": [
                    {"label": "OT hours MTD", "value": f"{ot_hours:.0f}h"},
                    {"label": "Total hours", "value": f"{total_hours:.0f}h"},
                    {"label": "OT %", "value": f"{ot_pct}%"},
                ],
                "perspective": "People",
                "perspective_color": "#f59e0b",
                "action": "Identify departments driving OT. Check if headcount gap or workload spike. Consider temp resource or workload redistribution.",
            })

        if attrition_ytd >= 2:
            signals.append({
                "code": "LKG",
                "color": "#ef4444",
                "name": "Attrition Pattern Points to a Systemic Issue",
                "desc": f"{attrition_ytd} employees have left YTD. If clustering in one department, the issue is structural not individual.",
                "nums": [
                    {"label": "Exits YTD", "value": str(attrition_ytd)},
                    {"label": "Headcount", "value": str(headcount)},
                    {"label": "Attrition rate", "value": f"{round(attrition_ytd / headcount * 100, 1) if headcount else 0}%"},
                ],
                "perspective": "Risk",
                "perspective_color": "#ef4444",
                "action": "Run exit interview analysis. If 2+ exits from same department, escalate to leadership review within 30 days.",
            })

        if appraisals_overdue >= 3:
            signals.append({
                "code": "IGN",
                "color": "#8b5cf6",
                "name": "Appraisal Backlog Is a Culture Signal",
                "desc": f"{appraisals_overdue} appraisals are overdue by more than 60 days. Employees read delayed reviews as disengagement from management.",
                "nums": [
                    {"label": "Overdue", "value": str(appraisals_overdue)},
                    {"label": "Threshold", "value": ">60 days"},
                ],
                "perspective": "Culture",
                "perspective_color": "#8b5cf6",
                "action": "Schedule bulk completion sprint. Assign HR BP to each line manager with overdue reviews. Target close within 2 weeks.",
            })

        if not signals:
            signals.append({
                "code": "THR",
                "color": "#22c55e",
                "name": "No Critical HR Signals Detected",
                "desc": "Overtime, attrition and appraisal metrics are within acceptable ranges.",
                "nums": [],
                "perspective": "Healthy",
                "perspective_color": "#22c55e",
                "action": "Continue monitoring. Review OT trend monthly.",
            })

        kpis = [
            {"label": "Headcount", "value": str(headcount), "variant": "primary", "sub": "active employees"},
            {"label": "On Leave", "value": str(on_leave), "variant": "default", "sub": "today"},
            {"label": "Open Positions", "value": str(open_positions), "variant": "warn" if open_positions else "default", "sub": "unfilled roles"},
            {"label": "Overtime % MTD", "value": f"{ot_pct}%", "variant": "danger" if ot_pct > 25 else ("warn" if ot_pct > 15 else "default"), "sub": f"{ot_hours:.0f}h OT"},
            {"label": "Monthly Payroll", "value": _fmt_short(payroll_total), "variant": "primary", "sub": self.env.company.currency_id.name},
            {"label": "Attrition YTD", "value": str(attrition_ytd), "variant": "danger" if attrition_ytd >= 3 else ("warn" if attrition_ytd >= 1 else "default"), "sub": "exits this year"},
        ]

        return {
            "kpis": kpis,
            "signals": signals,
            "tables": {
                "ot_trend": ot_trend,
                "leave_liability": leave_liability,
                "attrition_detail": attrition_detail,
                "dept_breakdown": dept_breakdown,
            },
            "period": today.strftime("%B %Y"),
        }


def _fmt_short(val):
    if not val:
        return "0"
    if abs(val) >= 1_000_000:
        return f"{val / 1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"{val / 1_000:.1f}K"
    return f"{val:,.0f}"
