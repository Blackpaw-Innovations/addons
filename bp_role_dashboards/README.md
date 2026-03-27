# BP Role Dashboards

`bp_role_dashboards` adds five role-focused intelligence dashboards for Blackpaw deployments on Odoo 19. Finance, HR, Sales, Operations, and Fuel teams each get a fast executive view of the metrics, signals, and tables that matter to their function. Weekly AI-generated brief emails are sent automatically every Monday.

---

## Architecture Position

```
bp_role_dashboards
  ├─ depends: account, hr, hr_attendance, crm, sale, mail, web, blackpaw_ai_service
  ├─ 5 × OWL client actions  (BpFinanceDashboard, BpHrDashboard, ...)
  ├─ 5 × TransientModel      (bp.finance.dashboard, bp.hr.dashboard, ...)
  ├─ 1 × cron model          (bp.brief.cron)
  └─ 1 × watchlist model     (bp.intelligence.watchlist)
```

The module is **independent** of `bp_strategic_intelligence` and `blackpaw_bi_dashboard`. It calls Claude exclusively through `blackpaw_ai_service`.

---

## Prerequisites

1. `blackpaw_ai_service` installed and configured (see its README).
2. Odoo 19 Community or Enterprise.
3. `account`, `hr`, `hr_attendance`, `crm`, `sale` modules installed.

---

## Installation

### 1. Add mount in Docker Compose

```yaml
# blackpaw-odoo-docker/docker-compose-19.yaml
volumes:
  - ../addons/bp_role_dashboards:/mnt/extra-addons/bp_role_dashboards
  - ../blackpaw_ai_service:/mnt/extra-addons/blackpaw_ai_service
```

### 2. Install

```bash
docker exec odoo19 odoo \
  -d blackpaw19 \
  -c /etc/odoo/odoo.conf \
  -i bp_role_dashboards \
  --stop-after-init
docker restart odoo19
```

### 3. Hard-refresh browser

`Ctrl+Shift+R` — clears the OWL/JS asset cache.

---

## Access Rights

Groups are shown in **Settings → Users & Companies → Groups** under the `Blackpaw /` prefix.

| Group | Implied By | Default Members | Permissions |
|-------|-----------|-----------------|-------------|
| Blackpaw / Dashboard User | `base.group_user` (all internal users) | All internal users | Read dashboards, read watchlist |
| Blackpaw / Dashboard Manager | Dashboard User | `admin` (always) | Read + write + create + delete watchlist; write brief cron settings |

**Admin always has Dashboard Manager access** — this is set automatically in the security XML via `user_ids`.

### Assigning Dashboard Manager to additional users

Settings → Users & Companies → Users → open user → Groups tab → add `Blackpaw / Dashboard Manager`.

---

## Menu Placement

| Dashboard | Path |
|-----------|------|
| Finance Intelligence | Accounting → Reporting → Finance Intelligence |
| HR Intelligence | Employees → Reporting → HR Intelligence |
| Sales Intelligence | Sales → Reporting → Sales Intelligence |
| Operations Intelligence | Blackpaw Intelligence → Operations Dashboard |
| Fuel Intelligence | Blackpaw Intelligence → Fuel Dashboard |
| All dashboards | Blackpaw Intelligence (top-level menu) |

---

## Weekly Brief Emails

A cron job (`bp.brief.cron`) runs every Monday at 06:00 and sends role-specific HTML brief emails to the designated recipients. The brief includes:

- An AI-generated opening paragraph (2 sentences, via gateway prompt `bi.role_brief.opener`)
- Key KPI cards
- Top signals (RED/AMBER/GREEN)
- A deep link back to the dashboard in Odoo

**Recipients** are configured per brief in Settings or directly on the `bp.brief.cron` records.

**AI brief fallback:** If the gateway is unavailable, a static phrase is used — the email still sends.

---

## AI Integration

The module uses `blackpaw.ai.service` with prompt key `bi.role_brief.opener`. The gateway must be running and `blackpaw.ai_gateway_url` must be set in System Parameters.

Cache key format: `brief_opener_{role}_{company_id}_{ISO_week_number}`

