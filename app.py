import os
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

prompt = """
You are an expert OCR data extraction system for financial documents.
Your task is to meticulously analyze the provided image of a Thai money transfer slip and extract key information.

Return the data ONLY in a valid, raw JSON object format. Do not include any explanatory text, markdown formatting like ```json, or anything outside of the JSON structure itself.

The required JSON schema is as follows:
{
  "bank": "The name of the bank (e.g., K-Bank, SCB, Krungthai, TTB)",
  "recipient_name": "The full name of the recipient",
  "amount": 0.00,
  "transaction_datetime": "YYYY-MM-DD HH:MM",
  "transaction_id": "The transaction reference number or ID"
}

**Crucial Rules:**
1.  **Data Types:** The `amount` field MUST be a numeric type (float or integer), not a string.
2.  **Date and Year Conversion:** You MUST convert the Thai Buddhist year (e.g., 2568, 68) to the corresponding Gregorian year (e.g., 2025). The final `transaction_datetime` must be in YYYY-MM-DD HH:MM format.
3.  **Missing Information:** If any piece of information cannot be found or is not present on the slip, use `null` as the value for that field. Do not omit the key.
4.  **Recipient Name:** Extract the full name of the recipient, excluding any bank account numbers or "PromptPay" labels.
5.  **Bank Name:** Identify the bank from its logo or text (e.g., K+, Krungthai, SCB EASY).
6.  **DateTime Format:** Combine date and time into a single field in YYYY-MM-DD HH:MM format.
"""

def extract_slip_data_with_gemini(image_path: str) -> dict:
    model = genai.GenerativeModel('gemini-2.5-pro')
    image_file = genai.upload_file(path=image_path)
    response = model.generate_content([prompt, image_file])
    cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(cleaned_response_text)
    if data.get("transaction_datetime"):
        dt = datetime.strptime(data["transaction_datetime"], "%Y-%m-%d %H:%M")
        data["transaction_datetime"] = dt.isoformat()
    return data

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    extracted_data = extract_slip_data_with_gemini(image_path=filepath)
    os.remove(filepath)

    return jsonify(extracted_data)

if __name__ == '__main__':
    app.run(debug=True, port=5001)