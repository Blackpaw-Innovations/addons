from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def update_stages(env):
    # Map XML IDs to states
    mapping = {
        'bp_mwanzo_marketplace.stage_draft': 'draft',
        'bp_mwanzo_marketplace.stage_active': 'active',
        'bp_mwanzo_marketplace.stage_expired': 'expired',
        'bp_mwanzo_marketplace.stage_cancelled': 'cancelled',
    }
    
    for xml_id, state in mapping.items():
        stage = env.ref(xml_id, raise_if_not_found=False)
        if stage:
            stage.target_state = state
            _logger.info(f"Updated stage {stage.name} with target_state {state}")
        else:
            _logger.warning(f"Stage {xml_id} not found")

    env.cr.commit()

if __name__ == "__main__":
    # This part is for running via shell, but we'll call the function from a shell script or just run this file
    pass
