from flask import Flask, render_template, request, jsonify, send_from_directory
import uuid
import os
import json
import math
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB limit
GEMINI_API_KEY = "AIzaSyCYrQhnsoaXhdiiA__mc3IOmCLwGK0lN7E" # Replaced with user provided key

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_bill_details(file_path, mime_type):
    # Removed as per user request. Fallback to manual entry.
    return None


# --- In-Memory Data Storage ---

# Budgets for different events
# Added 'last_alerted_percent' to track alerts
BUDGETS = {
    "TechFest": {"total": 50000, "used": 12000, "last_alerted_percent": 100},
    "Workshop": {"total": 20000, "used": 5000, "last_alerted_percent": 100},
    "Cultural Event": {"total": 100000, "used": 45000, "last_alerted_percent": 100}
}

# List of claims
# Each claim: { id, event, category, amount, description, status (Pending/Approved/Rejected), timestamp }
CLAIMS = []

# List of alerts
# Each alert: { id, event, remaining_percent, remaining_amount, severity, message, timestamp }
ALERTS = []

# --- Routes ---

@app.route('/')
def member_portal():
    """Renders the Member Portal for submitting claims."""
    return render_template('index.html', events=BUDGETS.keys(), alerts=ALERTS)


@app.route('/admin')
def admin_dashboard():
    """Renders the Admin Dashboard."""
    return render_template('dashboard.html')

# --- API Endpoints ---

@app.route('/api/claim', methods=['POST'])
def submit_claim():
    """Handle new reimbursement claim submission."""
    try:
        data = request.form
        file = request.files.get('receipt')

        # Basic Validation
        if not file or file.filename == '':
            return jsonify({"success": False, "message": "No file uploaded"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Invalid file type. Only PNG, JPG, JPEG, PDF allowed."}), 400

        # Secure save with UUID
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{original_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Ensure directory exists (just in case)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(file_path)
        
        # Manual Mode: Data extraction skipped. Admin will enter amount.
        amount = 0.0
        
        claim_id = str(uuid.uuid4())
        new_claim = {
            "id": claim_id,
            "event": data.get('event'),
            "category": data.get('category'),
            "amount": amount,
            "description": f"Receipt for {data.get('category')}", # Generic description
            "bill_filename": unique_filename,
            "status": "Pending" 
        }
        
        CLAIMS.append(new_claim)
        
        return jsonify({"success": True, "message": "Claim submitted! Waiting for Admin verification."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/data', methods=['GET'])
def get_data():
    """Fetch all claims and current budget status."""
    return jsonify({
        "budgets": BUDGETS,
        "claims": CLAIMS,
        "alerts": ALERTS
    })

@app.route('/api/approve/<claim_id>', methods=['POST'])
def approve_claim(claim_id):
    """Approve a claim if budget allows. Admin must provide verified amount."""
    try:
        data = request.json # Get JSON body
        approved_amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid amount provided"}), 400

    claim = next((c for c in CLAIMS if c['id'] == claim_id), None)
    if not claim:
        return jsonify({"success": False, "message": "Claim not found"}), 404
    
    event = claim['event']
    amount = approved_amount # Use the amount verified by admin
    
    budget = BUDGETS.get(event)
    
    if not budget:
         return jsonify({"success": False, "message": "Event budget not found"}), 404

    remaining = budget['total'] - budget['used']
    
    if amount > remaining:
        return jsonify({"success": False, "message": "Insufficient budget remaining!"}), 400
    
    # Update state
    claim['status'] = 'Approved'
    claim['amount'] = amount # Update claim with verified amount
    budget['used'] += amount
    
    # --- Alert Logic ---
    total = budget['total']
    used = budget['used']
    remaining = total - used
    
    # Calculate percentages
    remaining_percent = math.floor((remaining / total) * 100)
    last_alerted = budget.get('last_alerted_percent', 100)
    
    # Check if we need to alert (Threshold <= 15% AND dropped by at least 1%)
    if remaining_percent <= 15 and remaining_percent < last_alerted:
        
        # Determine Severity
        severity = 'warning'
        if remaining_percent == 0:
            severity = 'exhausted'
        elif remaining_percent <= 5:
            severity = 'critical'
            
        # Message
        msg = f"{event} budget low: {remaining_percent}% remaining (₹{remaining:,.2f} left)."
        if severity == 'exhausted':
             msg = f"❌ {event} exhausted: 0% remaining."
        elif severity == 'critical':
             msg = f"🚨 {event} critical: {remaining_percent}% remaining (₹{remaining:,.2f} left)."
        else:
             msg = f"⚠ {msg}"

        # Create Alert
        new_alert = {
            "id": str(uuid.uuid4()),
            "event": event,
            "remaining_percent": remaining_percent,
            "remaining_amount": remaining,
            "severity": severity,
            "message": msg,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        ALERTS.insert(0, new_alert) # Add to top
        budget['last_alerted_percent'] = remaining_percent # Update tracker

    return jsonify({"success": True, "message": "Claim Approved"})

@app.route('/api/reject/<claim_id>', methods=['POST'])
def reject_claim(claim_id):
    """Reject a claim."""
    claim = next((c for c in CLAIMS if c['id'] == claim_id), None)
    if not claim:
        return jsonify({"success": False, "message": "Claim not found"}), 404
    
    claim['status'] = 'Rejected'
    return jsonify({"success": True, "message": "Claim Rejected"})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Chatbot Endpoint ---
@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests with Gemini."""
    if not GEMINI_API_KEY:
        return jsonify({"response": "I'm currently offline (API Key Missing). To submit a claim, upload your bill and select the event!"})
    
    try:
        user_message = request.json.get('message', '')
        
        # 1. Build Context
        budget_summary = "\n".join([
            f"- {name}: ₹{b['used']} used of ₹{b['total']} ({math.floor(((b['total']-b['used'])/b['total'])*100)}% left)"
            for name, b in BUDGETS.items()
        ])
        
        pending_claims = len([c for c in CLAIMS if c['status'] == 'Pending'])
        approved_claims = len([c for c in CLAIMS if c['status'] == 'Approved'])
        
        recent_alerts = "\n".join([a['message'] for a in ALERTS[:3]]) if ALERTS else "No recent alerts."
        
        system_instruction = f"""
        You are BudgetEase Assistant, an AI helper for a college club expense system.
        Explain things clearly, briefly, and practically.
        DO NOT mention python code or internal APIs.
        
        Current System State:
        [Budgets]
        {budget_summary}
        
        [Statistics]
        Pending Claims: {pending_claims}
        Approved Claims: {approved_claims}
        
        [Recent Alerts]
        {recent_alerts}
        
        If asked about how to use the system:
        - Members: Screen allows uploading bills. System extracts amount automatically (extracted by Gemini).
        - Admins: Dashboard allows verifying and approving claims.
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
        response = model.generate_content(user_message)
        
        return jsonify({"response": response.text})
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        # Fallback response
        return jsonify({"response": "I'm having trouble connecting right now. Generally, you can submit claims on the home page and track them here."})


if __name__ == '__main__':
    app.run(debug=True)
