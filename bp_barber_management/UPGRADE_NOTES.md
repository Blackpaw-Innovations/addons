# Upgrade Notes

## Overview

This document provides safe upgrade procedures for the Barber Management module between versions. Always backup your database before performing any upgrades.

## Version 17.0.1.0.0 → 17.0.2.0.0

### Upgrade Safety
✅ **SAFE UPGRADE** - No database schema changes  
✅ No data migration required  
✅ No breaking changes to existing functionality  

### Pre-Upgrade Checklist

1. **Database Backup**
   ```bash
   # Create full database backup
   pg_dump -h localhost -U odoo -d your_database_name > backup_pre_upgrade_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **System Requirements Check**
   - Odoo 17.0 Community or Enterprise
   - PostgreSQL 12+ 
   - Python 3.8+
   - Sufficient disk space for upgrade process

3. **Maintenance Window**
   - Schedule upgrade during off-peak hours
   - Notify users of planned maintenance
   - Ensure no active appointments during upgrade window

### Upgrade Procedure

1. **Stop Odoo Service**
   ```bash
   sudo systemctl stop odoo
   ```

2. **Backup Current Module**
   ```bash
   cp -r /opt/odoo/addons/bp_barber_management /opt/odoo/addons/bp_barber_management.backup
   ```

3. **Update Module Files**
   ```bash
   cd /opt/odoo/addons
   git pull origin main
   # Or copy new module files manually
   ```

4. **Restart Odoo and Upgrade**
   ```bash
   sudo systemctl start odoo
   odoo -d your_database_name -u bp_barber_management
   ```

### Post-Upgrade Validation

#### 1. Core Functionality Check
- [ ] **Appointments**: Create and manage appointments
- [ ] **POS Integration**: Process service payments through POS
- [ ] **Website Booking**: Test online appointment booking
- [ ] **Package System**: Verify wallet balance and redemptions work

#### 2. Asset Verification
Run the following checks to ensure all UI components loaded correctly:

- [ ] **POS Assets**: Open POS session, verify Appointments pane displays
- [ ] **Website Assets**: Navigate to `/barber/booking`, confirm booking form loads
- [ ] **Backend Views**: Check all Barber menu items display properly
- [ ] **Dashboard**: Verify analytics dashboard charts render

#### 3. Integration Testing
- [ ] **Email Notifications**: Send test appointment confirmation
- [ ] **Kiosk Display**: If enabled, verify queue screen updates
- [ ] **Cron Jobs**: Check scheduled tasks are active

#### 4. Performance Verification
After Stage 15 upgrade, new database indexes should improve query performance:

```bash
# Check if indexes were created (PostgreSQL)
psql -d your_database_name -c "
SELECT indexname FROM pg_indexes 
WHERE indexname LIKE 'idx_bp_%' 
ORDER BY indexname;
"
```

Expected indexes:
- `idx_bp_appt_company_state_start`
- `idx_bp_appt_barber_start`
- `idx_pos_order_line_barber`
- `idx_bp_cons_usage_barber_date`

### Asset Rebuild (If Needed)

If UI assets don't load properly after upgrade:

```bash
# Development mode (rebuilds all assets)
odoo -d your_database_name --dev=all

# Or upgrade specific asset bundles
odoo -d your_database_name -u web,point_of_sale,website
```

### New Features in 17.0.2.0.0

After successful upgrade, you'll have access to:

1. **Enhanced Documentation**: Updated README and help content
2. **Deployment Tools**: Production-ready configuration examples in `ops/` folder
3. **Quality Tools**: Linting and testing helpers via Makefile
4. **CI Integration**: GitHub Actions for automated testing

### Rollback Procedure

If issues occur during upgrade:

1. **Stop Odoo**
   ```bash
   sudo systemctl stop odoo
   ```

2. **Restore Database**
   ```bash
   dropdb your_database_name
   createdb your_database_name
   psql -d your_database_name < backup_pre_upgrade_YYYYMMDD_HHMMSS.sql
   ```

3. **Restore Module Files**
   ```bash
   rm -rf /opt/odoo/addons/bp_barber_management
   mv /opt/odoo/addons/bp_barber_management.backup /opt/odoo/addons/bp_barber_management
   ```

4. **Restart Odoo**
   ```bash
   sudo systemctl start odoo
   ```

### Troubleshooting

#### Common Issues

**1. Asset Loading Problems**
- **Symptom**: POS or website pages show broken layouts
- **Solution**: Clear browser cache and rebuild assets
- **Command**: `odoo -d your_db --dev=all` (development mode)

**2. Permission Errors**
- **Symptom**: Users can't access new maintenance features
- **Solution**: Update user groups and permissions
- **Action**: Assign "Barber Manager" group for maintenance access

**3. Cron Jobs Not Running**
- **Symptom**: Automated reminders or archiving not working
- **Solution**: Verify cron jobs are active
- **Check**: Settings → Technical → Automated Actions

**4. Performance Degradation**
- **Symptom**: Slower appointment searches
- **Solution**: Verify database indexes were created
- **Check**: Run performance verification SQL above

#### Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Review Odoo logs for error messages
2. **GitHub Issues**: Search existing issues or create new one
3. **Professional Support**: Contact Blackpaw Innovations for paid support

### Best Practices

#### Before Each Upgrade
- Test upgrade on staging environment first
- Review CHANGELOG.md for breaking changes
- Coordinate with barbers to minimize disruption
- Have rollback plan ready

#### After Each Upgrade
- Monitor system performance for 24 hours
- Validate all critical business processes
- Train staff on any new features
- Update internal documentation

### Version-Specific Notes

#### From 17.0.1.0.0
- First production upgrade
- All new installations after 17.0.2.0.0 include full feature set
- No configuration migration needed

### Support Information

**Documentation**: See README.md, SECURITY.md, CONTRIBUTING.md  
**Professional Support**: [Blackpaw Innovations](https://blackpawinnovations.com)  
**Issue Reporting**: [GitHub Issues](https://github.com/Blackpaw-Innovations/bp-fuel-solution/issues)  
**Community Support**: GitHub Discussions

---

*Always test upgrades in a development environment before applying to production systems.*