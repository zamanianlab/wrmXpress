import pandas as pd
from pathlib import Path

def generate_tidy_csv(pipeline_folder, plate_id, metadata_dir):
    # Get all CSV files in the pipeline folder
    csv_files = list(pipeline_folder.glob('*.csv'))

    # Process each CSV file
    for csv_file in csv_files:
        # Read the CSV file
        df = pd.read_csv(csv_file)

        # Path to the metadata folder for the given plate ID
        plate_id_folder = metadata_dir / plate_id

        # List all metadata CSV files
        metadata_csv_files = list(plate_id_folder.glob('*.csv'))

        # Add metadata to the DataFrame
        for metadata_csv_file in metadata_csv_files:
            metadata_df = pd.read_csv(metadata_csv_file, header=None)
            metadata_df.fillna(value='NA', inplace=True)
            single_column_df = metadata_df.stack().reset_index(drop=True)
            df[metadata_csv_file.stem] = single_column_df

        # Save the DataFrame to a tidy CSV
        tidy_csv_path = pipeline_folder / f'{csv_file.stem}_tidy.csv'
        df.to_csv(tidy_csv_path, index=False)
