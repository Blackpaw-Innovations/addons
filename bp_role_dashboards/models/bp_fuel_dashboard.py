# -*- coding: utf-8 -*-
import datetime
from odoo import api, models


class BpFuelDashboard(models.TransientModel):
    _name = "bp.fuel.dashboard"
    _description = "Fuel Station Intelligence Dashboard"

    @api.model
    def get_dashboard_data(self):
        today = datetime.date.today()
        company_id = self.env.company.id
        currency = self.env.company.currency_id

        kpis = []
        signals = []
        tables = {}

        try:
            FuelOps = self.env["fuel.operations.dashboard"]
            raw = FuelOps.get_dashboard_data()

            # Extract whatever the method returns and surface it
            open_sessions = raw.get("open_sessions", 0) if isinstance(raw, dict) else 0
            dispensed_today = raw.get("dispensed_today", 0) if isinstance(raw, dict) else 0
            variance_pct = raw.get("variance_pct", 0) if isinstance(raw, dict) else 0
            wet_stock_days = raw.get("wet_stock_days", 0) if isinstance(raw, dict) else 0
            float_ok = raw.get("float_ok", True) if isinstance(raw, dict) else True
            qms_score = raw.get("qms_score", 0) if isinstance(raw, dict) else 0

            kpis = [
                {"label": "Open Sessions", "value": str(open_sessions), "variant": "primary", "sub": "active"},
                {"label": "Dispensed Today", "value": _fmt_short(dispensed_today) + "L", "variant": "default", "sub": "litres"},
                {"label": "Variance %", "value": f"{variance_pct:.2f}%", "variant": "danger" if variance_pct > 0.5 else ("warn" if variance_pct > 0.2 else "default"), "sub": "vs expected"},
                {"label": "Wet Stock Days", "value": str(wet_stock_days), "variant": "danger" if wet_stock_days < 3 else ("warn" if wet_stock_days < 5 else "success"), "sub": "days remaining"},
                {"label": "Float Status", "value": "OK" if float_ok else "ALERT", "variant": "success" if float_ok else "danger", "sub": "cash float"},
                {"label": "QMS Score", "value": f"{qms_score}%", "variant": "success" if qms_score >= 90 else ("warn" if qms_score >= 70 else "danger"), "sub": "daily checklist"},
            ]

            # Signals
            if variance_pct > 0.5:
                signals.append({
                    "code": "BLD",
                    "color": "#dc2626",
                    "name": "Pump Variance Exceeds 0.5% — Daily KES Loss Detected",
                    "desc": f"Variance of {variance_pct:.2f}% against expected volume. At current throughput this represents a measurable daily KES loss.",
                    "nums": [
                        {"label": "Variance %", "value": f"{variance_pct:.2f}%"},
                        {"label": "Threshold", "value": "0.5%"},
                    ],
                    "perspective": "Risk",
                    "perspective_color": "#ef4444",
                    "action": "Dip check all affected tanks immediately. Verify meter calibration. Cross-reference delivery notes vs received volumes.",
                })

            if wet_stock_days < 3:
                signals.append({
                    "code": "FRG",
                    "color": "#ef4444",
                    "name": "Wet Stock Buffer Critical — Supply Risk in 72 Hours",
                    "desc": f"Current wet stock covers only {wet_stock_days} days at current dispensing rate. A delivery delay could halt operations.",
                    "nums": [
                        {"label": "Days remaining", "value": str(wet_stock_days)},
                        {"label": "Critical threshold", "value": "<3 days"},
                    ],
                    "perspective": "Supply",
                    "perspective_color": "#ef4444",
                    "action": "Place emergency order now. Confirm ETA from supplier. Identify backup supplier if primary cannot deliver within 24h.",
                })

            tables = raw.get("tables", {}) if isinstance(raw, dict) else {}

        except Exception:
            # Fuel model not available
            kpis = [
                {"label": "Open Sessions", "value": "—", "variant": "default", "sub": "not configured"},
                {"label": "Dispensed Today", "value": "—", "variant": "default", "sub": ""},
                {"label": "Variance %", "value": "—", "variant": "default", "sub": ""},
                {"label": "Wet Stock Days", "value": "—", "variant": "default", "sub": ""},
                {"label": "Float Status", "value": "—", "variant": "default", "sub": ""},
                {"label": "QMS Score", "value": "—", "variant": "default", "sub": ""},
            ]
            signals.append({
                "code": "IGN",
                "color": "#8b5cf6",
                "name": "Fuel Module Not Configured on This Instance",
                "desc": "The bp-fuel-solution module is not installed or the fuel.operations.dashboard model is not available.",
                "nums": [],
                "perspective": "Setup",
                "perspective_color": "#8b5cf6",
                "action": "Install bp-fuel-solution and bp_bi_fuel_qms modules to activate this dashboard.",
            })

        if not signals:
            signals.append({
                "code": "THR",
                "color": "#22c55e",
                "name": "Fuel Station Operating Normally",
                "desc": "Variance, stock levels and QMS scores are all within acceptable parameters.",
                "nums": [],
                "perspective": "Healthy",
                "perspective_color": "#22c55e",
                "action": "Continue daily dip checks and QMS completion before shift close.",
            })

        return {
            "kpis": kpis,
            "signals": signals,
            "tables": tables,
            "currency": currency.name,
            "period": today.strftime("%B %Y"),
        }


def _fmt_short(val):
    if not val:
        return "0"
    if abs(val) >= 1_000_000:
        return f"{val/1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"{val/1_000:.1f}K"
    return f"{val:,.0f}"
