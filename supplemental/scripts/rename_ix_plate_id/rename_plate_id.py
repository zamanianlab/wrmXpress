import os
import sys
import re
from pathlib import Path


def validate_date(date_str):
    """Validate date format is YYYYMMDD."""
    if not re.match(r'^\d{8}$', date_str):
        return False
    # Basic validation: check if date components are reasonable
    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    if year < 1900 or year > 2100:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False
    return True


def validate_plate_number(plate_num_str):
    """Validate plate number is numeric."""
    try:
        num = int(plate_num_str)
        return num > 0
    except ValueError:
        return False


def get_user_inputs(plate_folders):
    """Prompt user for researcher initials and plate-specific information."""
    print("\n" + "="*60)
    print("PLATE ID RENAMING SCRIPT")
    print("="*60)
    
    # Get researcher initials (once for all plates)
    while True:
        initials = input("\nWhat are your initials? ").strip().upper()
        if initials:
            break
        print("Error: Initials cannot be empty. Please try again.")
    
    # Get date and plate number for each plate
    plate_info = {}
    for original_plate_id in plate_folders:
        print(f"\n--- Processing plate: {original_plate_id} ---")
        
        # Get date
        while True:
            date = input(f"What date was this plate '{original_plate_id}' run? (YYYYMMDD format): ").strip()
            if validate_date(date):
                break
            print("Error: Invalid date format. Please enter date as YYYYMMDD (e.g., 20250127)")
        
        # Get plate number
        while True:
            plate_num = input(f"What number plate was this '{original_plate_id}' of said date? ").strip()
            if validate_plate_number(plate_num):
                # Zero-pad to 2 digits
                plate_num_padded = str(int(plate_num)).zfill(2)
                break
            print("Error: Invalid plate number. Please enter a positive number.")
        
        # Construct new plate ID
        new_plate_id = f"{date}-p{plate_num_padded}-{initials}"
        plate_info[original_plate_id] = new_plate_id
        print(f"  → Will rename to: {new_plate_id}")
    
    return plate_info


def rename_files_in_folder(folder_path, old_plate_id, new_plate_id):
    """Rename all files in a folder that contain the old plate ID."""
    renamed_count = 0
    
    for file in os.listdir(folder_path):
        file_path = folder_path / file
        
        # Skip directories
        if file_path.is_dir():
            continue
        
        # Check if file contains old plate ID
        if old_plate_id in file:
            new_filename = file.replace(old_plate_id, new_plate_id)
            new_file_path = folder_path / new_filename
            
            try:
                file_path.rename(new_file_path)
                print(f"    Renamed file: {file} → {new_filename}")
                renamed_count += 1
            except Exception as e:
                print(f"    Error renaming {file}: {e}")
    
    return renamed_count


def detect_plate_id_from_files(plate_path):
    """Detect the actual plate_id from filenames in the folder."""
    # Look for HTD file in root
    for file in os.listdir(plate_path):
        if file.endswith('.HTD') and not (plate_path / file).is_dir():
            # Extract plate_id from HTD filename (remove .HTD extension)
            return file[:-4]
    
    # If no HTD file, look in TimePoint folders for TIF files
    for item in os.listdir(plate_path):
        item_path = plate_path / item
        if item_path.is_dir() and item.startswith("TimePoint_"):
            for file in os.listdir(item_path):
                if file.endswith('.TIF'):
                    # Extract plate_id from TIF filename (before _well_wavelength)
                    # Pattern: plate_id_well_wavelength.TIF
                    match = re.match(r'^(.+?)_[A-Z]\d+_w\d+\.TIF$', file)
                    if match:
                        return match.group(1)
    
    return None


def process_plate_folder(input_dir, original_plate_id, new_plate_id):
    """Process a single plate folder and rename all associated files and folders."""
    original_plate_path = input_dir / original_plate_id
    
    if not original_plate_path.exists():
        print(f"  Error: Plate folder not found: {original_plate_path}")
        return False
    
    print(f"\n  Processing: {original_plate_id} → {new_plate_id}")
    
    # Detect the actual plate_id from filenames
    actual_plate_id = detect_plate_id_from_files(original_plate_path)
    
    if not actual_plate_id:
        print(f"  Error: Could not detect plate_id from files in {original_plate_id}")
        return False
    
    if actual_plate_id != original_plate_id:
        print(f"    Detected plate_id in files: {actual_plate_id}")
    
    total_renamed = 0
    
    # Rename HTD file in root of plate folder
    htd_file = original_plate_path / f"{actual_plate_id}.HTD"
    if htd_file.exists():
        new_htd_file = original_plate_path / f"{new_plate_id}.HTD"
        try:
            htd_file.rename(new_htd_file)
            print(f"    Renamed root HTD: {actual_plate_id}.HTD → {new_plate_id}.HTD")
            total_renamed += 1
        except Exception as e:
            print(f"    Error renaming root HTD file: {e}")
    
    # Process TimePoint folders
    for item in os.listdir(original_plate_path):
        item_path = original_plate_path / item
        
        if item_path.is_dir() and item.startswith("TimePoint_"):
            print(f"    Processing {item}/")
            
            # Rename files in TimePoint folder (TIF and HTD files)
            renamed = rename_files_in_folder(item_path, actual_plate_id, new_plate_id)
            total_renamed += renamed
    
    # Finally, rename the plate folder itself (only if not already renamed)
    new_plate_path = input_dir / new_plate_id
    if original_plate_path != new_plate_path:
        try:
            original_plate_path.rename(new_plate_path)
            print(f"  Renamed folder: {original_plate_id}/ → {new_plate_id}/")
            total_renamed += 1
        except Exception as e:
            print(f"  Error renaming plate folder: {e}")
            return False
    
    print(f"  ✓ Completed: {total_renamed} items renamed")
    return True


def main():
    """Main function to orchestrate the renaming process."""
    # Define input directory
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    
    # Check if input directory exists
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        print("Please create an 'input/' directory and place your plate folders inside.")
        sys.exit(1)
    
    # Find all plate folders in input directory
    plate_folders = [item.name for item in input_dir.iterdir() if item.is_dir()]
    
    if not plate_folders:
        print(f"No plate folders found in: {input_dir}")
        print("Please add plate folders to the input directory.")
        sys.exit(1)
    
    print(f"\nFound {len(plate_folders)} plate folder(s) to process:")
    for folder in plate_folders:
        print(f"  - {folder}")
    
    # Get user inputs for all plates
    plate_info = get_user_inputs(plate_folders)
    
    # Confirm before proceeding
    print("\n" + "="*60)
    print("SUMMARY OF PLANNED RENAMES:")
    print("="*60)
    for old_id, new_id in plate_info.items():
        print(f"  {old_id} → {new_id}")
    
    confirm = input("\nProceed with renaming? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("Renaming cancelled.")
        sys.exit(0)
    
    # Process each plate folder
    print("\n" + "="*60)
    print("RENAMING IN PROGRESS...")
    print("="*60)
    
    success_count = 0
    for original_plate_id, new_plate_id in plate_info.items():
        if process_plate_folder(input_dir, original_plate_id, new_plate_id):
            success_count += 1
    
    # Final summary
    print("\n" + "="*60)
    print("RENAMING COMPLETE")
    print("="*60)
    print(f"Successfully processed {success_count}/{len(plate_folders)} plate(s)")
    
    if success_count == len(plate_folders):
        print("✓ All plates renamed successfully!")
    else:
        print("⚠ Some plates encountered errors. Please review the output above.")


if __name__ == "__main__":
    main()
