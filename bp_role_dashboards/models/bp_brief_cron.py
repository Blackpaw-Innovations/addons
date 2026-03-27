# -*- coding: utf-8 -*-
import datetime
from odoo import api, models


class BpBriefCron(models.TransientModel):
    _name = "bp.brief.cron"
    _description = "Blackpaw Weekly Intelligence Brief Generator"

    @api.model
    def send_weekly_briefs(self):
        """
        Entry point for the weekly cron (Monday 06:00).
        Sends role-appropriate intelligence briefs to configured recipients.
        """
        for company in self.env["res.company"].search([]):
            self_co = self.with_company(company)
            self_co._send_finance_brief()
            self_co._send_hr_brief()
            self_co._send_sales_brief()

    # ── Finance Brief ─────────────────────────────────────────────────────────

    def _send_finance_brief(self):
        try:
            data = self.env["bp.finance.dashboard"].get_dashboard_data()
        except Exception:
            return

        recipients = self._get_group_emails("account.group_account_manager")
        if not recipients:
            return

        subject, body = self._format_finance_brief(data)
        self._send_mail(recipients, subject, body)

    def _format_finance_brief(self, data):
        company = self.env.company
        period = data.get("period", "")
        currency = data.get("currency", "KES")
        kpis = {k["label"]: k["value"] for k in data.get("kpis", [])}
        signals = data.get("signals", [])

        subject = f"Finance Intelligence Brief — {period} | {company.name}"
        opener  = self._get_brief_opener("Finance", kpis, signals)

        signal_lines = ""
        for sig in signals:
            badge = "●" if sig.get("color") == "#ef4444" else ("◐" if sig.get("color") == "#f59e0b" else "○")
            signal_lines += f"<tr><td style='padding:4px 8px;color:{sig.get('color','#333')};font-weight:bold'>{badge} {sig.get('code','')}</td><td style='padding:4px 8px'>{sig.get('name','')}</td></tr>"
            if sig.get("action"):
                signal_lines += f"<tr><td></td><td style='padding:2px 8px 8px;color:#666;font-size:12px'>{sig.get('action','')}</td></tr>"

        kpi_lines = ""
        for label, value in kpis.items():
            kpi_lines += f"<tr><td style='padding:3px 8px;color:#64748b'>{label}</td><td style='padding:3px 8px;font-weight:600'>{value}</td></tr>"

        opener_html = f"<p style='padding:0 0 16px;margin:0;font-size:13px;color:#1e293b;line-height:1.6'>{opener}</p>" if opener else ""

        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#1e293b">
          <div style="background:#1e293b;padding:20px 24px;border-radius:8px 8px 0 0">
            <h2 style="margin:0;color:#f1f5f9;font-size:16px">{company.name}</h2>
            <p style="margin:4px 0 0;color:#94a3b8;font-size:13px">Finance Intelligence — {period}</p>
          </div>
          <div style="background:#f8fafc;padding:20px 24px">
            {opener_html}
            <table style="width:100%;border-collapse:collapse;margin-bottom:20px">{kpi_lines}</table>
            <h3 style="font-size:13px;color:#475569;text-transform:uppercase;letter-spacing:.05em;margin:0 0 8px">Active Signals</h3>
            <table style="width:100%;border-collapse:collapse">{signal_lines}</table>
          </div>
          <div style="background:#f1f5f9;padding:12px 24px;border-radius:0 0 8px 8px">
            <p style="margin:0;font-size:12px;color:#94a3b8">Blackpaw Intelligence | {datetime.date.today().strftime('%d %B %Y')}</p>
          </div>
        </div>
        """
        return subject, body

    # ── HR Brief ──────────────────────────────────────────────────────────────

    def _send_hr_brief(self):
        try:
            data = self.env["bp.hr.dashboard"].get_dashboard_data()
        except Exception:
            return

        recipients = self._get_group_emails("hr.group_hr_manager")
        if not recipients:
            return

        subject, body = self._format_hr_brief(data)
        self._send_mail(recipients, subject, body)

    def _format_hr_brief(self, data):
        company = self.env.company
        period = data.get("period", "")
        kpis = {k["label"]: k["value"] for k in data.get("kpis", [])}
        signals = data.get("signals", [])

        subject = f"People Intelligence Brief — {period} | {company.name}"
        opener  = self._get_brief_opener("HR", kpis, signals)

        signal_lines = ""
        for sig in signals:
            badge = "●" if sig.get("color") == "#ef4444" else ("◐" if sig.get("color") == "#f59e0b" else "○")
            signal_lines += f"<tr><td style='padding:4px 8px;color:{sig.get('color','#333')};font-weight:bold'>{badge} {sig.get('code','')}</td><td style='padding:4px 8px'>{sig.get('name','')}</td></tr>"

        kpi_lines = "".join(
            f"<tr><td style='padding:3px 8px;color:#64748b'>{l}</td><td style='padding:3px 8px;font-weight:600'>{v}</td></tr>"
            for l, v in kpis.items()
        )

        opener_html = f"<p style='padding:0 0 16px;margin:0;font-size:13px;color:#1e293b;line-height:1.6'>{opener}</p>" if opener else ""

        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#1e293b">
          <div style="background:#7c3aed;padding:20px 24px;border-radius:8px 8px 0 0">
            <h2 style="margin:0;color:#f1f5f9;font-size:16px">{company.name}</h2>
            <p style="margin:4px 0 0;color:#ddd6fe;font-size:13px">People Intelligence — {period}</p>
          </div>
          <div style="background:#f8fafc;padding:20px 24px">
            {opener_html}
            <table style="width:100%;border-collapse:collapse;margin-bottom:20px">{kpi_lines}</table>
            <h3 style="font-size:13px;color:#475569;text-transform:uppercase;letter-spacing:.05em;margin:0 0 8px">Active Signals</h3>
            <table style="width:100%;border-collapse:collapse">{signal_lines}</table>
          </div>
          <div style="background:#f1f5f9;padding:12px 24px;border-radius:0 0 8px 8px">
            <p style="margin:0;font-size:12px;color:#94a3b8">Blackpaw Intelligence | {datetime.date.today().strftime('%d %B %Y')}</p>
          </div>
        </div>
        """
        return subject, body

    # ── Sales Brief ───────────────────────────────────────────────────────────

    def _send_sales_brief(self):
        try:
            data = self.env["bp.sales.dashboard"].get_dashboard_data()
        except Exception:
            return

        recipients = self._get_group_emails("sales_team.group_sale_manager")
        if not recipients:
            return

        subject, body = self._format_sales_brief(data)
        self._send_mail(recipients, subject, body)

    def _format_sales_brief(self, data):
        company = self.env.company
        period = data.get("period", "")
        kpis = {k["label"]: k["value"] for k in data.get("kpis", [])}
        signals = data.get("signals", [])

        subject = f"Revenue Intelligence Brief — {period} | {company.name}"
        opener  = self._get_brief_opener("Sales", kpis, signals)

        signal_lines = ""
        for sig in signals:
            badge = "●" if sig.get("color") == "#ef4444" else ("◐" if sig.get("color") == "#f59e0b" else "○")
            signal_lines += f"<tr><td style='padding:4px 8px;color:{sig.get('color','#333')};font-weight:bold'>{badge} {sig.get('code','')}</td><td style='padding:4px 8px'>{sig.get('name','')}</td></tr>"

        kpi_lines = "".join(
            f"<tr><td style='padding:3px 8px;color:#64748b'>{l}</td><td style='padding:3px 8px;font-weight:600'>{v}</td></tr>"
            for l, v in kpis.items()
        )

        opener_html = f"<p style='padding:0 0 16px;margin:0;font-size:13px;color:#1e293b;line-height:1.6'>{opener}</p>" if opener else ""

        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#1e293b">
          <div style="background:#0284c7;padding:20px 24px;border-radius:8px 8px 0 0">
            <h2 style="margin:0;color:#f1f5f9;font-size:16px">{company.name}</h2>
            <p style="margin:4px 0 0;color:#bae6fd;font-size:13px">Revenue Intelligence — {period}</p>
          </div>
          <div style="background:#f8fafc;padding:20px 24px">
            {opener_html}
            <table style="width:100%;border-collapse:collapse;margin-bottom:20px">{kpi_lines}</table>
            <h3 style="font-size:13px;color:#475569;text-transform:uppercase;letter-spacing:.05em;margin:0 0 8px">Active Signals</h3>
            <table style="width:100%;border-collapse:collapse">{signal_lines}</table>
          </div>
          <div style="background:#f1f5f9;padding:12px 24px;border-radius:0 0 8px 8px">
            <p style="margin:0;font-size:12px;color:#94a3b8">Blackpaw Intelligence | {datetime.date.today().strftime('%d %B %Y')}</p>
          </div>
        </div>
        """
        return subject, body

    # ── AI Opener ─────────────────────────────────────────────────────────────

    def _get_brief_opener(self, role, kpis, signals):
        """
        Call blackpaw.ai.service to generate a 2-sentence opener for the brief.
        Fails silently — returns None if AI unavailable.
        """
        try:
            top_signals = [
                {"code": s.get("code", ""), "name": s.get("name", ""), "severity": s.get("color", "")}
                for s in (signals or [])[:3]
            ]
            data_dict = {
                "company": self.env.company.name,
                "role": role,
                "kpis": kpis,
                "top_signals": top_signals,
            }
            cache_key = (
                f"brief_opener_{role}_{self.env.company.id}_"
                f"{__import__('datetime').date.today().isocalendar()[1]}"
            )
            return self.env["blackpaw.ai.service"].generate(
                prompt_key="bi.role_brief.opener",
                data_dict=data_dict,
                cache_key=cache_key,
            )
        except Exception:
            return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_group_emails(self, group_xml_id):
        """Return list of email addresses for users in the given group within current company."""
        try:
            group = self.env.ref(group_xml_id)
        except Exception:
            return []
        users = group.users.filtered(
            lambda u: u.company_id == self.env.company and u.email and u.active
        )
        return [u.email for u in users]

    def _send_mail(self, recipients, subject, body_html):
        """Send an HTML email to a list of addresses using the outgoing mail server."""
        if not recipients:
            return
        IrMail = self.env["ir.mail_server"].sudo()
        mail = self.env["mail.mail"].sudo().create({
            "subject": subject,
            "email_from": self.env.company.email or "noreply@blackpawinnovations.com",
            "email_to": ",".join(recipients),
            "body_html": body_html,
            "auto_delete": True,
        })
        try:
            mail.send()
        except Exception:
            pass
