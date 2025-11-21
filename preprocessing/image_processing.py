import cv2
import math
import numpy as np
import os
import re
import shutil
import yaml
from PIL import Image

###################################################
######### IMAGE PROCESSING MAIN FUNCTIONS #########
###################################################

# Called in step 2 of wrapper.py to convert AVI videos to IX format and create HTD file
def avi_to_ix(g):
    # Get all AVI files in the plate directory
    avi_files = [os.path.join(g.plate_dir, f) for f in os.listdir(g.plate_dir) if f.endswith('.avi')]
    
    # Case: only 1 AVI file for the entire plate
    if len(avi_files) == 1:
        vid_path = avi_files[0]
        vid = cv2.VideoCapture(str(vid_path))
        ret = True
        frames = []
        frame_counter = 0
        
        # Apply frame skipping if enabled
        if g.frame_skipping_enabled:
            print(f"Frame skipping enabled: processing every {g.frame_skip_interval} frame(s)")
            while ret:
                ret, img = vid.read()
                if ret:
                    frame_counter += 1
                    # Only process frames according to skip interval
                    if (frame_counter - 1) % g.frame_skip_interval == 0:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('uint16')
                        frames.append(img)
                        
                        # Check frame cap
                        if g.frame_cap_enabled and len(frames) >= g.frame_cap_max_frames:
                            print(f"Frame cap reached: stopping at {len(frames)} frames")
                            break
        else:
            # Original behavior - process all frames
            while ret:
                ret, img = vid.read()
                if ret:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('uint16')
                    frames.append(img)
                    
                    # Check frame cap
                    if g.frame_cap_enabled and len(frames) >= g.frame_cap_max_frames:
                        print(f"Frame cap reached: stopping at {len(frames)} frames")
                        break
        
        timepoints = len(frames)
        print("Converting AVI to ImageXpress format.")
        if g.frame_skipping_enabled:
            print(f"Processing {timepoints} frames (skipped {frame_counter - timepoints} frames)")
        
        # Save each frame into TimePoint directories
        for timepoint in range(timepoints):
            if timepoint % 50 == 0:
                print(f"Converting timepoint {timepoint + 1} of {timepoints}.")
            dir = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}')
            if os.path.isdir(dir):
                shutil.rmtree(dir)
            os.makedirs(dir)
            # Save frame with '_A01_w1' to maintain original naming
            outpath = os.path.join(dir, g.plate + f'_A01_w1.TIF')
            cv2.imwrite(str(outpath), frames[timepoint])
    
    else:
        # Case: multiple AVI files, one per well
        well_names = [re.search(r'_(\D\d{2})\.avi$', os.path.basename(f)).group(1) for f in avi_files]  # Extract well names
        timepoints = 0
        for avi_file, well in zip(avi_files, well_names):
            vid = cv2.VideoCapture(avi_file)
            ret = True
            frames = []
            frame_counter = 0
            
            # Apply frame skipping if enabled
            if g.frame_skipping_enabled:
                print(f"Frame skipping enabled for {well}: processing every {g.frame_skip_interval} frame(s)")
                while ret:
                    ret, img = vid.read()
                    if ret:
                        frame_counter += 1
                        # Only process frames according to skip interval
                        if (frame_counter - 1) % g.frame_skip_interval == 0:
                            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('uint16')
                            frames.append(img)
                            
                            # Check frame cap
                            if g.frame_cap_enabled and len(frames) >= g.frame_cap_max_frames:
                                print(f"Frame cap reached for {well}: stopping at {len(frames)} frames")
                                break
            else:
                # Original behavior - process all frames
                while ret:
                    ret, img = vid.read()
                    if ret:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('uint16')
                        frames.append(img)
                        
                        # Check frame cap
                        if g.frame_cap_enabled and len(frames) >= g.frame_cap_max_frames:
                            print(f"Frame cap reached for {well}: stopping at {len(frames)} frames")
                            break
            
            current_timepoints = len(frames)
            if timepoints == 0:
                timepoints = current_timepoints  # Set timepoints based on first AVI
            elif current_timepoints != timepoints:
                print(f"Warning: Well {well} has {current_timepoints} frames, expected {timepoints}")
                timepoints = min(timepoints, current_timepoints)  # Use minimum to avoid errors
            
            # Loop through each timepoint and save frames for each well
            print(f"Converting AVI to ImageXpress format for well {well}.")
            if g.frame_skipping_enabled:
                print(f"Processing {current_timepoints} frames for {well} (skipped {frame_counter - current_timepoints} frames)")
            for timepoint in range(current_timepoints):
                if timepoint % 50 == 0:
                    print(f"Converting timepoint {timepoint + 1} of {current_timepoints} for well {well}.")
                dir = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}')
                if not os.path.isdir(dir):
                    os.makedirs(dir)  # Create timepoint directory if not already made
                # Save the frame with well name appended
                outpath = os.path.join(dir, f"{g.plate}_{well}_w1.TIF")
                cv2.imwrite(str(outpath), frames[timepoint])

    # Clean up any incomplete timepoint directories caused by extra frames
    if len(avi_files) == 1:
        # Single AVI case - expect 1 file per timepoint
        final_timepoints = __cleanup_incomplete_timepoints(g, 1)
    else:
        # Multiple AVI case - expect one file per well per timepoint
        final_timepoints = __cleanup_incomplete_timepoints(g, len(well_names))
    
    # Update the timepoints value to reflect actual complete timepoints
    if final_timepoints != timepoints:
        print(f"Updated timepoints from {timepoints} to {final_timepoints} after cleanup")
        timepoints = final_timepoints
    
    # Create HTD file with final timepoint count
    __create_htd(g, timepoints, source="AVI")
    
    return timepoints

