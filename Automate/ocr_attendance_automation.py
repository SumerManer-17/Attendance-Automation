from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import cv2
import pytesseract
import numpy as np
from PIL import Image
import re
import os
from tkinter import filedialog, messagebox
import tkinter as tk

class OCRAttendanceAutomator:
    def __init__(self, html_file_path):
        """
        Initialize the OCR + Attendance automator
        
        Args:
            html_file_path (str): Path to your HTML file
        """
        self.driver = None
        self.html_file_path = html_file_path
        self.total_students = 80
        
        # Try to set tesseract path (adjust based on your installation)
        self.setup_tesseract()
        
    def setup_tesseract(self):
        """Setup Tesseract OCR path"""
        # Common Windows paths for Tesseract
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME')),
            "tesseract"  # If it's in PATH
        ]
        
        for path in possible_paths:
            try:
                pytesseract.pytesseract.tesseract_cmd = path
                # Test if tesseract works
                pytesseract.get_tesseract_version()
                print(f"✓ Tesseract found at: {path}")
                return
            except:
                continue
        
        print("⚠ Tesseract not found. Please install Tesseract OCR.")
        print("   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        
    def select_image_file(self):
        """Open file dialog to select image"""
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        file_path = filedialog.askopenfilename(
            title="Select image with handwritten numbers",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
                ("All files", "*.*")
            ]
        )
        
        root.destroy()
        return file_path
        
    def preprocess_image(self, image_path):
        """
        Preprocess image for better OCR results
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                print("✗ Could not read image file")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply different preprocessing techniques
            processed_images = []
            
            # Method 1: Basic threshold
            _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("Basic Threshold", thresh1))
            
            # Method 2: Gaussian blur + threshold
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh2 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("Blurred Threshold", thresh2))
            
            # Method 3: Adaptive threshold
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY, 11, 2)
            processed_images.append(("Adaptive Threshold", adaptive))
            
            # Method 4: Morphological operations
            kernel = np.ones((2,2), np.uint8)
            morph = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
            processed_images.append(("Morphological", morph))
            
            return processed_images
            
        except Exception as e:
            print(f"✗ Error preprocessing image: {e}")
            return None
    
    def extract_numbers_from_image(self, image_path):
        """
        Extract numbers from image using OCR with multiple preprocessing methods
        """
        print(f"🔍 Processing image: {os.path.basename(image_path)}")
        
        processed_images = self.preprocess_image(image_path)
        if not processed_images:
            return []
        
        all_numbers = []
        
        # Try OCR with different preprocessing methods
        for method_name, processed_img in processed_images:
            try:
                print(f"   Trying {method_name}...")
                
                # OCR configuration for numbers
                config = '--psm 6 -c tessedit_char_whitelist=0123456789,-'
                
                # Perform OCR
                text = pytesseract.image_to_string(processed_img, config=config)
                
                # Extract numbers from text
                numbers = self.extract_numbers_from_text(text)
                if numbers:
                    print(f"   ✓ Found numbers: {numbers}")
                    all_numbers.extend(numbers)
                else:
                    print(f"   - No numbers found with {method_name}")
                    
            except Exception as e:
                print(f"   ✗ Error with {method_name}: {e}")
        
        # Remove duplicates and sort
        unique_numbers = sorted(list(set(all_numbers)))
        
        # Filter valid roll numbers (1-80)
        valid_numbers = [n for n in unique_numbers if 1 <= n <= 80]
        
        if valid_numbers:
            print(f"✓ Successfully extracted roll numbers: {valid_numbers}")
        else:
            print("⚠ No valid roll numbers found in image")
            
        return valid_numbers
    
    def extract_numbers_from_text(self, text):
        """Extract numbers from OCR text"""
        numbers = []
        
        # Clean the text
        text = text.strip().replace('\n', ' ').replace('\t', ' ')
        
        # Method 1: Find individual numbers
        individual_numbers = re.findall(r'\b\d{1,2}\b', text)
        for num_str in individual_numbers:
            try:
                num = int(num_str)
                if 1 <= num <= 80:
                    numbers.append(num)
            except ValueError:
                pass
        
        # Method 2: Find ranges like "1-5" or "10-15"
        ranges = re.findall(r'\b(\d{1,2})\s*[-–—]\s*(\d{1,2})\b', text)
        for start_str, end_str in ranges:
            try:
                start, end = int(start_str), int(end_str)
                if 1 <= start <= 80 and 1 <= end <= 80 and start <= end:
                    numbers.extend(range(start, end + 1))
            except ValueError:
                pass
        
        # Method 3: Find comma-separated numbers
        comma_separated = re.findall(r'\b\d{1,2}(?:\s*,\s*\d{1,2})+\b', text)
        for group in comma_separated:
            nums = re.findall(r'\d{1,2}', group)
            for num_str in nums:
                try:
                    num = int(num_str)
                    if 1 <= num <= 80:
                        numbers.append(num)
                except ValueError:
                    pass
        
        return numbers
    
    def setup_driver(self, browser="chrome"):
        """Setup WebDriver with options for different browsers"""
        
        if browser.lower() == "chrome":
            from selenium.webdriver.chrome.options import Options
            try:
                from selenium.webdriver.chrome.service import Service as ChromeService
                from webdriver_manager.chrome import ChromeDriverManager
                
                chrome_options = Options()
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--allow-running-insecure-content")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-logging")
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--silent")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                chrome_options = Options()
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--disable-extensions")
                self.driver = webdriver.Chrome(options=chrome_options)
                
        elif browser.lower() == "firefox":
            from selenium.webdriver.firefox.options import Options
            try:
                from selenium.webdriver.firefox.service import Service as FirefoxService
                from webdriver_manager.firefox import GeckoDriverManager
                
                firefox_options = Options()
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
            except:
                firefox_options = Options()
                self.driver = webdriver.Firefox(options=firefox_options)
                
        elif browser.lower() == "edge":
            from selenium.webdriver.edge.options import Options
            try:
                from selenium.webdriver.edge.service import Service as EdgeService
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                
                edge_options = Options()
                edge_options.add_argument("--disable-web-security")
                edge_options.add_argument("--disable-extensions")
                
                service = EdgeService(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=edge_options)
            except:
                edge_options = Options()
                self.driver = webdriver.Edge(options=edge_options)
        
        self.driver.maximize_window()
        print(f"✓ {browser.title()} browser started successfully!")
        
    def load_page(self):
        """Load the attendance HTML page"""
        try:
            self.driver.get(self.html_file_path)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "studentList"))
            )
            print("✓ Page loaded successfully!")
            time.sleep(2)
            return True
        except TimeoutException:
            print("✗ Failed to load the page. Check your file path.")
            return False
    
    def mark_attendance_by_roll_numbers(self, absent_roll_numbers):
        """Mark attendance by specifying exact roll numbers to keep absent"""
        if not absent_roll_numbers:
            absent_roll_numbers = []
        
        present_count = 80 - len(absent_roll_numbers)
        absent_count = len(absent_roll_numbers)
        
        print(f"📋 Marking attendance:")
        print(f"   Present: {present_count} students")
        print(f"   Absent: {absent_count} students (Roll numbers: {sorted(absent_roll_numbers)})")
        
        try:
            all_students = list(range(1, 81))
            present_students = [roll for roll in all_students if roll not in absent_roll_numbers]
            
            print(f"🔄 Processing {len(present_students)} students to mark present...")
            
            success_count = 0
            
            for i, roll_number in enumerate(present_students, 1):
                try:
                    if i % 20 == 0:
                        time.sleep(0.5)
                    
                    toggle_input = self.driver.find_element(By.ID, str(roll_number))
                    
                    if not toggle_input.is_selected():
                        self.driver.execute_script("arguments[0].click();", toggle_input)
                        success_count += 1
                    else:
                        success_count += 1
                    
                    if i % 20 == 0 or i == len(present_students):
                        print(f"   ✓ Processed {i}/{len(present_students)} students")
                    
                except (TimeoutException, NoSuchElementException):
                    print(f"   ✗ Failed to find student with roll number {roll_number}")
            
            print(f"✓ Successfully processed {success_count} students!")
            time.sleep(2)
            self.verify_attendance(present_count, absent_count)
            return True
            
        except Exception as e:
            print(f"✗ Error during attendance marking: {e}")
            return False
    
    def verify_attendance(self, expected_present, expected_absent):
        """Verify the attendance summary"""
        try:
            present_element = self.driver.find_element(By.ID, "present-count")
            absent_element = self.driver.find_element(By.ID, "absent-count")
            
            actual_present = int(present_element.text)
            actual_absent = int(absent_element.text)
            
            print(f"📊 Attendance Summary:")
            print(f"   Present: {actual_present} (Expected: {expected_present})")
            print(f"   Absent: {actual_absent} (Expected: {expected_absent})")
            
            if actual_present == expected_present and actual_absent == expected_absent:
                print("✓ Attendance verification successful!")
                return True
            else:
                print("⚠ Attendance counts don't match expected values!")
                return False
                
        except Exception as e:
            print(f"✗ Error verifying attendance: {e}")
            return False
    
    def save_attendance(self):
        """Click the save button"""
        try:
            save_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "save-button"))
            )
            
            print("💾 Clicking save button...")
            save_button.click()
            
            time.sleep(1)
            alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
            print(f"📋 Save confirmation received!")
            alert.accept()
            
            print("✓ Attendance saved successfully!")
            return True
            
        except TimeoutException:
            print("✗ Save button not found or no alert appeared")
            return False
        except Exception as e:
            print(f"✗ Error saving attendance: {e}")
            return False
    
    def close_driver(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("🔒 Browser closed.")

def main():
    # Configuration
    HTML_FILE_PATH = "file:///C:/Users/sumer/Desktop/Automate/attendance.html"
    
    print("🚀 OCR + Attendance Automation")
    print("=" * 50)
    
    # Initialize automator
    automator = OCRAttendanceAutomator(HTML_FILE_PATH)
    
    # Choose input method
    print("📝 Choose input method:")
    print("1. Select image file (OCR)")
    print("2. Manual input")
    
    input_method = input("Choose method (1-2): ").strip()
    
    absent_rolls = []
    
    if input_method == "1":
        # OCR Method
        print("\n📷 Select image containing handwritten absent roll numbers...")
        image_path = automator.select_image_file()
        
        if not image_path:
            print("❌ No image selected. Exiting.")
            return
        
        print(f"📸 Processing: {os.path.basename(image_path)}")
        absent_rolls = automator.extract_numbers_from_image(image_path)
        
        if not absent_rolls:
            print("⚠ No numbers found in image. Try manual input or different image.")
            manual_input = input("Enter roll numbers manually? (y/n): ").lower()
            if manual_input in ['y', 'yes']:
                roll_input = input("Enter absent roll numbers: ").strip()
                if roll_input:
                    from attendance_automation import parse_roll_numbers  # Import from previous script
                    absent_rolls = parse_roll_numbers(roll_input) or []
        
        if absent_rolls:
            print(f"🎯 Extracted absent roll numbers: {absent_rolls}")
            confirm = input("Are these numbers correct? (y/n): ").lower()
            if confirm not in ['y', 'yes']:
                roll_input = input("Enter correct absent roll numbers: ").strip()
                if roll_input:
                    from attendance_automation import parse_roll_numbers
                    absent_rolls = parse_roll_numbers(roll_input) or []
    
    elif input_method == "2":
        # Manual Method
        print("\n📝 Enter roll numbers of ABSENT students:")
        print("Examples: 1,5,10 or 1-5,10,15-20")
        
        roll_input = input("Enter absent roll numbers: ").strip()
        if roll_input:
            from attendance_automation import parse_roll_numbers
            absent_rolls = parse_roll_numbers(roll_input) or []
    
    else:
        print("❌ Invalid choice. Exiting.")
        return
    
    # Get browser choice
    print("\nAvailable browsers:")
    print("1. Chrome (default)")
    print("2. Firefox")
    print("3. Edge")
    
    browser_choice = input("Choose browser (1-3) or press Enter for Chrome: ").strip()
    browser_map = {"1": "chrome", "2": "firefox", "3": "edge", "": "chrome"}
    browser = browser_map.get(browser_choice, "chrome")
    
    print(f"\n📋 Final Configuration:")
    print(f"   Browser: {browser.title()}")
    print(f"   Absent students: {len(absent_rolls)} ({absent_rolls if absent_rolls else 'None'})")
    print(f"   Present students: {80 - len(absent_rolls)}")
    
    confirm = input("\nProceed with automation? (y/n): ").lower()
    if confirm not in ['y', 'yes']:
        print("❌ Operation cancelled.")
        return
    
    try:
        # Run automation
        automator.setup_driver(browser)
        
        if automator.load_page():
            if automator.mark_attendance_by_roll_numbers(absent_rolls):
                save_choice = input("\nSave attendance? (y/n): ").lower()
                if save_choice in ['y', 'yes']:
                    automator.save_attendance()
            
            print("\n⏰ Keeping browser open for 5 seconds...")
            time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n⚠ Automation interrupted by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        automator.close_driver()

if __name__ == "__main__":
    main()