This means each role gets one AI brief per week, per company, cached.

---

## Dashboards

### Finance Intelligence

Live metrics from `account.move`:
- Revenue MTD, Expenses MTD, Gross Profit, Gross Profit %, Cash in Bank
- AR Outstanding, Overdue Receivables, AR Aging
- Revenue Concentration by Client
- Payables Watchlist
- 6-month Revenue and Expense trend

### HR Intelligence

Live metrics from `hr.employee`, `hr.leave`, `hr.attendance`:
- Headcount, Employees on Leave, Open Positions
- Overtime % MTD, Monthly Payroll, Attrition YTD
- Overtime Trend, Leave Liability by Department
- Attrition Detail, Appraisal Backlog Signals

### Sales Intelligence

Live metrics from `crm.lead`, `sale.order`:
- Pipeline Value, Win Rate, Deals Closed MTD, Avg Deal Size
- Proposals Sent, Churn Risk
- Pipeline by Stage, Win Rate Trend, Loss Reasons
- Rep Performance Leaderboard, Stale Proposal Risk

### Operations Intelligence

Live metrics from `bp.job.card` (requires `bp_jobcards_app`):
- Open Jobs, Active Jobs, Overdue Jobs, Completed MTD
- Revenue MTD, Gross Margin Estimate
- Active Job Detail, Awaiting Sign-off Queue
- Degrades gracefully to a finance view if `bp_jobcards_app` is not installed

### Fuel Station Intelligence

Live metrics from the Blackpaw Fuel stack (requires `bp-fuel-solution`):
- Open Sessions, Dispensed Today, Variance %, Wet Stock Days
- Float Status, QMS Score
- Operational Risk Signals
- Degrades gracefully to setup guidance if the fuel stack is not installed

---

## Watchlist

`bp.intelligence.watchlist` stores items that the Dashboard Manager wants to monitor. The watchlist appears as a panel inside the dashboards. Only Dashboard Managers can add or remove watchlist items.

---

## Files

```
addons/bp_role_dashboards/
  __manifest__.py
  __init__.py
  models/
    __init__.py
    bp_finance_dashboard.py     ← bp.finance.dashboard TransientModel
    bp_hr_dashboard.py
    bp_sales_dashboard.py
    bp_operations_dashboard.py
    bp_fuel_dashboard.py
    bp_personal_dashboard.py
    bp_brief_cron.py            ← bp.brief.cron + Monday email logic
    bp_watchlist.py             ← bp.intelligence.watchlist
  security/
    bp_role_dashboards_security.xml
    ir.model.access.csv
  data/
    bp_cron.xml                 ← Monday 06:00 cron record
  views/
    bp_watchlist_views.xml
    bp_role_dashboards_actions.xml
  static/src/
    js/
      bp_finance_dashboard.js
      bp_hr_dashboard.js
      bp_sales_dashboard.js
      bp_operations_dashboard.js
      bp_fuel_dashboard.js
      bp_personal_dashboard.js
    xml/
      bp_finance_dashboard.xml
      bp_hr_dashboard.xml
      bp_sales_dashboard.xml
      bp_operations_dashboard.xml
      bp_fuel_dashboard.xml
      bp_personal_dashboard.xml
    scss/
      bp_role_dashboards.scss
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Dashboard menu not visible | User not in any internal group | Assign user to `Internal User` base group |
| Watchlist write blocked | User not in Dashboard Manager | Add `Blackpaw / Dashboard Manager` group |
| AI brief opener missing | Gateway not configured | Set `blackpaw.ai_gateway_url` and `blackpaw.ai_gateway_secret` in System Parameters |
| Operations dashboard shows finance fallback | `bp_jobcards_app` not installed | Install `bp_jobcards_app` or ignore — fallback is intentional |
| Monday brief not sending | Cron inactive | Settings → Technical → Scheduled Actions → activate `Send Role Intelligence Brief` |

---

## Support

- Maintainer: Blackpaw Innovations
- Website: https://www.blackpawinnovations.com
- Support: support@blackpawinnovations.com
