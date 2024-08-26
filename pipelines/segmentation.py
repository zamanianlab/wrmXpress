import os
import numpy as np
import pandas as pd
from skimage import io, measure
from cellpose import models

def segmentation(g, wells, well_sites, options):
    # Initialize Cellpose model
    model = models.CellposeModel(gpu=False, model_type=options['model'])
    
    results = []

    for well_site in well_sites:
        for wavelength in range(g.n_waves):
            # Load the image for the given well_site and wavelength
            image_path = os.path.join(g.plate_dir, f'{well_site}_{wavelength}.tif')
            image = io.imread(image_path)
            
            # Run segmentation
            masks, _, _, _ = model.eval(image, diameter=None)
            
            # Calculate metrics
            total_segmented_pixels = np.sum(masks > 0)
            num_objects = len(np.unique(masks)) - 1  # exclude background
            average_size = total_segmented_pixels / num_objects if num_objects > 0 else 0
            
            # Calculate compactness for each object
            compactness_list = [
                (region.perimeter ** 2) / (4 * np.pi * region.area)
                for region in measure.regionprops(masks)
            ]
            average_compactness = np.mean(compactness_list) if compactness_list else 0
            
            # Store results
            results.append({
                'well_site': well_site,
                'wavelength': wavelength,
                'total_segmented_pixels': total_segmented_pixels,
                'num_objects': num_objects,
                'average_size': average_size,
                'average_compactness': average_compactness
            })
            
            # Save segmented image
            img_dir = os.path.join(g.output, 'segmentation', 'img')
            stitched_image_path = os.path.join(img_dir, f'{well_site}_{wavelength}_segmented.png')
            io.imsave(stitched_image_path, masks)

    # Convert results to DataFrame and save as CSV
    df = pd.DataFrame(results)
    output_csv = os.path.join(g.output, 'segmentation', f'{g.plate}_segmentation.csv')
    df.to_csv(output_csv, index=False)

