# Instructions for training Cellpose models

1. Clone the wrmXpress repo and change to the cellpose branch:

    ```
    cd $HOME
    mkdir GitHub
    cd GitHub
    git clone https://github.com/zamanianlab/wrmXpress.git
    cd wrmXpress
    git checkout cellpose
    ```

2. Select and copy sample images from ResearchDrive to `~/GitHub/wrmXpress/cellpose_training/training_images`
   - Try to get 8-10 images per folder

3. Create a new conda environment called cellpose and install the GUI:

    ```
    cd ~/GitHub/wrmXpress/cellpose_training
    conda create --name cellpose python=3.8
    conda activate cellpose
    python -m pip install cellpose[gui]
    ```

4. Start the cellpose GUI:

    ```
    python -m cellpose
    ```

5. Load an image by dragging the file into the GUI

6. Select a model from the "custom models" drop-down
    - If you don't see any of our custom models, click Models > Add custom torch model to GUI, and load the models found at `~/GitHub/wrmXpress/cellpose_training/models`

7. Run the model on the new image, which will use the model to segment worms. Try both models, and move to step 8 after the better model has finished.

    ![Screen Shot 2022-08-10 at 9 39 44 AM](https://user-images.githubusercontent.com/16230555/183931407-90fa9138-ebdc-4368-9d47-f16f2a815d46.png)

8. Run the model on the new image, which will use the model to segment worms. Try both models, and move to step 8 after the better model has finished.

9. Manually annotate the image to delete, merge, or add masks
   1. Delete a mask: Cmd + Click
   2. Merge two masks: Click one mask, then Option + Click
   3. Add a new mask: Two finger click (on a Mac), and then draw the mask around the worm
   4. Annotations will be automatically saved

10. Repeat steps 5-8 with a new image.
