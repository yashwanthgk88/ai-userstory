#!/bin/bash
set -e

BASE="http://localhost:8000/api"
DATA_DIR="$(dirname "$0")"

echo "=== SecureReq AI Test Data Seeder ==="

# --- Auth ---
echo "[1/6] Registering users..."
curl -sf -X POST "$BASE/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"alice@acme.com","password":"Secure#Pass1","full_name":"Alice Chen"}' > /dev/null 2>&1 || true
curl -sf -X POST "$BASE/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"bob@acme.com","password":"Secure#Pass2","full_name":"Bob Martinez"}' > /dev/null 2>&1 || true

TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"alice@acme.com","password":"Secure#Pass1"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"
echo "  Logged in as alice@acme.com"

# --- Projects ---
echo "[2/6] Creating projects..."
P1=$(curl -sf -X POST "$BASE/projects" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"name":"RetireWell Platform","description":"Customer-facing retirement planning application handling SSN, financial data, and investment portfolios"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Project 1 (RetireWell): $P1"

P2=$(curl -sf -X POST "$BASE/projects" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"name":"HealthBridge HSA","description":"Health Savings Account platform with medical expense tracking, PHI handling, and insurance integration"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Project 2 (HealthBridge): $P2"

P3=$(curl -sf -X POST "$BASE/projects" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"name":"PaySecure Gateway","description":"Payment processing microservice handling credit card transactions, wire transfers, and merchant settlements"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Project 3 (PaySecure): $P3"

# --- Custom Standards ---
echo "[3/6] Uploading custom security standards..."
curl -sf -X POST "$BASE/projects/$P1/standards" -H "$AUTH" \
  -F "name=ACME Enterprise Security Standard v2.1" \
  -F "description=Organization-wide security controls mandated by CISO office. Covers data residency, API security, credential management, and deployment gates." \
  -F "file=@$DATA_DIR/acme-security-standard.json" > /dev/null
echo "  Uploaded ACME Security Standard to RetireWell"

curl -sf -X POST "$BASE/projects/$P2/standards" -H "$AUTH" \
  -F "name=ACME Enterprise Security Standard v2.1" \
  -F "description=Organization-wide security controls" \
  -F "file=@$DATA_DIR/acme-security-standard.json" > /dev/null
echo "  Uploaded ACME Security Standard to HealthBridge"

curl -sf -X POST "$BASE/projects/$P2/standards" -H "$AUTH" \
  -F "name=ACME Internal HIPAA Policy" \
  -F "description=Internal HIPAA compliance requirements that exceed regulatory minimums. Includes PHI encryption, access logging, breach notification, and consent management." \
  -F "file=@$DATA_DIR/hipaa-internal-policy.csv" > /dev/null
echo "  Uploaded HIPAA Internal Policy to HealthBridge"

curl -sf -X POST "$BASE/projects/$P3/standards" -H "$AUTH" \
  -F "name=ACME Enterprise Security Standard v2.1" \
  -F "description=Organization-wide security controls" \
  -F "file=@$DATA_DIR/acme-security-standard.json" > /dev/null
echo "  Uploaded ACME Security Standard to PaySecure"

# --- User Stories ---
echo "[4/6] Creating user stories..."

# RetireWell stories
S1=$(curl -sf -X POST "$BASE/projects/$P1/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"User Registration with SSN Verification","description":"As a new customer, I want to register for an account by providing my personal information including name, email, phone number, date of birth, and Social Security Number so that my identity can be verified and I can access retirement planning services.","acceptance_criteria":"1. User provides full name, email, phone, DOB, SSN\n2. SSN is validated against identity verification service\n3. User receives confirmation email\n4. Account is created in pending state until email verified"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: User Registration with SSN ($S1)"

S2=$(curl -sf -X POST "$BASE/projects/$P1/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Investment Portfolio Dashboard","description":"As an investor, I want to view my complete investment portfolio including account balances, asset allocation, transaction history, and beneficiary information so I can track my retirement savings progress.","acceptance_criteria":"1. Display all account balances in real-time\n2. Show asset allocation pie chart\n3. List last 90 days of transactions\n4. Show beneficiary details with edit capability"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Portfolio Dashboard ($S2)"

S3=$(curl -sf -X POST "$BASE/projects/$P1/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Password Reset Functionality","description":"As a user who has forgotten my password, I want to reset it using my registered email address so that I can regain access to my account securely.","acceptance_criteria":"1. User enters email address\n2. System sends reset link (valid 15 min)\n3. User sets new password meeting complexity requirements\n4. All existing sessions are invalidated"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Password Reset ($S3)"

S4=$(curl -sf -X POST "$BASE/projects/$P1/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Beneficiary Management","description":"As an account holder, I want to add, update, or remove beneficiaries for my retirement accounts, including their name, date of birth, SSN, relationship, and percentage allocation.","acceptance_criteria":"1. Add beneficiary with name, DOB, SSN, relationship\n2. Set percentage allocation (must total 100%)\n3. Require step-up authentication for changes\n4. Email notification on any beneficiary change"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Beneficiary Management ($S4)"

# HealthBridge stories
S5=$(curl -sf -X POST "$BASE/projects/$P2/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Medical Expense Reimbursement Upload","description":"As an HSA account holder, I want to upload medical receipts and healthcare provider invoices containing diagnosis codes and treatment information to request reimbursement for qualified medical expenses.","acceptance_criteria":"1. Upload PDF/JPG receipt (max 10MB)\n2. OCR extracts provider name, date, amount, diagnosis code\n3. System validates against IRS qualified expense list\n4. Reimbursement approved or flagged for review"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Medical Expense Upload ($S5)"

S6=$(curl -sf -X POST "$BASE/projects/$P2/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Healthcare Provider Search and Selection","description":"As a patient, I want to search for in-network healthcare providers by specialty, location, and rating, then save my preferred providers to my profile for quick access when filing claims.","acceptance_criteria":"1. Search by specialty, ZIP code, radius\n2. Display provider name, address, phone, rating\n3. Show real-time network status\n4. Save up to 10 preferred providers"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Provider Search ($S6)"

S7=$(curl -sf -X POST "$BASE/projects/$P2/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Export Health Records for Doctor Visit","description":"As a patient, I want to export my complete health records including diagnosis history, medications, lab results, and immunization records as a PDF or FHIR bundle so I can share them with a new healthcare provider.","acceptance_criteria":"1. Select date range and record categories to export\n2. Generate PDF with all selected records\n3. Optional FHIR R4 bundle export\n4. Download link valid for 24 hours\n5. Log all export events for HIPAA compliance"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Health Records Export ($S7)"

# PaySecure stories
S8=$(curl -sf -X POST "$BASE/projects/$P3/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Credit Card Payment Processing","description":"As a customer, I want to make payments using my credit card so that I can fund my investment account. The system should accept Visa, Mastercard, and American Express cards and process payments in real-time with 3D Secure verification.","acceptance_criteria":"1. Accept Visa, Mastercard, Amex\n2. PCI-compliant card entry form (iframe from processor)\n3. 3D Secure 2.0 authentication\n4. Real-time authorization with fraud check\n5. Email receipt on success"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Credit Card Processing ($S8)"

S9=$(curl -sf -X POST "$BASE/projects/$P3/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Wire Transfer for Large Transactions","description":"As a customer, I want to initiate wire transfers from my account to external bank accounts for amounts over $50,000, providing routing number and account number for the destination bank.","acceptance_criteria":"1. Enter destination routing number and account number\n2. Verify beneficiary name via bank lookup\n3. Dual approval required for amounts over $25,000\n4. 24-hour hold for first-time beneficiaries\n5. SMS and email confirmation with transaction reference"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Wire Transfer ($S9)"

S10=$(curl -sf -X POST "$BASE/projects/$P3/stories" -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"title":"Merchant Onboarding and KYC","description":"As a merchant, I want to complete the onboarding process by submitting my business registration documents, tax ID, bank account details for settlements, and completing Know Your Customer verification so I can start accepting payments through the platform.","acceptance_criteria":"1. Upload business license, tax ID document, bank statement\n2. Automated document verification via OCR\n3. KYC check against sanctions lists (OFAC, EU, UN)\n4. Bank account verification via micro-deposits\n5. Compliance team review for high-risk merchant categories"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Story: Merchant KYC ($S10)"

# --- Run Analyses ---
echo "[5/6] Running security analyses on all stories..."
for SID in $S1 $S2 $S3 $S4 $S5 $S6 $S7 $S8 $S9 $S10; do
  RESULT=$(curl -sf -X POST "$BASE/stories/$SID/analyze" -H "$AUTH")
  RISK=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Risk:{d['risk_score']:>3}/100 | Abuse:{len(d['abuse_cases']):>2} | Reqs:{len(d['security_requirements']):>2} | Model:{d['ai_model_used']}\")")
  echo "$RISK"
done

# --- Verify Compliance Mappings ---
echo "[6/6] Verifying compliance mappings include custom standards..."
# Get latest analysis for the SSN registration story (S1)
ANALYSIS_ID=$(curl -sf "$BASE/stories/$S1/analyses" -H "$AUTH" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
COMPLIANCE=$(curl -sf "$BASE/analyses/$ANALYSIS_ID/compliance" -H "$AUTH")
echo "$COMPLIANCE" | python3 -c "
import sys, json
from collections import Counter
data = json.load(sys.stdin)
standards = Counter(m['standard_name'] for m in data)
print(f'  Total mappings: {len(data)}')
for std, count in standards.most_common():
    marker = ' *** CUSTOM' if 'ACME' in std or 'HIPAA' in std.upper() else ''
    print(f'    {std}: {count} controls{marker}')
"

echo ""
echo "=== Seeding complete! ==="
echo "Open http://localhost:3000 and login with alice@acme.com / Secure#Pass1"
echo "3 projects, 10 stories, 10 analyses, 2 custom standards loaded."
