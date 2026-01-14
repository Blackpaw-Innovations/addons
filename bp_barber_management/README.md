# Barber Management for Odoo 17

[![Odoo 17](https://img.shields.io/badge/Odoo-17.0-875A7B.svg)](https://www.odoo.com/)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL%203.0-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Tested on Linux](https://img.shields.io/badge/Tested%20on-Linux-green.svg)]()

Complete barbershop management system for Odoo 17 with appointments, POS integration, packages, consumables tracking, analytics, and maintenance tools.

## Features

### Core Management (Stages 1-5)
- **Services & Barbers**: Complete barber and service catalog management
- **Chairs & Scheduling**: Chair assignments and barber availability schedules  
- **Appointments**: Full appointment lifecycle with states and customer management
- **Website Booking**: Online appointment booking with real-time availability
- **POS Integration**: Seamless point-of-sale integration with barber assignments

### Advanced Features (Stages 6-10)
- **Commissions**: Flexible commission rules (global, service-specific, category-based)
- **Service Packages**: Pre-paid service packages with wallet management
- **Consumables Tracking**: Bill of Materials for services and usage monitoring
- **Package Wallets**: Customer package purchases with expiry and redemption tracking
- **Analytics Dashboard**: Comprehensive KPI reporting and business insights

### Customer Experience (Stages 11-15) 
- **KPIs & Reporting**: Revenue, commission, and performance analytics
- **Interactive Dashboard**: Real-time business metrics and charts
- **Kiosk/TV Queue**: Queue management system for waiting customers
- **Email Notifications**: Automated appointment confirmations and reminders
- **Maintenance Tools**: Data integrity checks, archiving, and performance optimization

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Website       │    │   Appointments  │    │   POS System    │
│   Booking       │───▶│   Management    │◀──▶│   Integration   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Core Business Logic                         │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Consumables   │   Commissions   │      Service Packages       │
│   & Supplies    │   & Statements  │      & Wallets             │
├─────────────────┴─────────────────┴─────────────────────────────┤
│              Analytics & Maintenance                            │
│         (KPIs, Dashboard, Queue, Notifications)                │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Requirements
- Odoo 17.0 Community or Enterprise
- PostgreSQL 12+ 
- Python 3.8+
- Required Odoo modules: `base`, `mail`, `web`, `point_of_sale`, `website`

### Install Steps

1. **Clone the repository**:
```bash
cd /opt/odoo/addons
git clone https://github.com/Blackpaw-Innovations/bp-fuel-solution.git
```

2. **Install the module**:
```bash
odoo -d your_database -i bp_barber_management
```

### Upgrade

```bash
odoo -d your_database -u bp_barber_management
```

**Important**: Read `UPGRADE_NOTES.md` before upgrading between versions.

## Configuration

### Quick Setup
1. **Enable Barber Mode** in POS: Settings → Point of Sale → Configuration
2. **Configure Website Booking**: Website → Configuration → Barber Booking  
3. **Setup Kiosk Display** (optional): Barber → Kiosk Settings
4. **Enable Notifications**: Settings → Barber Notifications

### Initial Data
1. Create barbers and chairs: Barber → Barbers/Chairs
2. Define services: Barber → Services  
3. Set up schedules: Barber → Schedules
4. Configure commission rules: Barber → Commissions → Rules

## Demo Data

Includes sample data for:

### Services
- **Haircut** (CUT) - $10.00, 30 minutes
- **Shave** (SHV) - $6.00, 20 minutes  
- **Cut + Shave** (CNS) - $15.00, 50 minutes
- **Beard Trim** (BRD) - $7.00, 20 minutes
- **Kids Cut** (KID) - $8.00, 25 minutes

*Note: Each service automatically creates a corresponding POS product for point-of-sale integration.*

### Staff & Equipment
- **Chairs**: Chair 1 (C1), Chair 2 (C2)
- **Barbers**: 
  - John Barber (JBN) - Senior barber on Chair 1
  - Mary Stylist (MRS) - Mid-level stylist on Chair 2  
  - Alex Fade (ALX) - Junior barber (no assigned chair)

### Schedules
- John & Mary work Monday-Saturday, 09:00-18:00
- Fully configured for online booking system

### Sample Appointments
- Confirmed appointment for Mary at 10:00
- Draft appointment for John at 14:00
- In-service appointment for John at 11:00 (demonstrates POS integration)

- 3 sample barbers with different specialties
- 5 common barbershop services  
- Pre-configured schedules and availability
- Sample service packages and consumable BOMs
- POS configuration examples

Enable with: `--demo=bp_barber_management`

## Testing

### Run Tests
```bash
# Full test suite
odoo --test-enable -i bp_barber_management --stop-after-init

# Specific test tags  
odoo --test-tags=bp_barber_management --stop-after-init
```

### Continuous Integration
This module includes GitHub Actions CI that runs tests on every push and pull request.

## Documentation

- `CHANGELOG.md` - Version history and changes
- `UPGRADE_NOTES.md` - Safe upgrade procedures  
- `SECURITY.md` - Security policy and vulnerability reporting
- `CONTRIBUTING.md` - Development guidelines and contribution process
- `ops/` - Production deployment scripts and configuration examples

## Support

**Blackpaw Innovations**
- Website: https://blackpawinnovations.com
- Email: support@blackpawinnovations.com

For bugs and feature requests, please use the GitHub issue tracker.

## License

This module is licensed under LGPL-3.0 - see `LICENSE` file for details.

---

*Complete barbershop management made simple with Odoo 17* ✂️

## Author

**Blackpaw Innovations**  
Website: [blackpawinnovations.com](https://blackpawinnovations.com)

Professional Odoo Development & Implementation