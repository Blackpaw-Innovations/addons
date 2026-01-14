
import sys
# env is already available in the shell context

def cleanup_stages():
    print("Starting stage cleanup...")
    
    # Define the mapping of names to XML IDs
    stage_mapping = {
        'Test Room': 'BP_Optical_solution.optical_stage_test_room',
        'Fitting': 'BP_Optical_solution.optical_stage_fitting',
        'Ready For collection': 'BP_Optical_solution.optical_stage_ready',
        'Completed': 'BP_Optical_solution.optical_stage_completed',
    }
    
    # Get the IDs of the stages defined in XML
    keep_stage_ids = []
    for name, xml_id in stage_mapping.items():
        stage = env.ref(xml_id, raise_if_not_found=False)
        if stage:
            keep_stage_ids.append(stage.id)
        else:
            print(f"WARNING: XML Stage {xml_id} not found!")

    if not keep_stage_ids:
        print("No XML stages found. Aborting.")
        return

    # Find all stages
    Stage = env['optical.prescription.stage']
    all_stages = Stage.search([])
    
    # Identify stages to remove (those not in the keep list)
    stages_to_remove = all_stages.filtered(lambda s: s.id not in keep_stage_ids)
    
    print(f"Found {len(all_stages)} total stages.")
    print(f"Keeping {len(keep_stage_ids)} stages (XML defined).")
    print(f"Removing {len(stages_to_remove)} duplicate stages.")
    
    for stage in stages_to_remove:
        print(f"Processing duplicate stage: '{stage.name}' (ID: {stage.id})")
        
        # Find the correct stage to move tests to
        target_xml_id = stage_mapping.get(stage.name)
        target_stage = env.ref(target_xml_id, raise_if_not_found=False) if target_xml_id else None
        
        if target_stage:
            # Move tests
            tests = env['optical.test'].search([('stage_id', '=', stage.id)])
            if tests:
                print(f"  Moving {len(tests)} tests from ID {stage.id} to ID {target_stage.id}")
                tests.write({'stage_id': target_stage.id})
            
            # Delete the duplicate stage
            print(f"  Deleting stage ID {stage.id}")
            stage.unlink()
        else:
            print(f"  SKIPPING deletion of '{stage.name}' (ID: {stage.id}) - No matching XML stage found to migrate data to.")

    env.cr.commit()
    print("Cleanup complete.")

cleanup_stages()