# Called in step 2 of wrapper.py to convert loopbio (multi-camera array) videos to IX format and create HTD file
def loopbio_to_ix(g, camera_mapping, rotations):
    print("Converting LoopBio MP4 files to ImageXpress format.")
    
    # Find all camera directories in the plate directory
    # Skip TimePoint directories from previous runs
    camera_dirs = []
    for item in os.listdir(g.plate_dir):
        item_path = os.path.join(g.plate_dir, item)
        if os.path.isdir(item_path) and not item.startswith('TimePoint_'):
            camera_dirs.append(item_path)
    
    if not camera_dirs:
        raise ValueError(f"No camera directories found in {g.plate_dir}")
    
    timepoints = 0
    processed_wells = {}
    
    # Process each camera directory one at a time
    for camera_dir in camera_dirs:
        # Extract camera serial from directory name (last part after '.')
        dir_name = os.path.basename(camera_dir)
        try:
            camera_serial = dir_name.split('.')[-1]
        except:
            print(f"Warning: Could not extract camera serial from directory {dir_name}")
            continue
        
        # Check if this camera serial is in our mapping
        if int(camera_serial) not in camera_mapping:
            print(f"Warning: Camera serial {camera_serial} not found in mapping, skipping")
            continue
        
        well_position = camera_mapping[int(camera_serial)]
        
        # Find MP4 file in camera directory
        mp4_file = os.path.join(camera_dir, '000000.mp4')
        metadata_file = os.path.join(camera_dir, 'metadata.yaml')
        
        if not os.path.exists(mp4_file):
            print(f"Warning: MP4 file not found in {camera_dir}")
            continue
        
        # Validate metadata if it exists
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = yaml.safe_load(f)
                    if metadata.get('title') != g.plate:
                        print(f"Warning: Metadata title '{metadata.get('title')}' doesn't match plate name '{g.plate}'")
            except Exception as e:
                print(f"Warning: Could not read metadata from {metadata_file}: {e}")
        
        # Process MP4 file 
        print(f"Processing camera {camera_serial} -> well {well_position}")
        vid = cv2.VideoCapture(mp4_file)
        if not vid.isOpened():
            print(f"Error: Could not open MP4 file {mp4_file}")
            continue
        
        # Process frames one at a time and write immediately (like avi_to_ix)
        current_timepoint = 0
        frame_counter = 0
        ret = True
        
        # Apply frame skipping if enabled
        if g.frame_skipping_enabled:
            print(f"Frame skipping enabled for {well_position}: processing every {g.frame_skip_interval} frame(s)")
            while ret:
                ret, img = vid.read()
                if ret:
                    frame_counter += 1
                    # Only process frames according to skip interval
                    if (frame_counter - 1) % g.frame_skip_interval == 0:
                        current_timepoint += 1
                        
                        # Convert to grayscale and uint16
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('uint16')
                        
                        # Apply rotation if this well needs it
                        if well_position in rotations:
                            img = cv2.rotate(img, cv2.ROTATE_180)
                        
                        # Progress indicator
                        if current_timepoint % 50 == 0:
                            print(f"Converting timepoint {current_timepoint} for well {well_position}")
                        
                        # Create timepoint directory if it doesn't exist
                        timepoint_dir = os.path.join(g.plate_dir, f'TimePoint_{current_timepoint}')
                        os.makedirs(timepoint_dir, exist_ok=True)
                        
                        # Save frame immediately with proper naming convention
                        outpath = os.path.join(timepoint_dir, f"{g.plate}_{well_position}_w1.TIF")
                        cv2.imwrite(outpath, img)
                        
                        # Check frame cap
                        if g.frame_cap_enabled and current_timepoint >= g.frame_cap_max_frames:
                            print(f"Frame cap reached for {well_position}: stopping at {current_timepoint} frames")
                            break
        else:
            # Original behavior - process all frames
            while ret:
                ret, img = vid.read()
                if ret:
                    current_timepoint += 1
                    
                    # Convert to grayscale and uint16
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('uint16')
                    
                    # Apply rotation if this well needs it
                    if well_position in rotations:
                        img = cv2.rotate(img, cv2.ROTATE_180)
                    
                    # Progress indicator
                    if current_timepoint % 50 == 0:
                        print(f"Converting timepoint {current_timepoint} for well {well_position}")
                    
                    # Create timepoint directory if it doesn't exist
                    timepoint_dir = os.path.join(g.plate_dir, f'TimePoint_{current_timepoint}')
                    os.makedirs(timepoint_dir, exist_ok=True)
                    
                    # Save frame immediately with proper naming convention
                    outpath = os.path.join(timepoint_dir, f"{g.plate}_{well_position}_w1.TIF")
                    cv2.imwrite(outpath, img)
                    
                    # Check frame cap
                    if g.frame_cap_enabled and current_timepoint >= g.frame_cap_max_frames:
                        print(f"Frame cap reached for {well_position}: stopping at {current_timepoint} frames")
                        break
        
        vid.release()
        
        # Set timepoints based on first processed camera
        if timepoints == 0:
            timepoints = current_timepoint
        elif current_timepoint != timepoints:
            print(f"Warning: Camera {camera_serial} has {current_timepoint} frames, expected {timepoints}")
            # Use the minimum to avoid index errors
            timepoints = min(timepoints, current_timepoint)
        
        processed_wells[well_position] = camera_serial
        if g.frame_skipping_enabled:
            print(f"Completed processing camera {camera_serial} -> well {well_position} ({current_timepoint} frames, skipped {frame_counter - current_timepoint} frames)")
        else:
            print(f"Completed processing camera {camera_serial} -> well {well_position} ({current_timepoint} frames)")
    
    # Clean up any incomplete timepoint directories caused by extra frames
    final_timepoints = __cleanup_incomplete_timepoints(g, len(processed_wells))
    
    # Update the timepoints value to reflect actual complete timepoints
    if final_timepoints != timepoints:
        print(f"Updated timepoints from {timepoints} to {final_timepoints} after cleanup")
        timepoints = final_timepoints
    
    # Create HTD file with final timepoint count
    __create_htd(g, timepoints, source="LoopBio")
    
    print(f"Successfully processed {len(processed_wells)} cameras with {timepoints} complete timepoints")
    print(f"Processed wells: {list(processed_wells.keys())}")
    
    return timepoints

