/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class BarberDashboard extends Component {
    static template = "bp_barber_management.dashboard_template";

    setup() {
        this.orm = useService("orm");
        this.http = useService("http");
        this.notification = useService("notification");

        this.state = useState({
            period: "7d",
            dateFrom: null,
            dateTo: null,
            customMode: false,
            loading: false,
            error: null,
            kpis: {
                revenue_by_barber: [],
                revenue_by_service: [],
                utilization: { busy_minutes: 0, available_minutes: 0, percent: 0 },
                no_show_rate: { no_shows: 0, total_bookings: 0, percent: 0 },
                attach_rate: { orders_with_services: 0, with_retail_attached: 0, percent: 0 },
                top_consumables: []
            },
            meta: {
                period: "7d",
                from: null,
                to: null
            }
        });

        onWillStart(async () => {
            await this.loadKpis();
        });
    }

    get periodOptions() {
        return [
            { key: "today", label: _t("Today") },
            { key: "7d", label: _t("Last 7 Days") },
            { key: "30d", label: _t("Last 30 Days") },
            { key: "custom", label: _t("Custom") }
        ];
    }

    async loadKpis() {
        this.state.loading = true;
        this.state.error = null;

        try {
            const payload = {
                period: this.state.period,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo
            };

            const response = await this.http.post("/bp_barber/kpi", payload);

            if (response.error) {
                this.state.error = response.error;
                this.notification.add(response.error, { type: "danger" });
            } else {
                this.state.kpis = response.tiles || {};
                this.state.meta = {
                    period: response.period,
                    from: response.from,
                    to: response.to
                };
            }
        } catch (error) {
            console.error("Failed to load KPIs:", error);
            this.state.error = "Failed to load dashboard data";
            this.notification.add(_t("Failed to load dashboard data"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    onPeriodChange(event) {
        this.state.period = event.target.value;
        this.state.customMode = this.state.period === "custom";

        if (!this.state.customMode) {
            this.state.dateFrom = null;
            this.state.dateTo = null;
            this.loadKpis();
        }
    }

    onDateFromChange(event) {
        this.state.dateFrom = event.target.value;
        if (this.state.dateFrom && this.state.dateTo) {
            this.loadKpis();
        }
    }

    onDateToChange(event) {
        this.state.dateTo = event.target.value;
        if (this.state.dateFrom && this.state.dateTo) {
            this.loadKpis();
        }
    }

    onRefresh() {
        this.loadKpis();
    }

    // Helper methods for rendering
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount || 0);
    }

    formatPercent(percent) {
        return `${(percent || 0).toFixed(1)}%`;
    }

    getTopBarbers(limit = 3) {
        return (this.state.kpis.revenue_by_barber || []).slice(0, limit);
    }

    getTopServices(limit = 3) {
        return (this.state.kpis.revenue_by_service || []).slice(0, limit);
    }

    getTopConsumables(limit = 5) {
        return (this.state.kpis.top_consumables || []).slice(0, limit);
    }

    // Calculate bar widths for mini charts
    getBarWidth(value, maxValue) {
        return maxValue > 0 ? Math.round((value / maxValue) * 100) : 0;
    }

    getTotalRevenue() {
        return (this.state.kpis.revenue_by_barber || [])
            .reduce((sum, item) => sum + (item.amount || 0), 0);
    }

    getMaxBarberRevenue() {
        const revenues = (this.state.kpis.revenue_by_barber || []).map(b => b.amount || 0);
        return Math.max(...revenues, 1);
    }

    getMaxServiceRevenue() {
        const revenues = (this.state.kpis.revenue_by_service || []).map(s => s.amount || 0);
        return Math.max(...revenues, 1);
    }
}

// Register the dashboard component
registry.category("actions").add("bp_barber.dashboard_client_action", BarberDashboard);

export default BarberDashboard;