# app.py
import os
import re
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

# Install: pip install google-genai
from google import genai

from attendance_automation import AttendanceAutomator, parse_roll_numbers

# -------------------------
# Configuration / constants
# -------------------------
# Prefer setting your key as an environment variable:
GOOGLE_API_KEY="AIzaSyCtHitiysfg-__FxQVk-fmsWeMbnRqc75o"
API_KEY = os.environ.get("GOOGLE_API_KEY")  # fallback: None
# If you must hardcode for testing (not recommended), set API_KEY = "YOUR_KEY" here.

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif"}
HTML_FILE_PATH = "file:///C:/Users/sumer/Desktop/Automate/attendance.html"  # adjust if needed

# Choose a vision-enabled Gemini model. If you get an error, replace with a model name your account supports.
# Examples (may vary by account): "gemini-2.0-flash", "gemini-1.5-pro-vision", "gemini-2.5-pro"
# Use the model name your project/account has access to.
MODEL_NAME = "gemini-2.5-pro"

# -------------------------
# Flask app setup
# -------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")  # change in production
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------
# GenAI client
# -------------------------
if not API_KEY:
    # Try common alternative env var name if user used GEMINI_API_KEY
    API_KEY = os.environ.get("GEMINI_API_KEY")

# Create client. Client will also read from environment if API key not provided here.
client = genai.Client(api_key=API_KEY)

# -------------------------
# Helpers
# -------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_numbers_with_gemini(image_path: str):
    """
    Upload the image to the GenAI file service and call generate_content with the uploaded file.
    Returns (numbers_list, cleaned_text)
    """
    try:
        # Upload file to Gemini/GenAI file store (re-usable file object)
        # The client.files.upload(...) pattern is recommended for multimodal inputs. :contentReference[oaicite:2]{index=2}
        print(f"Uploading file to GenAI: {image_path}")
        uploaded = client.files.upload(file=image_path)
        print("Uploaded file id/info:", uploaded)

        prompt = (
            "Extract only the roll numbers separated by commas from this image. "
            "Return ONLY digits and commas. No words, no explanation, no labels."
        )

        # Call model with the prompt and the uploaded image file in 'contents'
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, uploaded],
            # optionally you can add max_output_tokens, temperature, etc.
        )

        # Debug: show full response (useful when things go wrong)
        print("Full response object:", response)

        text = (response.text or "").strip()
        print("🔍 Gemini raw text:", repr(text))

        # Post-process: keep digits and commas only
        cleaned = re.sub(r"[^0-9,]", "", text)
        numbers = [n.strip() for n in cleaned.split(",") if n.strip()]
        return numbers, cleaned

    except Exception as e:
        # Provide helpful debug output
        print("Error calling Gemini/GenAI:", str(e))
        # Return empty so upstream can handle gracefully
        return [], ""

# -------------------------
# Routes
# -------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        roll_input = ""

        # Case 1: manual input from form
        if request.form.get("roll_numbers"):
            roll_input = request.form["roll_numbers"].strip()

        # Case 2: uploaded image (process with Gemini)
        elif "image" in request.files:
            image_file = request.files["image"]
            if image_file and image_file.filename != "" and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                image_file.save(filepath)
                print("Saved uploaded image to:", filepath)

                numbers, raw_text = extract_numbers_with_gemini(filepath)
                # If no numbers returned, include the raw_text in logs for debugging
                if not numbers:
                    print("No numbers found by Gemini. Raw text:", raw_text)
                    flash("Couldn't extract roll numbers from the image. Try a clearer image or manual input.", "warning")
                else:
                    roll_input = ",".join(numbers)
                    print("✅ Cleaned (joined):", roll_input)
            else:
                flash("No valid image uploaded. Allowed: png, jpg, jpeg, bmp, gif", "danger")

        if roll_input:
            try:
                absent_rolls = parse_roll_numbers(roll_input)
                print("📌 Parsed rolls:", absent_rolls)

                # Run Selenium live
                automator = AttendanceAutomator(HTML_FILE_PATH)
                automator.setup_driver("chrome")

                if automator.load_page():
                    automator.mark_attendance_by_roll_numbers(absent_rolls)
                    automator.save_attendance()

                    # NOTE: input(...) will block the Flask worker thread/process.
                    # If you're running this in production or want non-blocking behavior,
                    # remove this and close the driver programmatically or run automation outside the Flask request.
                    input("✅ Attendance done in browser. Press Enter to close browser...")
                    automator.close_driver()

                return f"✅ Attendance executed. Rolls: {absent_rolls}"
            except Exception as e:
                print("Error during attendance automation:", str(e))
                flash("An error occurred while running the attendance script. Check server logs.", "danger")
                return redirect(url_for("index"))

    return render_template("index.html")

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # For development only. In production use a WSGI server.
    app.run(debug=True, host="0.0.0.0", port=5000)