# Splits multi-well images into individual wells using a grid layout.  
# Supports masking and both single- and multi-well modes.
# Called after conversion to IX format and HTDs are parsed
def grid_crop(g):
    rows_per_image = g.rows // g.rec_rows
    cols_per_image = g.cols // g.rec_cols

    # Check if we need to use crop directory (multi-well mode)
    if g.mode == "multi-well":
        print("Multi-well mode detected. Using crop directory to prevent file overwriting.")
        
        # 1. Create crop directory in work folder
        crop_dir = os.path.join(g.work, 'crop')
        os.makedirs(crop_dir, exist_ok=True)
        
        # 2. Copy input images to crop directory for processing
        for timepoint in range(g.time_points):
            input_timepoint_dir = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}')
            crop_timepoint_dir = os.path.join(crop_dir, f'TimePoint_{timepoint + 1}')
            
            if os.path.exists(input_timepoint_dir):
                # Create timepoint directory in crop folder
                os.makedirs(crop_timepoint_dir, exist_ok=True)
                
                # Copy all images to crop directory
                for filename in os.listdir(input_timepoint_dir):
                    if filename.lower().endswith(('.tif', '.tiff')):
                        src_path = os.path.join(input_timepoint_dir, filename)
                        dst_path = os.path.join(crop_timepoint_dir, filename)
                        shutil.copy2(src_path, dst_path)
        
        # 3. Perform cropping operations in crop directory
        for timepoint in range(g.time_points):
            crop_timepoint_dir = os.path.join(crop_dir, f'TimePoint_{timepoint + 1}')
            if not os.path.exists(crop_timepoint_dir):
                continue
                
            original_images = os.listdir(crop_timepoint_dir)

            # loop through each image in crop timepoint folder
            for current in original_images:
                # get path of current image in crop directory
                current_path = os.path.join(crop_timepoint_dir, current)
                # skip over if file does not exist
                if not os.path.exists(current_path):
                    continue

                # conversion of the well name to an array - A01 becomes [0, 0] where the format is [row, col]
                # group refers to group of wells to be split (for example splitting the group A01 into a 2x2 would result in wells A01, A02, B01, and B02)
                # get group_id using regex by extracting column letter and row number from current
                letter, number, site, wavelength = extract_well_name(current)
                if letter is None:  # Skip files that don't match the expected image naming pattern
                    continue
                group_id = [__capital_to_num(letter), int(number) - 1]

                # split image into individual wells (this deletes the original multi-well image in crop directory)
                individual_wells = __split_image(current_path, cols_per_image, rows_per_image)

                # loop through individual well images and save with corresponding well name in crop directory
                for i in range(rows_per_image):
                    for j in range(cols_per_image):
                        well_name = __generate_well_name(g, group_id, j, i, cols_per_image, rows_per_image)
                        
                        # Skip if well_name is None (shouldn't happen but safety check)
                        if well_name is None:
                            print(f"    ERROR: well_name is None for sub-well [{i},{j}]")
                            continue
                            
                        # save current image as well name in crop directory
                        # Use a unique temporary filename during cropping to prevent overwrites
                        temp_filename = f"{current.replace('.TIF', '')}_{well_name}_temp.TIF"
                        temp_outpath = os.path.join(crop_timepoint_dir, temp_filename)
                        
                        # Final filename for transfer back
                        if site:
                            final_filename = g.plate_short + f'_{well_name}_s{site}_w{wavelength}.TIF'
                        else:
                            final_filename = g.plate_short + f'_{well_name}_w{wavelength}.TIF'
                        
                        try:
                            if g.circle_diameter != 'NA':
                                __apply_mask(individual_wells[i * cols_per_image + j], g.circle_diameter, 'circle').save(temp_outpath)
                            elif g.square_side != 'NA':
                                __apply_mask(individual_wells[i * cols_per_image + j], g.square_side, 'square').save(temp_outpath)
                            else:
                                individual_wells[i * cols_per_image + j].save(temp_outpath)

                        except Exception as e:
                            print(f"    ERROR saving {well_name}: {e}")
        
        # 4. Transfer cropped images back to input directory (overwriting multi-well images)
        print("Transferring cropped individual well images back to input directory.")
        for timepoint in range(g.time_points):
            input_timepoint_dir = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}')
            crop_timepoint_dir = os.path.join(crop_dir, f'TimePoint_{timepoint + 1}')
            
            if os.path.exists(crop_timepoint_dir):
                # Remove all existing files in input timepoint directory
                for filename in os.listdir(input_timepoint_dir):
                    file_path = os.path.join(input_timepoint_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                
                # Copy all cropped images from crop directory to input directory with proper renaming
                for filename in os.listdir(crop_timepoint_dir):
                    if filename.lower().endswith(('.tif', '.tiff')) and '_temp.TIF' in filename:
                        # Extract the well name and construct the final filename
                        # Temp filename format: "20250813-p01-MZ_A01_w1_A01_temp.TIF"
                        # Final filename format: "20250813-p01-MZ_A01_w1.TIF"
                        
                        # Parse the temp filename to extract well name and other components
                        parts = filename.replace('_temp.TIF', '').split('_')
                        if len(parts) >= 4:
                            # Extract the well name (last part before _temp)
                            well_name = parts[-1]  # e.g., "A01"
                            
                            # Extract wavelength from original filename
                            wavelength_match = re.search(r'_w(\d+)', filename)
                            if wavelength_match:
                                wavelength = wavelength_match.group(1)
                                
                                # Construct final filename
                                final_filename = f"{g.plate_short}_{well_name}_w{wavelength}.TIF"
                                
                                src_path = os.path.join(crop_timepoint_dir, filename)
                                dst_path = os.path.join(input_timepoint_dir, final_filename)
                                
                                shutil.copy2(src_path, dst_path)
                            else:
                                print(f"    WARNING: Could not extract wavelength from {filename}")
                        else:
                            print(f"    WARNING: Could not parse temp filename {filename}")
        
        # 5. Clean up crop directory
        print("Cleaning up crop directory.")
        if os.path.exists(crop_dir):
            shutil.rmtree(crop_dir)
        
        print("Multi-well grid cropping completed successfully.")
    
    else:
        # Original single-well logic (unchanged)
        print("Single-well mode detected. Using standard grid cropping.")
        
        # loop through each timepoint folder
        for timepoint in range(g.time_points):
            original_images = os.listdir(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}'))

            # loop through each image in timepoint folder
            for current in original_images:
                # get path of current image
                current_path = os.path.join(g.plate_dir, 'TimePoint_' + str(timepoint + 1), current)
                # skip over if file does not exist
                if not os.path.exists(current_path):
                    continue

                # conversion of the well name to an array - A01 becomes [0, 0] where the format is [col, row]
                # group refers to group of wells to be split (for example splitting the group A01 into a 2x2 would result in wells A01, A02, B01, and B02)
                # get group_id using regex by extracting column letter and row number from current
                letter, number, site, wavelength = extract_well_name(current)
                if letter is None:  # Skip files that don't match the expected image naming pattern
                    continue
                group_id = [__capital_to_num(letter), int(number) - 1]

                # split image into individual wells
                individual_wells = __split_image(current_path, cols_per_image, rows_per_image)

                # loop through individual well images and save with corresponding well name
                for i in range(rows_per_image):
                    for j in range(cols_per_image):
                        well_name = __generate_well_name(g, group_id, j, i, cols_per_image, rows_per_image)
                        # save current image as well name
                        if site:
                            outpath = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}', g.plate_short + f'_{well_name}_s{site}_w{wavelength}.TIF')
                        else:
                            outpath = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}', g.plate_short + f'_{well_name}_w{wavelength}.TIF')
                        if g.circle_diameter != 'NA':
                            __apply_mask(individual_wells[i * cols_per_image + j], g.circle_diameter, 'circle').save(outpath)
                        elif g.square_side != 'NA':
                            __apply_mask(individual_wells[i * cols_per_image + j], g.square_side, 'square').save(outpath)
                        else:
                            individual_wells[i * cols_per_image + j].save(outpath)

