# Generating a CellProfiler Pipeline

With CellProfiler, there are numerous pipelines that you can build by configuring the many different modules it has to offer. Our lab mainly uses it for measuring C. elegans size and fluorescence quantification. 

1. Download [CellProfiler](https://cellprofiler.org/)

2. On your desktop create a new folder called `cellprofiler`, where all the outputs for your initial pipeline testing will populate. 

2. Open CellProfiler and start a new project. A project template can be found in the `supplemental/CellProfiler` folder called `template.cpproj`. This template is specifically for measuring C. elegans size so you may have to reconfigure the modules for your own . 

3. Drag and drop a subset of test images into the Images pane.
    - To run in headless mode (on a server, or adding to wrmXpress), the pipeline will not be able to use Images, Metadata, NamesAndTypes, or Groups. Instead, these will need to be populated with the LoadData module.

4. In the bottom left hand corner, click on the Output Settings button and change the default output folder to the `cellprofiler` folder you created above. 

5. You may add or delete modules depending on the type of pipeline you are developing by clicking the plus sign button next to Adjust modules in the bottom left hand corner. Modules will populate in the left pane.  

6. Configure each module to fine tune your pipeline. 

7. Click the Analyze Images button in the bottom left hand corner to test your pipeline. 
    - Make sure that the check marks next to each module are green, otherwise your pipeline will not run properly. 
    - Continue to go through steps 5-7 until you get the output you desire.  

8. To implement into wrmXpress, make sure you are using the LoadData, SaveImages, and ExportToSpreadsheet modules properly. Pipelines can be added to `pipelines/cellprofiler` and our CellProfiler pipelines found in that same folder can be referenced to see how we configure those modules. 
