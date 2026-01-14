#!/bin/bash

# Deployment script for BP Optical Core module
# This script copies the module to Odoo addons directory and upgrades it

echo "========================================"
echo "BP Optical Core Deployment Script"
echo "========================================"

# 1. Copy module to Odoo addons directory
echo "Step 1: Copying module to /opt/odoo/addons..."
sudo cp -r /home/blackpaw/blackpaw_addons/BP_Optical_solution /opt/odoo/addons/

# 2. Restart Odoo service
echo "Step 2: Restarting Odoo service..."
sudo systemctl restart odoo

# Wait for Odoo to start
echo "Waiting for Odoo to start (15 seconds)..."
sleep 15

# 3. Upgrade module via CLI
echo "Step 3: Upgrading BP_Optical_solution module in Optical database..."
sudo -u odoo /usr/bin/python3 /opt/odoo/odoo-bin -c /etc/odoo.conf -d Optical -u BP_Optical_solution --stop-after-init

# 4. Check Odoo service status (no pager)
echo "Step 4: Checking Odoo service status..."
sudo systemctl status odoo --no-pager

echo "========================================"
echo "Deployment complete!"
echo "========================================"