# Automatically detect and crop wells. Supports both circular and square well detection with fallback to grid method.
# Uses template-based detection: detects wells once in TimePoint_1, then reuses positions.
# Called after conversion to IX format and HTDs are parsed
def auto_crop(g):
    print("Starting auto crop...")
    
    # Get configuration from YAML
    try:
        # Parse multi-well-detection configuration
        if hasattr(g, 'multi_well_detection'):
            detection_config = g.multi_well_detection
            if isinstance(detection_config, dict):
                well_shape = detection_config.get('well_shape', 'circle')
            else:
                well_shape = 'circle'  # default
        else:
            well_shape = 'circle'  # default
    except:
        well_shape = 'circle'  # fallback default
    
    print(f"Using well shape detection: {well_shape}")
    
    # Determine plate-specific Hough circle parameters based on plate dimensions
    total_wells = g.rows * g.cols
    if total_wells == 24:  # 24-well plate (e.g., 4×6 or 6×4)
        search_multiplier = 0.73
        hough_param1 = 80
        hough_param2 = 80
        print(f"Detected 24-well plate ({g.rows}×{g.cols}): using optimized parameters")
    elif total_wells == 96:  # 96-well plate (e.g., 8×12 or 12×8)
        search_multiplier = 1.0
        hough_param1 = 50
        hough_param2 = 60
        print(f"Detected 96-well plate ({g.rows}×{g.cols}): using optimized parameters")
    else:  # Default for other plate types
        search_multiplier = 0.8
        hough_param1 = 50
        hough_param2 = 30
        print(f"Using default parameters for {g.rows}×{g.cols} plate")
    
    expected_rows = g.rows // g.rec_rows
    expected_cols = g.cols // g.rec_cols
    expected_wells = expected_rows * expected_cols
    
    # Template detection: analyze TimePoint_1 to get well positions
    template_positions = __detect_template_positions(g, expected_rows, expected_cols, well_shape, 
                                                     search_multiplier, hough_param1, hough_param2)
    
    if template_positions is None:
        print("Template detection failed, falling back to grid method for all timepoints")
        # Fall back to original grid_crop method
        grid_crop(g)
        return
    
    print("Applying template positions to all timepoints...")
    
    # Check if we need to use crop directory (multi-well mode)
    if g.mode == "multi-well":
        print("Multi-well mode detected. Using crop directory to prevent file overwriting.")
        
        # 1. Create crop directory in work folder
        crop_dir = os.path.join(g.work, 'crop')
        os.makedirs(crop_dir, exist_ok=True)
        
        # 2. Copy input images to crop directory for processing
        for timepoint in range(g.time_points):
            input_timepoint_dir = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}')
            crop_timepoint_dir = os.path.join(crop_dir, f'TimePoint_{timepoint + 1}')
            
            if os.path.exists(input_timepoint_dir):
                # Create timepoint directory in crop folder
                os.makedirs(crop_timepoint_dir, exist_ok=True)
                
                # Copy all images to crop directory
                for filename in os.listdir(input_timepoint_dir):
                    if filename.lower().endswith(('.tif', '.tiff')):
                        src_path = os.path.join(input_timepoint_dir, filename)
                        dst_path = os.path.join(crop_timepoint_dir, filename)
                        shutil.copy2(src_path, dst_path)
        
        # 3. Perform auto cropping operations in crop directory
        for timepoint in range(g.time_points):
            crop_timepoint_dir = os.path.join(crop_dir, f'TimePoint_{timepoint + 1}')
            if not os.path.exists(crop_timepoint_dir):
                continue
                
            original_images = os.listdir(crop_timepoint_dir)

            # loop through each image in crop timepoint folder
            for current in original_images:
                # get path of current image in crop directory
                current_path = os.path.join(crop_timepoint_dir, current)
                # skip over if file does not exist
                if not os.path.exists(current_path):
                    continue

                # Extract well information
                letter, number, site, wavelength = extract_well_name(current)
                if letter is None:  # Skip files that don't match the expected image naming pattern
                    continue
                group_id = [__capital_to_num(letter), int(number) - 1]

                # Load image
                original_image = Image.open(current_path)
                
                # Use template positions instead of detecting wells each time
                if current in template_positions:
                    well_positions = template_positions[current]
                else:
                    print(f"    WARNING: No template positions found for {current}")
                    well_positions = None
                
                # Extract and save each well
                for i in range(expected_rows):
                    for j in range(expected_cols):
                        well_name = __generate_well_name(g, group_id, j, i, expected_cols, expected_rows)
                        
                        # Skip if well_name is None
                        if well_name is None:
                            print(f"    ERROR: well_name is None for sub-well [{i},{j}]")
                            continue
                        
                        # Use a unique temporary filename during cropping to prevent overwrites
                        temp_filename = f"{current.replace('.TIF', '')}_{well_name}_temp.TIF"
                        temp_outpath = os.path.join(crop_timepoint_dir, temp_filename)
                        
                        # Extract the well image using template positions
                        # Template is guaranteed to have all valid positions or we wouldn't be here
                        center_x, center_y, size = well_positions[i][j]
                        well_img = __extract_well_region(original_image, center_x, center_y, size, well_shape)
                        
                        # Apply masks if specified
                        if g.circle_diameter != 'NA':
                            __apply_mask(well_img, g.circle_diameter, 'circle').save(temp_outpath)
                        elif g.square_side != 'NA':
                            __apply_mask(well_img, g.square_side, 'square').save(temp_outpath)
                        else:
                            well_img.save(temp_outpath)
        
        # 4. Transfer cropped images back to input directory (same as grid_crop)
        for timepoint in range(g.time_points):
            input_timepoint_dir = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}')
            crop_timepoint_dir = os.path.join(crop_dir, f'TimePoint_{timepoint + 1}')
            
            if os.path.exists(crop_timepoint_dir):
                # Remove all existing files in input timepoint directory
                for filename in os.listdir(input_timepoint_dir):
                    file_path = os.path.join(input_timepoint_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                
                # Copy all cropped images from crop directory to input directory with proper renaming
                for filename in os.listdir(crop_timepoint_dir):
                    if filename.lower().endswith(('.tif', '.tiff')) and '_temp.TIF' in filename:
                        # Parse the temp filename to extract well name and other components
                        parts = filename.replace('_temp.TIF', '').split('_')
                        if len(parts) >= 4:
                            # Extract the well name (last part before _temp)
                            well_name = parts[-1]  # e.g., "A01"
                            
                            # Extract wavelength from original filename
                            wavelength_match = re.search(r'_w(\d+)', filename)
                            if wavelength_match:
                                wavelength = wavelength_match.group(1)
                                
                                # Construct final filename
                                final_filename = f"{g.plate_short}_{well_name}_w{wavelength}.TIF"
                                
                                src_path = os.path.join(crop_timepoint_dir, filename)
                                dst_path = os.path.join(input_timepoint_dir, final_filename)
                                
                                shutil.copy2(src_path, dst_path)
                            else:
                                print(f"    WARNING: Could not extract wavelength from {filename}")
                        else:
                            print(f"    WARNING: Could not parse temp filename {filename}")
        
        # 5. Clean up crop directory
        if os.path.exists(crop_dir):
            shutil.rmtree(crop_dir)

    print("Auto crop completed.")

# Extracts the column letter, row number, site number, and wavelength number from the image name
# Called in grid_crop() and auto_crop()
def extract_well_name(well_string):
    # regular expression pattern to match the format
    pattern = r'_([A-Z])(\d+)(?:_s(\d+))?_w(\d+)\.(tif|TIF|png|PNG|jpg|JPG|jpeg|JPEG)$'
    match = re.search(pattern, well_string)

    # check number of groups to determine site number if applicable and well number
    if match:
        # extract column letter
        letter = match.group(1)

        # extract row number
        number = match.group(2)

        # extract site number
        # if no site, site will be None
        site = match.group(3)

        # extract wavelength number
        wavelength = match.group(4)

        return letter, number, site, wavelength
    else:
        # return None if the pattern doesn't match
        return None, None, None, None

# Stitches all timepoints by merging site images for each timepoint
# Called in wrapper.py after plate has been cropped, and wells/sites used are retrieved
def stitch_all_timepoints(g, wells, input_dir, output_dir, format='TIF'):
    # check if images in input directory have been stitched already
    current_dir = os.path.join(input_dir, f'TimePoint_1')

    # loop through each timepoint folder in input directory
    for timepoint in range(g.time_points):
        # get current directory
        current_dir = os.path.join(input_dir, f'TimePoint_{timepoint+1}')

        # ensure that current directory is valiid
        if not os.path.isdir(current_dir):
            raise ValueError("Path is not a valid directory.")

        outpath = os.path.join(output_dir, f'TimePoint_{timepoint+1}')

        # stitch all sites in current timepoint directory
        stitch_directory(g, wells, current_dir, outpath, format)

# Stitches all site images in a directory into well-level images for each wavelength
# Called in stitch_all_timepoints()
def stitch_directory(g, wells, input_dir, output_dir, format='TIF'):
    # create output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # add site paths to list for each well and wavelength and stitch
    for wavelength in range(g.n_waves):
        for well in wells:
            site_paths = []
            for site in range(g.x_sites * g.y_sites):
                site_path = os.path.join(input_dir, g.plate_short + f'_{well}_s{site+1}_w{wavelength+1}.{format}')
                if not os.path.exists(site_path):
                    print("Sites have already been stitched.")
                    return
                site_paths.append(site_path)

            # create outpath of current well
            outpath = os.path.join(output_dir, g.plate_short + f'_{well}_w{wavelength+1}.{format}')
            
            # stitch sites
            if input_dir == output_dir:
                __stitch_sites(sorted(site_paths), outpath, delete_original=True)
            else:
                __stitch_sites(sorted(site_paths), outpath, delete_original=False)

# Applies circular or square masks to all well images across timepoints and wavelengths
# Called in wrapper.py after plate is stitched
def apply_masks(g):
    # return if no masking required
    if g.circle_diameter == 'NA' and g.square_side == 'NA':
        return
    if g.mode == 'multi-site' and g.stitch == False:
        print("Masks cannot be applied at the site-level.")
        return
    print(f"Applying masks...")
    # loop through timepoints
    for timepoint in range(g.time_points):
        # loop through wavelengths
        for wavelength in range(g.n_waves):
            # loop through individual wells
            for row in range(g.rows):
                for col in range(g.cols):
                    # generate well id
                    well_id = well_idx_to_name(g, row, col)
                    # get path of current image
                    img_path = os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}', g.plate_short + f'_{well_id}_w{wavelength + 1}.TIF')
                    # skip over path if it does not exist
                    if not os.path.exists(img_path):
                        continue
                    # open current image, apply mask, and save
                    with Image.open(img_path) as img:
                        if g.circle_diameter != 'NA':
                            __apply_mask(img, g.circle_diameter, 'circle').save(img_path)
                        elif g.square_side != 'NA':
                            __apply_mask(img, g.square_side, 'square').save(img_path)
    print(f"Finished applying masks.")

