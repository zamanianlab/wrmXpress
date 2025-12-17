# Training a YOLO model using Roboflow annotations for segmentation

1. Gather your training images. Yolo requires your images to be in PNG or JPG format. If your images are coming from an ImageXpress and are in the ImageXpress format (TIF), download and use the `tif_to_png` folder in the supplemental/scripts folder to convert your images to the proper format. Training images should be representative of what your actual image data will look like. 

2. If not using ImageXpress images skip down to step 4 and have your images already converted and selected. Add your plates with images of interest to the `input` folder of `tif_to_png`. You may leave the whole plate as is in this folder and after conversion select which images you want to use for training. The script will convert every TIF within the first timepoint folder. 

3. In a terminal window, navigate to the `tif_to_png` folder. Run this command to install the requirements: `pip install requirements.txt`. Then, run the convert_tif_to_png.py script by using this command: `python convert_tif_to_png.py`. PNGs will be available in the output folder. 

4. Create a [Roboflow](https://roboflow.com/) account.

5. In Roboflow, create a new project for segmentation.

6. In the upload data tab, click select files, and select all of the images that you wish to train. More images can be added later. 

7. Once uploaded, you may start annotating in the annotate tab. For most objects, you will likely be able to use the smart selection tool, but as objects decrease in size, it will be more difficult to use that tool. In that case you will need to use the polygon tool. 

8. Once you have annotated your images, add them to your dataset. It can automatically split the data into training, validation, and testing data. Ideally, you want 70% or more of your dataset to be training data.

9. In the dataset tab, click the train model button and it will prompt you to add augmentations for the data set. Augmentations will increase the training data set size and is highly recommended. Choose whichever augmentations you think would help train a more robust model.

10. Go to the versions tab and click download dataset. The image and annotation format should be in YOLOv8. Toggle ‘show download code’. Before copying, follow the next few steps.

11. On your desktop create a new folder called `yolo`. 

12. In a terminal window, install ultralytics with this command: `pip install ultralytics`

13. Install roboflow with this command: `pip install roboflow`

14. Use the terminal and copy and paste the curl command given from step 10 in the `yolo` folder you created. The images you annotated and augmented will be downloaded in this folder. 

15. Run this command to start training your model: `yolo segment train data=Path/to/data.yaml model=yolov8n-seg.pt epochs=100 imgsz=640`. Depending on your dataset size, this may take a few hours to days if running locally. For faster training, consult a server administrator for GPU access. 

16. Once training is completed, check the yolo/runs/segment/train folder to see results. 

17. To test the model on new images run this command: `yolo segment predict model=runs/segment/train/weights/best.pt source=Path/to/real/images save=True`. You will need a new set of images that you would like to test the model on. 

18. To add the model to wrmXpress and test locally, navigate to runs/segment/train/weights and rename `best.pt` to a name that best fits the model. You may take this model and copy and paste it to the pipelines/models/yolo folder in wrmXpress.

