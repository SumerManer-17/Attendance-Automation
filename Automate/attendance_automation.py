from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from pathlib import Path


class AttendanceAutomator:
    def __init__(self, html_file_path):
        """
        Initialize the attendance automator
        """
        self.driver = None
        self.html_file_path = html_file_path
        self.total_students = 81

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
                chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument("--start-maximized")
                chrome_options.add_experimental_option("detach", True)

                # Automatically download and manage ChromeDriver
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                # Fallback: try without webdriver-manager
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

        else:
            raise ValueError(f"Unsupported browser: {browser}")

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
            print("✗ Failed to load the page. Check your file path or studentList ID.")
            return False

    def mark_attendance_by_roll_numbers(self, absent_roll_numbers):
        """
        Mark attendance by specifying exact roll numbers to keep absent
        All other students will be marked present
        """
        if not absent_roll_numbers:
            absent_roll_numbers = []

        invalid_rolls = [roll for roll in absent_roll_numbers if roll < 1 or roll > 81]
        if invalid_rolls:
            print(f"✗ Invalid roll numbers: {invalid_rolls}. Must be between 1 and 81.")
            return False

        present_count = 81 - len(absent_roll_numbers)
        absent_count = len(absent_roll_numbers)

        print(f"📋 Marking attendance:")
        print(f"   Present: {present_count} students")
        print(f"   Absent: {absent_count} students (Roll numbers: {sorted(absent_roll_numbers)})")

        try:
            all_students = list(range(1, 81))
            present_students = [roll for roll in all_students if roll not in absent_roll_numbers]

            print(f"🔄 Processing {len(present_students)} students to mark present...")

            success_count = 0
            failed_rolls = []

            for i, roll_number in enumerate(present_students, 1):
                try:
                    if i % 20 == 0:
                        time.sleep(0.5)

                    toggle_input = self.driver.find_element(By.ID, str(roll_number))

                    if not toggle_input.is_selected():
                        self.driver.execute_script("arguments[0].click();", toggle_input)
                    success_count += 1

                    if i % 20 == 0 or i == len(present_students):
                        print(f"   ✓ Processed {i}/{len(present_students)} students")

                except (TimeoutException, NoSuchElementException):
                    failed_rolls.append(roll_number)
                    print(f"   ✗ Failed to find student with roll number {roll_number}")

            print(f"✓ Successfully processed {success_count} students!")

            if failed_rolls:
                print(f"⚠ Failed to process roll numbers: {failed_rolls}")

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
            alert_text = alert.text
            print(f"📋 Save confirmation received: {alert_text}")
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


def parse_roll_numbers(input_string):
    """
    Parse roll numbers from user input
    Supports: "1,2,3" or "1 2 3" or "1-5,7,9-12"
    """
    if not input_string.strip():
        return []

    roll_numbers = []
    try:
        parts = input_string.replace(' ', ',').split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                start, end = part.split('-', 1)
                roll_numbers.extend(range(int(start), int(end) + 1))
            else:
                roll_numbers.append(int(part))
        return sorted(list(set(roll_numbers)))
    except ValueError:
        print("✗ Invalid format. Examples: '1,2,3' or '1-5,7,9-12'")
        return None


def main():
    # Safe HTML file path
    HTML_FILE_PATH = Path(r"C:\Users\sumer\Desktop\Automate\attendance.html").absolute().as_uri()

    print("🚀 Starting Attendance Automation")
    print("=" * 50)

    print("Available browsers:")
    print("1. Chrome (default)")
    print("2. Firefox")
    print("3. Edge")

    browser_choice = input("Choose browser (1-3) or press Enter for Chrome: ").strip()
    browser_map = {"1": "chrome", "2": "firefox", "3": "edge", "": "chrome"}
    browser = browser_map.get(browser_choice, "chrome")

    print("\n📝 Enter roll numbers of ABSENT students:")
    print("Examples: 1,5,10 or 1-5,10,15-20")
    print("Leave empty if all students are present")

    while True:
        roll_input = input("\nEnter absent roll numbers: ").strip()
        if not roll_input:
            absent_rolls = []
            break
        absent_rolls = parse_roll_numbers(roll_input)
        if absent_rolls is not None:
            invalid_rolls = [r for r in absent_rolls if r < 1 or r > 81]
            if invalid_rolls:
                print(f"✗ Invalid roll numbers: {invalid_rolls}. Must be between 1 and 81.")
                continue
            break

    print(f"\n📋 Configuration:")
    print(f"   Browser: {browser.title()}")
    print(f"   Absent students: {len(absent_rolls)} ({absent_rolls if absent_rolls else 'None'})")
    print(f"   Present students: {81 - len(absent_rolls)}")

    confirm = input("\nProceed with this configuration? (y/n): ").lower()
    if confirm not in ['y', 'yes']:
        print("❌ Operation cancelled.")
        return

    automator = AttendanceAutomator(HTML_FILE_PATH)

    try:
        automator.setup_driver(browser)
        if automator.load_page():
            if automator.mark_attendance_by_roll_numbers(absent_rolls):
                save_choice = input("\nDo you want to save the attendance? (y/n): ").lower()
                if save_choice in ['y', 'yes']:
                    automator.save_attendance()
                else:
                    print("⏭ Skipping save step.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        automator.close_driver()


if __name__ == "__main__":
    main()