# Converts 0-indexed row and column indices to a well name (e.g., row=1, col=2 → 'B03')
# Called in __generate_well_name() and __apply_masks()
def well_idx_to_name(g, row, col):
    # generate letter
    letter = chr(row + 65)

    # determine number of preceding zeroes for single digit numbered columns
    # if total columns is less than 100, columns will be two digits, else number of digits for columns will match the total columns
    if col < 9:
        if g.cols >= 100:
            num_zeroes = len(str(g.cols)) - 1
            number = num_zeroes*"0" + str(col + 1)
        else:
            number = f"0{col + 1}"
    else:
        number = str(col + 1)
    return f"{letter}{number}"

# Generates a list of image paths for the given wells and wavelength
def generate_selected_image_paths(g, wells, wavelength, directory, format='TIF'):
    image_paths = []
    for well in wells:
        tiff_file_base = f"{g.plate_short}_{well}"
        wavelength_tiff_file = os.path.join(directory, f"{tiff_file_base}_w{wavelength}.{format}")
        base_tiff_file = os.path.join(directory, f"{tiff_file_base}.{format}")
        
        # Check if the wavelength-specific or base file exists
        if os.path.exists(wavelength_tiff_file):
            image_paths.append(wavelength_tiff_file)
        elif os.path.exists(base_tiff_file):
            image_paths.append(base_tiff_file)
        else:
            print(f"No file found for well {well} in directory {directory}")
            
    return image_paths


