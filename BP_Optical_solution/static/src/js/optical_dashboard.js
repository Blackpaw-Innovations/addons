/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

export class OpticalDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            kpi: {
                total_patients: 0,
                appointments: 0,
                exams_completed: 0,
                pending_tests: 0,
                revenue: 0,
                currency_symbol: '$',
                currency_name: 'USD',
                no_show_rate: 0,
                avg_waiting_time: 0,
                follow_ups_due: 0,
                repeat_visit_rate: 0
            },
            charts: {},
            sales_metrics: {
                avg_sale_per_patient: 0,
                top_selling_frame: 'N/A',
                top_lens_type: 'N/A',
                insurance_pct: 0,
                cash_pct: 0
            },
            staff: [],
            branches: [],
            customDate: { start: '', end: '' },
            currentBranch: null,
            currentRange: 'today'
        });
        this.charts = {};

        // Refs
        this.patientTypeChartRef = useRef("patientTypeChart");
        this.genderChartRef = useRef("genderChart");
        this.ageGroupChartRef = useRef("ageGroupChart");
        this.appointmentTimelineRef = useRef("appointmentTimeline");
        this.diagnosisChartRef = useRef("diagnosisChart");
        this.revenueBreakdownChartRef = useRef("revenueBreakdownChart");

        onWillStart(async () => {
            await loadBundle("web.chartjs");
            this.state.branches = await this.orm.call("optical.dashboard", "get_branches", []);
            await this.loadData('today');
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async loadData(range) {
        this.state.currentRange = range;
        const args = {
            date_range: range,
            branch_id: this.state.currentBranch
        };

        if (range === 'custom') {
            args.start_date = this.state.customDate.start;
            args.end_date = this.state.customDate.end;
        }

        const result = await this.orm.call("optical.dashboard", "get_dashboard_stats", [], args);
        this.state.kpi = result.kpi;
        this.state.charts = result.charts;
        this.state.sales_metrics = result.sales_metrics;
        this.state.staff = result.staff;
        // Only render if mounted (refs are available)
        if (this.patientTypeChartRef.el) {
            this.renderCharts();
        }
    }

    onBranchChange(ev) {
        this.state.currentBranch = ev.target.value;
        this.loadData(this.state.currentRange);
    }

    renderCharts() {
        if (!this.state.charts.patient_type) return;

        // Ensure Chart is available
        const ChartConstructor = window.Chart && window.Chart.Chart ? window.Chart.Chart : window.Chart;
        if (typeof ChartConstructor !== 'function') {
            console.error("Chart.js not loaded correctly. window.Chart:", window.Chart);
            return;
        }

        // Destroy existing charts
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};

        // Helper to get context safely
        const getCtx = (ref) => {
            return ref.el ? ref.el.getContext('2d') : null;
        };

        // Helper to check if data is empty
        const isDataEmpty = (data) => {
            return !data || data.every(v => v === 0);
        };

        // Patient Type Chart
        const ctx1 = getCtx(this.patientTypeChartRef);
        if (ctx1) {
            this.charts.patientType = new ChartConstructor(ctx1, {
                type: 'bar',
                data: {
                    labels: this.state.charts.patient_type.labels,
                    datasets: [{
                        label: 'Patients',
                        data: this.state.charts.patient_type.data,
                        backgroundColor: ['rgba(59, 130, 246, 0.7)', 'rgba(16, 185, 129, 0.7)'],
                        borderColor: ['rgba(59, 130, 246, 1)', 'rgba(16, 185, 129, 1)'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });
        }

        // Gender Chart
        const ctx2 = getCtx(this.genderChartRef);
        if (ctx2) {
            let chartData = this.state.charts.gender.data;
            let chartLabels = this.state.charts.gender.labels;
            let backgroundColors = ['rgba(59, 130, 246, 0.7)', 'rgba(244, 114, 182, 0.7)', 'rgba(156, 163, 175, 0.7)'];

            if (isDataEmpty(chartData)) {
                chartData = [1]; // Dummy data
                chartLabels = ['No Data'];
                backgroundColors = ['rgba(200, 200, 200, 0.3)'];
            }

            this.charts.gender = new ChartConstructor(ctx2, {
                type: 'doughnut',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        data: chartData,
                        backgroundColor: backgroundColors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: { enabled: !isDataEmpty(this.state.charts.gender.data) }
                    }
                }
            });
        }

        // Age Group Chart
        const ctx3 = getCtx(this.ageGroupChartRef);
        if (ctx3) {
            let chartData = this.state.charts.age_group.data;
            let chartLabels = this.state.charts.age_group.labels;
            let backgroundColors = ['rgba(249, 168, 37, 0.7)', 'rgba(59, 130, 246, 0.7)', 'rgba(139, 92, 246, 0.7)'];

            if (isDataEmpty(chartData)) {
                chartData = [1]; // Dummy data
                chartLabels = ['No Data'];
                backgroundColors = ['rgba(200, 200, 200, 0.3)'];
            }

            this.charts.ageGroup = new ChartConstructor(ctx3, {
                type: 'doughnut',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        data: chartData,
                        backgroundColor: backgroundColors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: { enabled: !isDataEmpty(this.state.charts.age_group.data) }
                    }
                }
            });
        }

        // Timeline
        const ctx4 = getCtx(this.appointmentTimelineRef);
        if (ctx4) {
            this.charts.timeline = new ChartConstructor(ctx4, {
                type: 'bar',
                data: {
                    labels: this.state.charts.timeline.labels,
                    datasets: [{
                        label: 'Appointments',
                        data: this.state.charts.timeline.data,
                        backgroundColor: 'rgba(16, 185, 129, 0.7)',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });
        }

        // Diagnosis
        const ctx5 = getCtx(this.diagnosisChartRef);
        if (ctx5) {
            this.charts.diagnosis = new ChartConstructor(ctx5, {
                type: 'bar',
                data: {
                    labels: this.state.charts.diagnosis.labels,
                    datasets: [{
                        label: 'Cases',
                        data: this.state.charts.diagnosis.data,
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: { legend: { display: false } }
                }
            });
        }

        // Revenue Breakdown
        const ctx6 = getCtx(this.revenueBreakdownChartRef);
        if (ctx6 && this.state.charts.revenue_breakdown) {
            this.charts.revenueBreakdown = new ChartConstructor(ctx6, {
                type: 'pie',
                data: {
                    labels: this.state.charts.revenue_breakdown.labels,
                    datasets: [{
                        data: this.state.charts.revenue_breakdown.data,
                        backgroundColor: [
                            'rgba(59, 130, 246, 0.7)', // Blue
                            'rgba(16, 185, 129, 0.7)', // Green
                            'rgba(249, 168, 37, 0.7)', // Yellow
                            'rgba(244, 114, 182, 0.7)' // Pink
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right' } }
                }
            });
        }
    }

    formatCurrency(value) {
        const currency = this.state.kpi.currency_name || 'USD';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency }).format(value || 0);
    }
}

OpticalDashboard.template = "BP_Optical_solution.OpticalDashboard";
registry.category("actions").add("optical_dashboard", OpticalDashboard);
