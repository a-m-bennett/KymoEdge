# KymoEdge
## Note before use
**KymoEdge (ND 27-008)** is freely available without a fee for a non-commercial use, and may be redistributed under these conditions. Please see the attached license for further details. For commercial use, the non-exclusive commercial license requires a non-refundable annual fee. For commercial use queries, please contact [softwarelicensing@nd.edu](mailto:softwarelicensing@nd.edu).

---

**Non-Exclusive Commercial License Details:**
* The non-exclusive commercial license requires a non-refundable $25,000 US annual royalty.
* The license is non-negotiable.

Information required to complete the license:
* Legal company name
* State/country of incorporation
* Type of corporation
* Principal address of corporation
* The "field of use" with which the company plans to use **KymoEdge (ND 27-008)**
* Name of the person who will sign the licensed
* Title of the person who will sign the license
* Address for notices, including name and email of person to be notified

Steps to execute the license:
* Contact Notre Dame’s IDEA Center at [softwarelicensing@nd.edu](mailto:softwarelicensing@nd.edu).
* You'll then receive a Docusign document with the license
* Review the information and electronically sign it
* The signed document will automatically return to the University of Notre Dame du Lac (UND), where it will be signed by UND
* You'll receive an "Approved" email along with a scan of the fully executed document
* Pay the license fee per license agreement
* Once paid, you may begin using the **KymoEdge (ND 27-008)** software

This technology may not be exported or reexported to Cuba, Iran, North Korea, Syria, and Sudan.


## Setup
1. Create a folder where you will store the Kymograph Edge Detection Tool. 
2. Download the KymographEdgeDetection.py demoFiles folder, and requirements.txt and place them in the desired folder.
3. In your terminal, navigate to the folder.
4. While not required, it is advised that you create a virtual enviorment in this folder.
5. To install the required packages, run `pip install -r requirements.txt` in the terminal.
6. The tool is now ready to use. To do so, simply run the python file.

## Demo Data
Two demo images are provided to allow users to play around with the interface before using your own data. To use one of the demo files, select either "Demo1" or "Demo2" for the "Image Data Source" and click "Load Image"

## The Interface
### The Configuration Panel
#### Image Data Source
Select one of three options.
1. Browse Local File... 
2. Demo1
3. Demo2
#### Browse
Clicking the Browse button will open your computer's file browser.
You may then navigate to your desired tiff or tif file. 
Once a valid path is slected, click "Load Image".
#### Load Image
On a click, "Load Image" triggers the function load_tiff_direct which will take in the tiff file, convert to greyscale if necessary, and load the data as a numpy array. The image is then displayed on the canvas to the right of the Configuration Panel.
#### Rotate Image 90&deg;
As the path finding algorithm works from the left edge to the right edge of the image, utilize the Rotate Image 90&deg; button to correctly orient the image.
#### Show Ban Regions Box Overlays
Banning boxes can clog up the image. To make them invisible, uncheck this box. The bans will still be in effect, but will not be visible. 
#### Grid Tick Frequency (px)
While the ticks serve no functional purpose, they can help orient and provide perspective in the image. To change the freqency of the tickmarks, change the value in this field.
#### Jump Values
The jump values control the smoothness of the path by limiting how many pixels the path can jump from column to column. Splitting the jump values into above and below is done to account for times where the kymograph falls faster than it grows. 
#### Compute / Update Path
On a click, "Compute / Update Path" triggers several functions which culminates in an updated path showing on the canvas in green. This path is found using a shortest path algorithm with respect to the banned regions as specified by the user.
#### Undo Last Ban Region
On a click, "Undo Last Ban Region" removes the most recent ban box drawn by the user.
#### Clear All Ban Regions
On a click, "Clear All Ban Regions" reverts the image to its original state, removing any ban boxes.
#### Export Path Data
On a click, "Export Path Data" will open your computer's file saving screen. Here, the desired save location can be designated, as well as the desired name for the data file. Three file formats are available to accomidate further processing; txt, dat, and csv.

### Calibration Settings
Different experimental settings call for different export settings. These three settings will be used to covert the path data from pixels to subunit per second.
#### Time per pixel (s)
Enter the time, in seconds, that each pixel represents.
#### Nanometeres per pixel (nm)
Enter the number of nanometers that each pixel represents.
#### Nanometeres per subunit (nm)
Enter the number of nanometeres are in each subunit.
### The Canvas
Upon starting, the Canvas will appear blank. Once an image is selected and Load Image is clicked, the image will be loaded onto the canvas. 
#### Banning
Experimental data often comes with noise, which can interfere when trying to find the desired edge in the data. To account for this, the user can ban regions of the image. To do so, click and drag on the image. This will create a red box, banning the pixels in that area. To remove a ban box, click the red X in the upper right hand corner of the box or utilize the "Undo Last Ban Region" or "Clear All Ban Regions" buttons.

## The Process