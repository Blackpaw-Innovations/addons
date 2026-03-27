/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BpPersonalDashboard extends Component {
    static template = "bp_role_dashboards.BpPersonalDashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ data: null, isLoading: true });
        onMounted(() => this.load());
    }

    async load() {
        try {
            const data = await this.orm.call(
                "bp.personal.dashboard",
                "get_my_data",
                [],
                {}
            );
            this.state.data = data;
        } catch (e) {
            this.notification.add("Could not load personal dashboard", { type: "warning" });
        } finally {
            this.state.isLoading = false;
        }
    }

    get taskStatusColor() {
        const d = this.state.data;
        if (!d) return "#22c55e";
        if (d.overdue_task_count >= 3) return "#ef4444";
        if (d.overdue_task_count >= 1) return "#f59e0b";
        return "#22c55e";
    }

    fmt(val) {
        if (!val && val !== 0) return "—";
        if (Math.abs(val) >= 1_000_000) return (val / 1_000_000).toFixed(2) + "M";
        if (Math.abs(val) >= 1_000) return (val / 1_000).toFixed(1) + "K";
        return Number(val).toLocaleString();
    }
}

registry.category("actions").add("bp_dash_personal", BpPersonalDashboard);
