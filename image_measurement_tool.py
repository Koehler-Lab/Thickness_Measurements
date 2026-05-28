"""
Interactive Image Measurement Tool — Annotated PNG Export
Measure linear structures in TIFF images, export to CSV,
and save color-coded annotation PNGs for each measured image.
"""

import cv2
import numpy as np
from pathlib import Path
import pandas as pd
from tkinter import Tk, filedialog
import sys

# Distinct, high-contrast colors (BGR) that cycle per measurement
MEASUREMENT_COLORS = [
    (0, 255, 0),       # Green
    (0, 165, 255),     # Orange
    (255, 0, 255),     # Magenta
    (255, 255, 0),     # Cyan
    (0, 0, 255),       # Red
    (255, 0, 0),       # Blue
    (0, 255, 255),     # Yellow
    (180, 105, 255),   # Hot pink
    (0, 215, 255),     # Gold
    (208, 224, 64),    # Turquoise
]


class ImageMeasurementTool:
    def __init__(self, window_width=1200, window_height=800):
        self.points = []
        self.measurements = []
        self.current_image = None
        self.current_filename = None
        self.display_image = None
        self.pixel_to_unit = 1.0
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
        self.brightness = 0
        self.contrast = 1.0

        # --- NEW: saved annotations for the current image ---
        # Each entry: {'points': [...], 'length': float, 'color': (B,G,R)}
        self.saved_annotations = []

    def apply_adjustments(self, image):
        """Apply brightness and contrast adjustments to image"""
        adjusted = cv2.convertScaleAbs(image, alpha=self.contrast, beta=self.brightness)
        return adjusted

    def _current_color(self):
        """Return the color for the measurement currently being drawn."""
        idx = len(self.saved_annotations) % len(MEASUREMENT_COLORS)
        return MEASUREMENT_COLORS[idx]

    def draw_annotations(self):
        """Redraw all saved + in-progress annotations on the display image"""
        adjusted_image = self.apply_adjustments(self.current_image)
        self.display_image = adjusted_image.copy()

        # --- Draw previously saved measurements ---
        for ann in self.saved_annotations:
            color = ann['color']
            pts = ann['points']
            length = ann['length']

            # Lines
            if len(pts) > 1:
                for i in range(1, len(pts)):
                    p1 = (pts[i-1][0] + self.offset_x, pts[i-1][1] + self.offset_y)
                    p2 = (pts[i][0] + self.offset_x, pts[i][1] + self.offset_y)
                    cv2.line(self.display_image, p1, p2, color, 1)

            # Dots
            for pt in pts:
                adj = (pt[0] + self.offset_x, pt[1] + self.offset_y)
                cv2.circle(self.display_image, adj, 3, color, 1)
                cv2.circle(self.display_image, adj, 1, color, -1)

            # Length label near midpoint of the measurement
            if len(pts) >= 2:
                mid_idx = len(pts) // 2
                mid = (pts[mid_idx][0] + self.offset_x, pts[mid_idx][1] + self.offset_y)
                label = f"{length:.2f} {self.unit_name}"
                cv2.putText(self.display_image, label,
                            (mid[0] + 5, mid[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

        # --- Draw current (in-progress) measurement ---
        color = self._current_color()
        if len(self.points) > 1:
            for i in range(1, len(self.points)):
                p1 = (self.points[i-1][0] + self.offset_x, self.points[i-1][1] + self.offset_y)
                p2 = (self.points[i][0] + self.offset_x, self.points[i][1] + self.offset_y)
                cv2.line(self.display_image, p1, p2, color, 1)

        for point in self.points:
            adjusted_point = (point[0] + self.offset_x, point[1] + self.offset_y)
            cv2.circle(self.display_image, adjusted_point, 3, color, 1)
            cv2.circle(self.display_image, adjusted_point, 1, color, -1)

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to add measurement points"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.panning:
                self.pan_start = (x, y)
            else:
                actual_point = (x - self.offset_x, y - self.offset_y)
                self.points.append(actual_point)
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.panning and self.pan_start is not None:
                dx = x - self.pan_start[0]
                dy = y - self.pan_start[1]
                self.offset_x += dx
                self.offset_y += dy
                self.pan_start = (x, y)
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

    def save_annotation_png(self, image_path):
        """Save a PNG with all measurement annotations drawn on the original image."""
        if not self.saved_annotations:
            return  # Nothing to save

        # Draw on original (unadjusted) image at full resolution, no pan offset
        annotated = self.current_image.copy()

        for ann in self.saved_annotations:
            color = ann['color']
            pts = ann['points']
            length = ann['length']

            if len(pts) > 1:
                for i in range(1, len(pts)):
                    cv2.line(annotated, pts[i-1], pts[i], color, 1)

            for pt in pts:
                cv2.circle(annotated, pt, 3, color, 1)
                cv2.circle(annotated, pt, 1, color, -1)

            if len(pts) >= 2:
                mid_idx = len(pts) // 2
                mid = pts[mid_idx]
                label = f"{length:.2f} {self.unit_name}"
                cv2.putText(annotated, label,
                            (mid[0] + 5, mid[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

        # Build output path: same folder, <stem>_annotated.png
        src = Path(image_path)
        out_path = src.parent / f"{src.stem}_annotated.png"
        cv2.imwrite(str(out_path), annotated)
        print(f"  Annotation PNG saved: {out_path.name}")

    def set_cursor(self, cursor_type):
        """Set cursor type if supported by OpenCV version"""
        try:
            if hasattr(cv2, 'WND_PROP_CURSOR'):
                cv2.setWindowProperty('Measure Image', cv2.WND_PROP_CURSOR, cursor_type)
        except:
            pass

    def center_window(self, window_name):
        """Center the window on the screen"""
        try:
            import tkinter as tk
            root = tk.Tk()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.destroy()
            x = (screen_width - self.window_width) // 2
            y = (screen_height - self.window_height) // 2
            cv2.moveWindow(window_name, x, y)
        except:
            pass

    def process_image(self, image_path):
        """Process a single image"""
        self.current_filename = Path(image_path).name

        img = cv2.imread(str(image_path), cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)

        if img is None:
            print(f"Error: Could not read {image_path}")
            return

        if img.dtype == np.uint16:
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        self.current_image = img.copy()

        # Reset per-image state
        self.offset_x = 0
        self.offset_y = 0
        self.panning = False
        self.brightness = 0
        self.contrast = 1.0
        self.saved_annotations = []

        self.display_image = self.apply_adjustments(self.current_image.copy())

        cv2.namedWindow('Measure Image', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Measure Image', self.window_width, self.window_height)
        cv2.setMouseCallback('Measure Image', self.mouse_callback)

        if hasattr(cv2, 'CURSOR_CROSS'):
            self.set_cursor(cv2.CURSOR_CROSS)

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

            if key == 32:  # Spacebar
                if not self.panning:
                    self.panning = True
                    if hasattr(cv2, 'CURSOR_HAND'):
                        self.set_cursor(cv2.CURSOR_HAND)
                    print("  Panning mode ON - drag to pan")
                else:
                    self.panning = False
                    self.pan_start = None
                    if hasattr(cv2, 'CURSOR_CROSS'):
                        self.set_cursor(cv2.CURSOR_CROSS)
                    print("  Panning mode OFF - click to add points")

            elif key == 82 or key == 0:  # Up arrow
                self.brightness = min(100, self.brightness + 10)
                print(f"  Brightness: {self.brightness:+d}")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)

            elif key == 84 or key == 1:  # Down arrow
                self.brightness = max(-100, self.brightness - 10)
                print(f"  Brightness: {self.brightness:+d}")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)

            elif key == 83 or key == 3:  # Right arrow
                self.contrast = min(5.0, self.contrast + 0.2)
                print(f"  Contrast: {self.contrast:.1f}x")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)

            elif key == 81 or key == 2:  # Left arrow
                self.contrast = max(0.3, self.contrast - 0.2)
                print(f"  Contrast: {self.contrast:.1f}x")
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)

            elif key == ord('s'):  # Save measurement
                if len(self.points) >= 2:
                    length = self.calculate_length()
                    color = self._current_color()

                    # Store annotation for PNG export
                    self.saved_annotations.append({
                        'points': list(self.points),
                        'length': length,
                        'color': color,
                    })

                    self.measurements.append({
                        'filename': self.current_filename,
                        'length': length
                    })
                    print(f"  Measurement saved: {length:.2f} {self.unit_name}  (color #{len(self.saved_annotations)})")
                    print(f"  Total measurements for this image: "
                          f"{sum(1 for m in self.measurements if m['filename'] == self.current_filename)}")

                    # Reset points for next measurement; redraw keeps saved annotations visible
                    self.points = []
                    self.draw_annotations()
                    cv2.imshow('Measure Image', self.display_image)
                else:
                    print("  Need at least 2 points to save a measurement")

            elif key == ord('r'):  # Reset current measurement
                self.points = []
                self.draw_annotations()
                cv2.imshow('Measure Image', self.display_image)
                print("  Measurement reset")

            elif key == ord('p'):  # Previous image
                if len(self.points) >= 2:
                    response = input("You have unsaved points. Save measurement? (y/n): ")
                    if response.lower() == 'y':
                        length = self.calculate_length()
                        color = self._current_color()
                        self.saved_annotations.append({
                            'points': list(self.points),
                            'length': length,
                            'color': color,
                        })
                        self.measurements.append({
                            'filename': self.current_filename,
                            'length': length
                        })
                        print(f"  Measurement saved: {length:.2f} {self.unit_name}")
                self.save_annotation_png(image_path)
                self.points = []
                cv2.destroyAllWindows()
                return 'previous'

            elif key == ord('n'):  # Next image
                if len(self.points) >= 2:
                    response = input("You have unsaved points. Save measurement? (y/n): ")
                    if response.lower() == 'y':
                        length = self.calculate_length()
                        color = self._current_color()
                        self.saved_annotations.append({
                            'points': list(self.points),
                            'length': length,
                            'color': color,
                        })
                        self.measurements.append({
                            'filename': self.current_filename,
                            'length': length
                        })
                        print(f"  Measurement saved: {length:.2f} {self.unit_name}")
                self.save_annotation_png(image_path)
                self.points = []
                break

            elif key == ord('q'):  # Quit
                if len(self.points) >= 2:
                    response = input("You have unsaved points. Save measurement? (y/n): ")
                    if response.lower() == 'y':
                        length = self.calculate_length()
                        color = self._current_color()
                        self.saved_annotations.append({
                            'points': list(self.points),
                            'length': length,
                            'color': color,
                        })
                        self.measurements.append({
                            'filename': self.current_filename,
                            'length': length
                        })
                        print(f"  Measurement saved: {length:.2f} {self.unit_name}")
                self.save_annotation_png(image_path)
                cv2.destroyAllWindows()
                return 'quit'

        cv2.destroyAllWindows()
        return 'continue'

    def run(self, image_folder=None):
        """Main function to process all images"""
        if image_folder is None:
            root = Tk()
            root.withdraw()
            image_folder = filedialog.askdirectory(title="Select folder containing TIFF images")
            root.destroy()
            if not image_folder:
                print("No folder selected. Exiting.")
                return

        image_folder = Path(image_folder)

        tiff_files = sorted(list(image_folder.glob("*.tif")) + list(image_folder.glob("*.tiff")))

        if not tiff_files:
            print(f"No TIFF files found in {image_folder}")
            return

        print(f"\nFound {len(tiff_files)} TIFF files")

        response = input("\nDo you want to set a scale (pixels to real units)? (y/n): ")
        if response.lower() == 'y':
            try:
                self.pixel_to_unit = float(input("Enter conversion factor (e.g., 0.5 if 1 pixel = 0.5 um): "))
                self.unit_name = input("Enter unit name (e.g., um, mm): ")
            except ValueError:
                print("Invalid input. Using pixels.")

        current_index = 0
        while current_index < len(tiff_files):
            img_path = tiff_files[current_index]
            print(f"\n[Image {current_index + 1}/{len(tiff_files)}]")
            result = self.process_image(img_path)

            if result == 'quit':
                break
            elif result == 'previous':
                if current_index > 0:
                    current_index -= 1
                else:
                    print("  Already at first image")
                    current_index = 0
            else:
                current_index += 1

        if self.measurements:
            df = pd.DataFrame(self.measurements)
            output_file = image_folder / "measurements.csv"
            print(f"\n{'='*60}")
            print(f"Saving results to: {output_file}")
            df.to_csv(output_file, index=False)

            print(f"\n{'='*60}")
            print("SUMMARY")
            print(f"{'='*60}")
            print(f"Total measurements: {len(df)}")
            print(f"Images measured: {df['filename'].nunique()}")
            print(f"\nMeasurements per file:")
            print(df['filename'].value_counts().to_string())
            print(f"\nResults saved to: {output_file}")
            print(f"Annotated PNGs saved alongside original images.")
            print(f"{'='*60}")
        else:
            print("\nNo measurements were saved.")


if __name__ == "__main__":
    tool = ImageMeasurementTool(window_width=1200, window_height=800)
    tool.run()
