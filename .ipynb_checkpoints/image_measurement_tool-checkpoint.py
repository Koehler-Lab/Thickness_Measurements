"""
Interactive Image Measurement Tool
Measure linear structures in TIFF images and export to CSV
"""

import cv2
import numpy as np
from pathlib import Path
import pandas as pd
from tkinter import Tk, filedialog
import sys

class ImageMeasurementTool:
    def __init__(self):
        self.points = []
        self.measurements = []
        self.current_image = None
        self.current_filename = None
        self.display_image = None
        self.pixel_to_unit = 1.0  # Change this if you know your scale
        self.unit_name = "pixels"
        
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to add measurement points"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Add point
            self.points.append((x, y))
            
            # Draw the point
            cv2.circle(self.display_image, (x, y), 5, (0, 255, 0), -1)
            
            # If we have at least 2 points, draw lines between them
            if len(self.points) > 1:
                cv2.line(self.display_image, self.points[-2], self.points[-1], (0, 255, 0), 2)
            
            cv2.imshow('Measure Image', self.display_image)
            
    def calculate_length(self):
        """Calculate total length from points"""
        if len(self.points) < 2:
            return 0
        
        total_length = 0
        for i in range(1, len(self.points)):
            p1 = np.array(self.points[i-1])
            p2 = np.array(self.points[i])
            total_length += np.linalg.norm(p2 - p1)
        
        return total_length * self.pixel_to_unit
    
    def process_image(self, image_path):
        """Process a single image"""
        self.current_filename = Path(image_path).name
        
        # Read image
        img = cv2.imread(str(image_path), cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
        
        if img is None:
            print(f"Error: Could not read {image_path}")
            return
        
        # Convert to 8-bit for display if needed
        if img.dtype == np.uint16:
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        # Convert grayscale to BGR for colored annotations
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        self.current_image = img.copy()
        self.display_image = img.copy()
        
        # Create window and set mouse callback
        cv2.namedWindow('Measure Image', cv2.WINDOW_NORMAL)
        cv2.setMouseCallback('Measure Image', self.mouse_callback)
        
        print(f"\n{'='*60}")
        print(f"Image: {self.current_filename}")
        print(f"{'='*60}")
        print("Instructions:")
        print("  - LEFT CLICK: Add points along the structure to measure")
        print("  - 's': Save current measurement and start a new one")
        print("  - 'r': Reset current measurement (clear points)")
        print("  - 'n': Next image (skip current)")
        print("  - 'q': Quit and save all measurements")
        print(f"{'='*60}\n")
        
        cv2.imshow('Measure Image', self.display_image)
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):  # Save measurement
                if len(self.points) >= 2:
                    length = self.calculate_length()
                    self.measurements.append({
                        'filename': self.current_filename,
                        'length': length
                    })
                    print(f"✓ Measurement saved: {length:.2f} {self.unit_name}")
                    print(f"  Total measurements for this image: {sum(1 for m in self.measurements if m['filename'] == self.current_filename)}")
                    
                    # Reset for next measurement on same image
                    self.points = []
                    self.display_image = self.current_image.copy()
                    cv2.imshow('Measure Image', self.display_image)
                else:
                    print("⚠ Need at least 2 points to save a measurement")
            
            elif key == ord('r'):  # Reset current measurement
                self.points = []
                self.display_image = self.current_image.copy()
                cv2.imshow('Measure Image', self.display_image)
                print("↻ Measurement reset")
            
            elif key == ord('n'):  # Next image
                if len(self.points) >= 2:
                    response = input("You have unsaved points. Save measurement? (y/n): ")
                    if response.lower() == 'y':
                        length = self.calculate_length()
                        self.measurements.append({
                            'filename': self.current_filename,
                            'length': length
                        })
                        print(f"✓ Measurement saved: {length:.2f} {self.unit_name}")
                self.points = []
                break
            
            elif key == ord('q'):  # Quit
                if len(self.points) >= 2:
                    response = input("You have unsaved points. Save measurement? (y/n): ")
                    if response.lower() == 'y':
                        length = self.calculate_length()
                        self.measurements.append({
                            'filename': self.current_filename,
                            'length': length
                        })
                        print(f"✓ Measurement saved: {length:.2f} {self.unit_name}")
                cv2.destroyAllWindows()
                return 'quit'
        
        cv2.destroyAllWindows()
        return 'continue'
    
    def run(self, image_folder=None):
        """Main function to process all images"""
        # Select folder if not provided
        if image_folder is None:
            root = Tk()
            root.withdraw()
            image_folder = filedialog.askdirectory(title="Select folder containing TIFF images")
            root.destroy()
            
            if not image_folder:
                print("No folder selected. Exiting.")
                return
        
        image_folder = Path(image_folder)
        
        # Find all TIFF files
        tiff_files = sorted(list(image_folder.glob("*.tif")) + list(image_folder.glob("*.tiff")))
        
        if not tiff_files:
            print(f"No TIFF files found in {image_folder}")
            return
        
        print(f"\nFound {len(tiff_files)} TIFF files")
        
        # Ask for scale (optional)
        response = input("\nDo you want to set a scale (pixels to real units)? (y/n): ")
        if response.lower() == 'y':
            try:
                self.pixel_to_unit = float(input("Enter conversion factor (e.g., 0.5 if 1 pixel = 0.5 µm): "))
                self.unit_name = input("Enter unit name (e.g., µm, mm): ")
            except ValueError:
                print("Invalid input. Using pixels.")
        
        # Process each image
        for i, img_path in enumerate(tiff_files, 1):
            print(f"\n[Image {i}/{len(tiff_files)}]")
            result = self.process_image(img_path)
            
            if result == 'quit':
                break
        
        # Save results
        if self.measurements:
            df = pd.DataFrame(self.measurements)
            
            # Ask for output filename
            output_file = image_folder / "measurements.csv"
            print(f"\n{'='*60}")
            print(f"Saving results to: {output_file}")
            df.to_csv(output_file, index=False)
            
            # Print summary
            print(f"\n{'='*60}")
            print("SUMMARY")
            print(f"{'='*60}")
            print(f"Total measurements: {len(df)}")
            print(f"Images measured: {df['filename'].nunique()}")
            print(f"\nMeasurements per file:")
            print(df['filename'].value_counts().to_string())
            print(f"\nResults saved to: {output_file}")
            print(f"{'='*60}")
        else:
            print("\nNo measurements were saved.")

if __name__ == "__main__":
    tool = ImageMeasurementTool()
    tool.run()