#####################################################
######### IMAGE PROCESSING HELPER FUNCTIONS #########
#####################################################

# Cleans up incomplete timepoint directories that may result from cameras recording extra frames 
# Called in avi_to_ix() and loopbio_to_ix()
def __cleanup_incomplete_timepoints(g, expected_files_per_timepoint):
    print(f"Checking for incomplete timepoints using TimePoint_1 as reference...")
    
    # Get all timepoint directories
    timepoint_dirs = [d for d in os.listdir(g.plate_dir) 
                     if d.startswith('TimePoint_') and os.path.isdir(os.path.join(g.plate_dir, d))]
    
    if not timepoint_dirs:
        print("No timepoint directories found.")
        return 0
    
    # Use TimePoint_1 as reference for expected file count
    reference_dir = os.path.join(g.plate_dir, 'TimePoint_1')
    if not os.path.exists(reference_dir):
        print("TimePoint_1 not found - cannot determine reference file count.")
        return 0
    
    reference_count = len([f for f in os.listdir(reference_dir) 
                          if f.lower().endswith(('.tif', '.tiff'))])
    print(f"Reference count from TimePoint_1: {reference_count} files")
    
    # Remove timepoints that don't match the reference count
    removed_count = 0
    for tp_dir in timepoint_dirs:
        tp_path = os.path.join(g.plate_dir, tp_dir)
        file_count = len([f for f in os.listdir(tp_path) 
                         if f.lower().endswith(('.tif', '.tiff'))])
        
        if file_count != reference_count:
            print(f"  {tp_dir}: Incomplete ({file_count}/{reference_count} files) - removing")
            shutil.rmtree(tp_path)
            removed_count += 1
    
    # Count remaining complete timepoints
    remaining_dirs = [d for d in os.listdir(g.plate_dir) 
                     if d.startswith('TimePoint_') and os.path.isdir(os.path.join(g.plate_dir, d))]
    
    if removed_count > 0:
        print(f"Removed {removed_count} incomplete timepoint directories.")
    
    print(f"Final result: {len(remaining_dirs)} complete timepoints.")
    return len(remaining_dirs)

# Creates HTD for avi input or loopbio input. 
# Called in avi_to_ix() and loopbio_to_ix()
def __create_htd(g, timepoints, source): # source is set to "AVI" or "LoopBio" in avi_to_ix and loopbio_to_ix respectively
    lines = []
    lines.append('"Description", ' + source + "\n")
    lines.append('"TimePoints", ' + str(timepoints) + "\n")
    lines.append('"XWells", ' + str(g.rec_cols) + "\n")
    lines.append('"YWells", ' + str(g.rec_rows) + "\n")
    lines.append('"XSites", ' + "1" + "\n")
    lines.append('"YSites", ' + "1" + "\n")
    lines.append('"NWavelengths", ' + "1" + "\n")
    lines.append('"WaveName1", ' + '"Transmitted Light"' + "\n")

    htd_path = os.path.join(g.plate_dir, g.plate_short + '.HTD')
    with open(htd_path, mode='w') as htd_file:
        htd_file.writelines(lines)

