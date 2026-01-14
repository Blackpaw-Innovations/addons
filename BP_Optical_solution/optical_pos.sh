#!/bin/bash

# Check if database name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <database_name>"
    echo "Example: ./optical_pos.sh my_database"
    exit 1
fi

DB_NAME=$1

echo "--------------------------------------------------"
echo "Deploying BP_Optical_solution..."
echo "--------------------------------------------------"

# 1. Copy the module to the addons directory
echo "Copying module files..."
sudo cp -r /home/blackpaw/blackpaw_addons/BP_Optical_solution /opt/odoo/addons/
sudo chown -R odoo:odoo /opt/odoo/addons/BP_Optical_solution

# 2. Restart Odoo service
echo "Restarting Odoo service..."
sudo systemctl restart odoo

# 3. Upgrade the module via CLI
echo "Upgrading BP_Optical_solution on database: $DB_NAME"
sudo -u odoo /opt/odoo/odoo-bin -c /etc/odoo.conf -d "$DB_NAME" -u BP_Optical_solution --stop-after-init

# 4. Check status with no pager
echo "Checking service status..."
sudo systemctl status odoo --no-pager

echo "--------------------------------------------------"
echo "Deployment Complete"
echo "--------------------------------------------------"
