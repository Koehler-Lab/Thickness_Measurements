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
    def __init__(self, window_width=1200, window_height=800):
        self.points = []
        self.measurements = []
        self.current_image = None
        self.current_filename = None
        self.display_image = None
        self.pixel_to_unit = 1.0  # Change this if you know your scale
        self.unit_name = "pixels"
        
        # Window size
        self.window_width = window_width
        self.window_height = window_height
        
        # Panning variables
        self.panning = False
        self.pan_start = None
        self.offset_x = 0
        self.offset_y = 0
        
        # Image adjustment variables
        self.brightness = 0  # Range: -100 to 100
        self.contrast = 1.0  # Range: 0.5 to 3.0
        
    def apply_adjustments(self, image):
        """Apply brightness and contrast adjustments to image"""
        # Apply contrast
        adjusted = cv2.convertScaleAbs(image, alpha=self.contrast, beta=self.brightness)
        return adjusted
    
    def draw_annotations(self):
        """Redraw all points and lines on the display image"""
        # Apply adjustments to the base image
        adjusted_image = self.apply_adjustments(self.current_image)
        self.display_image = adjusted_image.copy()
        
        # Draw lines between points
        if len(self.points) > 1:
            for i in range(1, len(self.points)):
                # Adjust points for current offset
                p1 = (self.points[i-1][0] + self.offset_x, self.points[i-1][1] + self.offset_y)
                p2 = (self.points[i][0] + self.offset_x, self.points[i][1] + self.offset_y)
                cv2.line(self.display_image, p1, p2, (0, 255, 0), 1)
        
        # Draw points (more delicate)
        for point in self.points:
            adjusted_point = (point[0] + self.offset_x, point[1] + self.offset_y)
            # Draw outer circle (hollow)
            cv2.circle(self.display_image, adjusted_point, 3, (0, 255, 0), 1)
            # Draw center dot
            cv2.circle(self.display_image, adjusted_point, 1, (0, 255, 0), -1)
        
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to add measurement points"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.panning:
                # Start panning
                self.pan_start = (x, y)
            else:
                # Add measurement point (adjust for current offset)
                actual_point = (x - self.offset_x, y - self.offset_y)
                self.points.append(actual_point)
                
                # Redraw with new point
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)
        
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.panning and self.pan_start is not None:
                # Calculate pan delta
                dx = x - self.pan_start[0]
                dy = y - self.pan_start[1]
                
                # Update offset
                self.offset_x += dx
                self.offset_y += dy
                
                # Update pan start for next movement
                self.pan_start = (x, y)
                
                # Redraw image with new offset
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)
        
        elif event == cv2.EVENT_LBUTTONUP:
            if self.panning:
                self.pan_start = None
            
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
    
    def set_cursor(self, cursor_type):
        """Set cursor type if supported by OpenCV version"""
        try:
            if hasattr(cv2, 'WND_PROP_CURSOR'):
                cv2.setWindowProperty('Measure Image', cv2.WND_PROP_CURSOR, cursor_type)
        except:
            # Cursor change not supported in this OpenCV version
            pass
    
    def center_window(self, window_name):
        """Center the window on the screen"""
        try:
            # Get screen resolution
            import tkinter as tk
            root = tk.Tk()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.destroy()
            
            # Calculate position to center the window
            x = (screen_width - self.window_width) // 2
            y = (screen_height - self.window_height) // 2
            
            # Move window to center
            cv2.moveWindow(window_name, x, y)
        except:
            # If centering fails, just continue
            pass
    
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
        
        # Reset panning and adjustments for new image
        self.offset_x = 0
        self.offset_y = 0
        self.panning = False
        self.brightness = 0
        self.contrast = 1.0
        
        # Apply initial adjustments and set display image
        self.display_image = self.apply_adjustments(self.current_image.copy())
        
        # Create window and set mouse callback
        cv2.namedWindow('Measure Image', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Measure Image', self.window_width, self.window_height)
        cv2.setMouseCallback('Measure Image', self.mouse_callback)
        
        # Set cursor to crosshair for precise measurements (if supported)
        if hasattr(cv2, 'CURSOR_CROSS'):
            self.set_cursor(cv2.CURSOR_CROSS)
        
        # Center window on screen
        self.center_window('Measure Image')
        
        print(f"\n{'='*60}")
        print(f"Image: {self.current_filename}")
        print(f"{'='*60}")
        print("Instructions:")
        print("  - LEFT CLICK: Add points along the structure to measure")
        print("  - SPACE: Hold to enable panning mode (then drag with mouse)")
        print("  - UP/DOWN arrows: Adjust brightness")
        print("  - LEFT/RIGHT arrows: Adjust contrast")
        print("  - 's': Save current measurement and start a new one")
        print("  - 'r': Reset current measurement (clear points)")
        print("  - 'p': Previous image")
        print("  - 'n': Next image (skip current)")
        print("  - 'q': Quit and save all measurements")
        print(f"{'='*60}\n")
        
        cv2.imshow('Measure Image', self.display_image)
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == 32:  # Spacebar - toggle panning mode
                if not self.panning:
                    self.panning = True
                    # Change cursor to hand for panning (if supported)
                    if hasattr(cv2, 'CURSOR_HAND'):
                        self.set_cursor(cv2.CURSOR_HAND)
                    print("🖐️  Panning mode ON - drag to pan")
                else:
                    self.panning = False
                    self.pan_start = None
                    # Change cursor back to crosshair for measurement (if supported)
                    if hasattr(cv2, 'CURSOR_CROSS'):
                        self.set_cursor(cv2.CURSOR_CROSS)
                    print("👆 Panning mode OFF - click to add points")
            
            elif key == 82 or key == 0:  # Up arrow - increase brightness
                self.brightness = min(100, self.brightness + 10)
                print(f"☀️  Brightness: {self.brightness:+d}")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)
            
            elif key == 84 or key == 1:  # Down arrow - decrease brightness
                self.brightness = max(-100, self.brightness - 10)
                print(f"☀️  Brightness: {self.brightness:+d}")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)
            
            elif key == 83 or key == 3:  # Right arrow - increase contrast
                self.contrast = min(5.0, self.contrast + 0.2)
                print(f"◐  Contrast: {self.contrast:.1f}x")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)
            
            elif key == 81 or key == 2:  # Left arrow - decrease contrast
                self.contrast = max(0.3, self.contrast - 0.2)
                print(f"◐  Contrast: {self.contrast:.1f}x")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)
            
            elif key == ord('s'):  # Save measurement
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
            
            elif key == ord('p'):  # Previous image
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
                cv2.destroyAllWindows()
                return 'previous'
            
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
        current_index = 0
        while current_index < len(tiff_files):
            img_path = tiff_files[current_index]
            print(f"\n[Image {current_index + 1}/{len(tiff_files)}]")
            result = self.process_image(img_path)
            
            if result == 'quit':
                break
            elif result == 'previous':
                # Go to previous image
                if current_index > 0:
                    current_index -= 1
                else:
                    print("⚠ Already at first image")
                    current_index = 0  # Stay at first image
            else:  # 'continue' or next image
                current_index += 1
        
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
    # You can adjust the default window size here (width, height)
    # Default is 1200x800, but you can change it to any size you prefer
    # Examples:
    #   tool = ImageMeasurementTool(1600, 1000)  # Larger window
    #   tool = ImageMeasurementTool(800, 600)    # Smaller window
    #   tool = ImageMeasurementTool(1920, 1080)  # Full HD
    
    tool = ImageMeasurementTool(window_width=1200, window_height=800)
    tool.run()