# Converts capital letters to numbers, where A is 0, B is 1, and so on. 
# Called in grid_crop() and auto_crop()
def __capital_to_num(alpha):
    return ord(alpha) - 65

# Splits image into x by y images and delete original image. 
# Called in grid_crop()
def __split_image(img_path, x, y):
    original_img = Image.open(img_path)
    if original_img is None:
        raise ValueError("Could not load the image")

    # get dimensions of original image
    original_width, original_height = original_img.size

    # calculate dimensions of cropped images
    width = original_width // x
    height = original_height // y

    images = []

    # loop through grid and split the image
    # place images into array row by row
    for i in range(y):
        for j in range(x):
            # calculate the coordinates for cropping
            left = j * width
            upper = i * height
            right = (j + 1) * width
            lower = (i + 1) * height

            # crop the region from the original image
            cropped_img = original_img.crop((left, upper, right, lower))

            # append the small image to the array
            images.append(cropped_img)

    # delete original uncropped image
    os.remove(img_path)

    return images

# Generates well name using the provided group id
# Called in grid_crop() and auto_crop()
def __generate_well_name(g, group_id, col, row, cols_per_image, rows_per_image):
    if g.mode == "multi-well":
        # For multi-well mode, group_id represents the camera's assigned well position from LoopBio
        # The camera mapping is: A01, A02, A03, B01, B02, B03 in a 2x3 grid
        # But each camera covers a 4x4 region of the final 8x12 plate
        
        # group_id[0] = camera row letter index (A=0, B=1), group_id[1] = camera col number index (01=0, 02=1, 03=2)
        camera_row_idx = group_id[0]  # A=0, B=1
        camera_col_idx = group_id[1]  # 01=0, 02=1, 03=2
        
        # Map camera positions to their coverage areas:
        # For a 2x3 camera layout covering an 8x12 plate:
        # - Each camera covers 4 rows (8/2) and 4 columns (12/3)
        # - Camera A01 [0,0] -> covers plate rows 0-3, cols 0-3   (A01-A04, B01-B04, C01-C04, D01-D04)
        # - Camera A02 [0,1] -> covers plate rows 0-3, cols 4-7   (A05-A08, B05-B08, C05-C08, D05-D08)  
        # - Camera A03 [0,2] -> covers plate rows 0-3, cols 8-11  (A09-A12, B09-B12, C09-C12, D09-D12)
        # - Camera B01 [1,0] -> covers plate rows 4-7, cols 0-3   (E01-E04, F01-F04, G01-G04, H01-H04)
        # - Camera B02 [1,1] -> covers plate rows 4-7, cols 4-7   (E05-E08, F05-F08, G05-G08, H05-H08)
        # - Camera B03 [1,2] -> covers plate rows 4-7, cols 8-11  (E09-E12, F09-F12, G09-G12, H09-H12)
        
        # Calculate starting well position for this camera
        start_well_row = camera_row_idx * rows_per_image  # A cameras start at row 0, B cameras at row 4
        start_well_col = camera_col_idx * cols_per_image  # 01 cameras start at col 0, 02 at col 4, 03 at col 8
        
        # Add sub-well offset to get final well position
        well_row = start_well_row + row
        well_col = start_well_col + col
        
        # Validate that we're within plate bounds
        if well_row >= g.rows or well_col >= g.cols:
            print(f"    WARNING: Well position ({well_row}, {well_col}) exceeds plate bounds ({g.rows}, {g.cols})")
            return None
            
    else:
        # Original single-well logic
        well_row = group_id[0] * rows_per_image + row
        well_col = group_id[1] * cols_per_image + col
    
    well_name = well_idx_to_name(g, well_row, well_col)

    return well_name

