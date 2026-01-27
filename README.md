# Image Measurement Tool

A Python tool for measuring linear structures in TIFF images with automatic filename tracking.

## Installation

1. Make sure you have Python 3.7+ installed

2. Install required packages:
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install opencv-python numpy pandas
```

## Usage

1. Run the script:
```bash
python image_measurement_tool.py
```

2. Select the folder containing your TIFF images

3. (Optional) Set a scale if you know the pixel-to-unit conversion
   - Example: If 1 pixel = 0.5 µm, enter 0.5 as the conversion factor

4. For each image:
   - **LEFT CLICK** to add points along the structure you want to measure
   - **SPACE** (hold) to enable panning mode, then drag the image with your mouse
   - **UP/DOWN arrows** to adjust brightness
   - **LEFT/RIGHT arrows** to adjust contrast
   - **Press 's'** to save the current measurement
   - **Press 'r'** to reset/clear the current measurement
   - **Press 'p'** to go back to the previous image
   - **Press 'n'** to move to the next image
   - **Press 'q'** to quit and save all measurements

5. Results are saved to `measurements.csv` in the same folder as your images

## Customizing Window Size

To change the default window size, edit the last few lines of `image_measurement_tool.py`:

```python
# Change these numbers to your preferred width and height
tool = ImageMeasurementTool(window_width=1200, window_height=800)
```

Examples:
- Larger window: `ImageMeasurementTool(1600, 1000)`
- Smaller window: `ImageMeasurementTool(800, 600)`
- Full HD: `ImageMeasurementTool(1920, 1080)`

## Output

The CSV file will have two columns:
- `filename`: Name of the TIFF file
- `length`: Measured length (in pixels or your specified unit)

Multiple measurements per file are supported - each measurement will be a separate row with the same filename.

## Tips

- **Window position**: The window will automatically open centered on your screen
- **Panning**: Hold SPACE and drag with your mouse to pan around large images
- **Brightness/Contrast**: Use arrow keys to adjust image visibility
  - UP/DOWN arrows: Adjust brightness (-100 to +100)
  - LEFT/RIGHT arrows: Adjust contrast (0.5x to 3.0x)
- **Navigation**: Use 'p' to go back to previous images if you need to remeasure
- Markers are delicate (small hollow circles with a center dot) for better visibility
- You can measure curved structures by clicking multiple points along the curve
- The tool calculates the total path length through all clicked points
- You can have multiple measurements per image
- The measurement line is drawn in thin green as you click
- If you accidentally add a wrong point, press 'r' to reset and start over
- Brightness and contrast adjustments reset when moving to a new image

## Example Output

```csv
filename,length
image001.tiff,245.67
image001.tiff,189.34
image002.tiff,312.45
image003.tiff,201.23
image003.tiff,198.76
image003.tiff,215.89
```