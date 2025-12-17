# Training a CellPose segmentation model

1. Download the CellPose GUI:
    - If you don't already have CellPose, create a conda environment by running this command in a terminal window: `conda create --name cellpose python=3.9` 
    - Activate the conda environment by running this command: `conda activate cellpose`
    - Install the CellPose GUI and environment by running this command: `python -m pip install cellpose[gui]`

2. Start the cellpose GUI with this command: `python -m cellpose`

3. Create a new folder on your desktop called `cellpose`. Add three more folders within: `train`, `test`, and `models`. Add your training images of interest to the training folder, and some images in the test folder. The training images should make up at least 70% of all images (train + test). Training and test images should be representative of what your actual image data will look like.

4. Drag and drop an image from your `train` folder into the CellPose GUI. 

5. Begin making annotations and drawing masks.
    - Right click to create an anchor point and then draw with your mouse or mouse pad around the object that you want to segment.
    - To delete a mask hold command and click on the mask. 
    - To merger two masks, click one mask, then hold option and click on the other mask. 
    - Annotations will be automatically saved in the same `training_images` folder as a .npy file.

6. Repeat step 4 and 5 until all images are annotated. 

7. Once images are annotated, run this command: `python -m cellpose --train --dir path/to/train/ --test_dir path/to/test/ --learning_rate 0.00001 --weight_decay 0.1 --n_epochs 100 --train_batch_size 1`. Your model will be in the `models` folder. 

8. Rename the model you have created to a name that best fits it. To add the model to wrmXpress and test locally, you may take this model and copy and paste it to the `pipelines/models/cellpose` folder in wrmXpress.