# Applies a circular or square mask to an image based on the specified type.
# Called in grid_crop(), auto_crop(), and apply_masks()
def __apply_mask(image, mask_size, type):
    # get current height and width of image
    width, height = image.size

    if type == 'square': # Square mask crops the image to the specified size
        new_side_length = height * mask_size
        # calculate the coordinates to crop the image
        left = (width - new_side_length) // 2
        top = (height - new_side_length) // 2
        right = (width + new_side_length) // 2
        bottom = (height + new_side_length) // 2

        # crop the image
        masked_image = image.crop((left, top, right, bottom))

        return masked_image

    elif type == 'circle': # Circle mask will add a black border around the specified size of circle
        # calculate the circle's radius
        radius = (height * mask_size) / 2

        # create a circular mask
        y, x = np.ogrid[:height, :width]
        center = (width // 2, height // 2)
        # find squared distance of each coordinate from the centre and return True if it is within the mask area
        mask_area = (x - center[0])**2 + (y - center[1])**2 > radius**2

        # apply the mask to the image
        masked_array = np.array(image)
        masked_array[mask_area] = 0
        masked_image = Image.fromarray(masked_array, mode='I;16')

        return masked_image

# Detect well positions from TimePoint_1 images to create a template for all timepoints 
# Called in auto_crop()
def __detect_template_positions(g, expected_rows, expected_cols, well_shape, 
                                search_multiplier, hough_param1, hough_param2):
    timepoint_1_dir = os.path.join(g.plate_dir, 'TimePoint_1')
    
    if not os.path.exists(timepoint_1_dir):
        print("TimePoint_1 directory not found for template detection")
        return None
    
    template_positions = {}
    images = [f for f in os.listdir(timepoint_1_dir) if f.lower().endswith(('.tif', '.tiff'))]
    
    if not images:
        print("No images found in TimePoint_1 for template detection")
        return None
    
    for image_file in images:
        image_path = os.path.join(timepoint_1_dir, image_file)
        
        try:
            image = Image.open(image_path)
            well_positions = __detect_wells(image, expected_rows, expected_cols, well_shape,
                                           search_multiplier, hough_param1, hough_param2)
            
            if well_positions is not None:
                template_positions[image_file] = well_positions
            else:
                print(f"Template detection failed for {image_file}")
                return None
                
        except Exception as e:
            print(f"Error processing {image_file}: {e}")
            return None
    
    return template_positions

# Simplified well detection using Hough circles with distance transform fallback
# Called in __detect_template_positions()
def __detect_wells(image, expected_rows, expected_cols, well_shape,
                   search_multiplier, hough_param1, hough_param2):
    # Convert to grayscale
    np_image = np.array(image)
    if len(np_image.shape) == 3:
        gray_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY)
    else:
        gray_image = np_image
        if gray_image.dtype != np.uint8:
            min_val, max_val = np.min(gray_image), np.max(gray_image)
            if max_val > min_val:
                gray_image = ((gray_image - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            else:
                gray_image = np.zeros_like(gray_image, dtype=np.uint8)
    
    h, w = gray_image.shape
    row_spacing = h // expected_rows
    col_spacing = w // expected_cols
    estimated_well_size = min(row_spacing, col_spacing) * 0.8
    
    grid_positions = []
    
    for i in range(expected_rows):
        row_positions = []
        for j in range(expected_cols):
            # Calculate grid center
            center_y = int((i + 0.5) * row_spacing)
            center_x = int((j + 0.5) * col_spacing)
            
            # Try to refine position
            try:
                refined_x, refined_y = __refine_well_position(gray_image, center_x, center_y, 
                                                                   int(estimated_well_size), well_shape,
                                                                   search_multiplier, hough_param1, hough_param2)
                row_positions.append((refined_x, refined_y, estimated_well_size))
            except:
                # Use grid position as fallback
                row_positions.append((center_x, center_y, estimated_well_size))
        
        grid_positions.append(row_positions)
    
    return grid_positions

# Simplified well position refinement using Hough circles or distance transform
# Called in __detect_wells()
def __refine_well_position(gray_image, center_x, center_y, search_radius, well_shape,
                           search_multiplier, hough_param1, hough_param2):
    h, w = gray_image.shape
    search_size = int(search_radius * search_multiplier)
    y1 = max(0, center_y - search_size)
    y2 = min(h, center_y + search_size)
    x1 = max(0, center_x - search_size)
    x2 = min(w, center_x + search_size)
    
    search_region = gray_image[y1:y2, x1:x2]
    blurred = cv2.GaussianBlur(search_region, (5, 5), 1)
    
    if well_shape == 'circle':
        # Use Hough circle detection
        try:
            region_h, region_w = search_region.shape
            min_radius = int(min(region_h, region_w) * 0.2)
            max_radius = int(min(region_h, region_w) * 0.4)
            
            circles = cv2.HoughCircles(
                blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=min_radius,
                param1=hough_param1, param2=hough_param2, minRadius=min_radius, maxRadius=max_radius
            )
            
            if circles is not None:
                circles = np.round(circles[0, :]).astype(int)
                search_center_x = search_size
                search_center_y = search_size
                
                # Find closest circle to expected center
                best_circle = min(circles, 
                                 key=lambda c: np.sqrt((c[0] - search_center_x)**2 + (c[1] - search_center_y)**2))
                
                return x1 + best_circle[0], y1 + best_circle[1]
        except:
            pass
    
    else:  # square wells
        # Use edge detection for square wells
        try:
            edges = cv2.Canny(search_region, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    return x1 + cx, y1 + cy
        except:
            pass
    
    # If all methods fail, use original position
    return center_x, center_y

# Extract a well region from the image
# Called in auto_crop()
def __extract_well_region(image, center_x, center_y, size, well_shape):
    padding_factor = 1.2
    crop_size = int(size * padding_factor)
    
    left = max(0, center_x - crop_size // 2)
    top = max(0, center_y - crop_size // 2)
    right = min(image.width, center_x + crop_size // 2)
    bottom = min(image.height, center_y + crop_size // 2)
    
    cropped_img = image.crop((left, top, right, bottom))
    
    if well_shape == 'circle':
        # Apply circular mask
        np_img = np.array(cropped_img)
        rel_center_x = center_x - left
        rel_center_y = center_y - top
        
        Y, X = np.ogrid[:np_img.shape[0], :np_img.shape[1]]
        dist_from_center = np.sqrt((X - rel_center_x)**2 + (Y - rel_center_y)**2)
        mask = dist_from_center <= size // 2
        
        masked_img = np_img.copy()
        if len(np_img.shape) == 3:
            for c in range(np_img.shape[2]):
                masked_img[:,:,c][~mask] = 0
        else:
            masked_img[~mask] = 0
        
        return Image.fromarray(masked_img)
    
    return cropped_img

# Stitches sites into an n by n square image and fills extra space with black and deletes original images if specified
# Called in stitch_directory()
def __stitch_sites(image_paths, outpath, delete_original=False, format='TIF'):
    if not image_paths:
        raise ValueError("The list of image paths is empty.")

    # load the first image to determine individual image size
    with Image.open(image_paths[0]) as img:
        img_width, img_height = img.size

    if img_width != img_height:
        raise ValueError("Images are not square.")

    # calculate dimensions for the output image
    num_images = len(image_paths)
    side_length = math.ceil(math.sqrt(num_images))
    canvas_size = side_length * img_width

    # create a new image with a black 
    if format == 'TIF':
        stitched_image = Image.new('I;16', (canvas_size, canvas_size), 0)
    else:
        stitched_image = Image.new('RGB', (canvas_size, canvas_size))

    # place each image into the stitched_image
    # assumes that stitched sites form a square (if requires change in the future, use x_sites and y_sites)
    for i, img_path in enumerate(image_paths):
        with Image.open(img_path) as img:
            if img.size != (img_width, img_height):
                raise ValueError(f"Image at {img_path} is not of the correct size.")
            x = (i % side_length) * img_width
            y = (i // side_length) * img_height
            stitched_image.paste(img, (x, y))
        
        # delete original image if not diagnostic image
        if delete_original:
            os.remove(img_path)

    stitched_image.save(outpath)
