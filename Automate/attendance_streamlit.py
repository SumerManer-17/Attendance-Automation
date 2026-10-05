import streamlit as st
import pytesseract
from PIL import Image
import os
from attendance_automation import AttendanceAutomator, parse_roll_numbers

# Path to Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Local HTML file path
HTML_FILE_PATH = "file:///C:/Users/sumer/Desktop/Automate/attendance.html"

# Streamlit UI
st.set_page_config(page_title="Attendance Automation", page_icon="🧠", layout="centered")
st.title("🧾 Attendance Automation System")

st.write("Use this tool to automate attendance marking based on roll numbers or uploaded image (OCR).")

# --- Input section ---
option = st.radio("Select Input Type:", ["Manual Entry", "Image Upload"])

roll_input = ""

if option == "Manual Entry":
    roll_input = st.text_input("Enter ABSENT roll numbers (e.g. 1,2,3 or 1-5,10,15-20):")

elif option == "Image Upload":
    uploaded_file = st.file_uploader("Upload an image with roll numbers", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)

        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789,-'
        text = pytesseract.image_to_string(image, config=custom_config)
        roll_input = text.strip().replace("\n", "").replace(" ", "")
        st.success(f"OCR Extracted Rolls: {roll_input}")

# --- Execute button ---
if st.button("🚀 Run Attendance Automation"):
    if roll_input.strip() == "":
        st.warning("Please enter or upload roll numbers first.")
    else:
        absent_rolls = parse_roll_numbers(roll_input)
        if absent_rolls is None:
            st.error("Invalid roll number format. Please check and try again.")
        else:
            st.info(f"Running automation... Absent Rolls: {absent_rolls}")

            automator = AttendanceAutomator(HTML_FILE_PATH)
            automator.setup_driver("chrome")

            if automator.load_page():
                if automator.mark_attendance_by_roll_numbers(absent_rolls):
                    automator.save_attendance()
                    st.success("✅ Attendance marked and saved successfully!")
                else:
                    st.error("⚠ Failed to mark attendance properly.")
            automator.close_driver()
