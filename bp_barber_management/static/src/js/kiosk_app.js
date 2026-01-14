/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class BarberKioskApp extends Component {
    static template = "bp_barber_management.kiosk_app_template";

    setup() {
        // Get configuration from DOM attributes
        const container = document.getElementById('bp-barber-kiosk');
        this.config = {
            token: container.dataset.token || null,
            refreshSeconds: parseInt(container.dataset.refreshSeconds || '10'),
            baseUrl: container.dataset.baseUrl || '',
            companyName: container.dataset.companyName || 'Barber Shop',
            companyLogo: container.dataset.companyLogo || null
        };

        this.state = useState({
            loading: true,
            error: null,
            reconnecting: false,
            lastUpdate: null,
            currentTime: new Date(),
            data: {
                server_time: null,
                barbers: []
            }
        });

        this.refreshInterval = null;
        this.clockInterval = null;

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            // Hide loading indicator
            const loadingEl = document.getElementById('kiosk-loading');
            if (loadingEl) {
                loadingEl.style.display = 'none';
            }

            // Start refresh interval
            this.startRefreshInterval();

            // Start clock update
            this.startClockUpdate();
        });

        onWillUnmount(() => {
            this.stopIntervals();
        });
    }

    startRefreshInterval() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.refreshInterval = setInterval(() => {
            this.loadData();
        }, this.config.refreshSeconds * 1000);
    }

    startClockUpdate() {
        if (this.clockInterval) {
            clearInterval(this.clockInterval);
        }

        this.clockInterval = setInterval(() => {
            this.state.currentTime = new Date();
        }, 1000);
    }

    stopIntervals() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        if (this.clockInterval) {
            clearInterval(this.clockInterval);
            this.clockInterval = null;
        }
    }

    async loadData() {
        try {
            this.state.reconnecting = this.state.data.barbers.length > 0;

            const payload = {};
            if (this.config.token) {
                payload.token = this.config.token;
            }

            const response = await fetch('/barber/kiosk/data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.state.data = data;
            this.state.lastUpdate = new Date();
            this.state.error = null;
            this.state.loading = false;
            this.state.reconnecting = false;

        } catch (error) {
            console.error('Error loading kiosk data:', error);
            this.state.error = error.message;
            this.state.loading = false;
            this.state.reconnecting = false;

            // Show error for 5 seconds, then try again
            setTimeout(() => {
                if (this.state.error) {
                    this.state.error = null;
                    this.loadData();
                }
            }, 5000);
        }
    }

    // Helper methods for template
    formatTime(timeStr) {
        if (!timeStr) return '';
        const date = new Date(timeStr);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    }

    formatTimeRange(startStr, endStr) {
        if (!startStr || !endStr) return '';
        return `${this.formatTime(startStr)}–${this.formatTime(endStr)}`;
    }

    getCustomerDisplayName(fullName) {
        if (!fullName || fullName === 'Walk-in') {
            return 'Walk-in';
        }

        const parts = fullName.trim().split(/\s+/);
        if (parts.length === 1) {
            return parts[0];
        }

        // Return first name + last initial
        const firstName = parts[0];
        const lastInitial = parts[parts.length - 1].charAt(0).toUpperCase();
        return `${firstName} ${lastInitial}.`;
    }

    getRemainingTimeDisplay(remainingMin) {
        if (remainingMin <= 0) return 'Finishing up';
        if (remainingMin === 1) return '1 min remaining';
        return `${remainingMin} min remaining`;
    }

    getETADisplay(etaMin) {
        if (etaMin <= 0) return 'Now';
        if (etaMin < 60) return `${etaMin} min`;
        const hours = Math.floor(etaMin / 60);
        const minutes = etaMin % 60;
        return `${hours}h ${minutes}min`;
    }

    getBarberColorClass(colorIndex) {
        const colors = [
            'barber-color-1', 'barber-color-2', 'barber-color-3',
            'barber-color-4', 'barber-color-5', 'barber-color-6',
            'barber-color-7', 'barber-color-8', 'barber-color-9', 'barber-color-10'
        ];
        return colors[(colorIndex - 1) % colors.length] || colors[0];
    }

    getCurrentTimeDisplay() {
        return this.state.currentTime.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }

    getCurrentDateDisplay() {
        return this.state.currentTime.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    get hasBarbers() {
        return this.state.data.barbers && this.state.data.barbers.length > 0;
    }

    get activeBarbersCount() {
        if (!this.hasBarbers) return 0;
        return this.state.data.barbers.filter(b => b.now || b.next.length > 0).length;
    }
}

// Auto-mount the kiosk app when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('bp-barber-kiosk');
    if (container) {
        try {
            const app = new BarberKioskApp();
            app.mount(container);
        } catch (error) {
            console.error('Failed to mount kiosk app:', error);
            // Show error fallback
            document.getElementById('kiosk-loading').style.display = 'none';
            document.getElementById('kiosk-error').style.display = 'block';
        }
    }
});

export default BarberKioskApp;