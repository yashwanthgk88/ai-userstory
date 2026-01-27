"""Fallback keyword-based security analysis when Claude API is unavailable."""

import uuid


def _id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:03d}"


# Pattern detection keywords mapped to categories
PATTERNS = {
    "authentication": {
        "keywords": ["password", "login", "register", "authentication", "sign in", "sign up", "reset", "credentials"],
        "abuse_cases": [
            {"threat": "Credential Stuffing Attack", "actor": "External Attacker", "description": "Automated attack using breached username/password combinations.", "impact": "Critical", "likelihood": "High", "attack_vector": "Automated login attempts, botnet", "stride_category": "Spoofing"},
            {"threat": "Brute Force Password Attack", "actor": "External Attacker", "description": "Systematic attempt to guess passwords through automated tools.", "impact": "High", "likelihood": "High", "attack_vector": "Password cracking tools, dictionary attacks", "stride_category": "Spoofing"},
            {"threat": "Session Hijacking", "actor": "External Attacker", "description": "Attacker steals or predicts session tokens to impersonate authenticated users.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "XSS, network sniffing, session fixation", "stride_category": "Spoofing"},
            {"threat": "Password Reset Token Exploitation", "actor": "External Attacker", "description": "Exploiting weak password reset mechanism via predictable tokens or timing attacks.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "Token prediction, email interception", "stride_category": "Spoofing"},
            {"threat": "Account Enumeration", "actor": "External Attacker", "description": "Determining valid usernames through error response differences.", "impact": "Medium", "likelihood": "High", "attack_vector": "Response analysis, timing attacks", "stride_category": "Information Disclosure"},
        ],
        "requirements": [
            {"text": "Implement adaptive MFA for all users", "priority": "Critical", "category": "Authentication & Access Control", "details": "Require MFA for login, sensitive operations, and new device registration."},
            {"text": "Hash passwords using Argon2id with memory cost >=64MB", "priority": "Critical", "category": "Authentication & Access Control", "details": "Never use MD5, SHA1, or plain SHA256 for passwords."},
            {"text": "Enforce password policy: 12+ chars, breach database check", "priority": "High", "category": "Authentication & Access Control", "details": "Check against HaveIBeenPwned API. Block common passwords."},
            {"text": "Implement progressive account lockout", "priority": "High", "category": "Authentication & Access Control", "details": "5 failures = 15min, 10 = 1hr, 15 = 24hr lockout."},
            {"text": "Generate cryptographically secure password reset tokens (256-bit)", "priority": "High", "category": "Authentication & Access Control", "details": "Tokens expire in 15 minutes. Single-use only."},
        ],
    },
    "pii_ssn": {
        "keywords": ["ssn", "social security", "pii", "personal information", "date of birth", "dob"],
        "abuse_cases": [
            {"threat": "SSN Harvesting Attack", "actor": "External Attacker", "description": "Exploiting vulnerabilities to harvest SSNs for identity theft.", "impact": "Critical", "likelihood": "High", "attack_vector": "API exploitation, SQL injection, insider threat", "stride_category": "Information Disclosure"},
            {"threat": "SSN Enumeration via Error Messages", "actor": "External Attacker", "description": "Using error messages to determine valid SSN formats.", "impact": "High", "likelihood": "Medium", "attack_vector": "Input fuzzing, error analysis", "stride_category": "Information Disclosure"},
            {"threat": "Identity Theft via SSN Exposure in Logs", "actor": "Malicious Insider", "description": "SSN data logged in plain text accessed by unauthorized personnel.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "Log file access, SIEM exploitation", "stride_category": "Information Disclosure"},
        ],
        "requirements": [
            {"text": "Encrypt all PII at rest using AES-256-GCM", "priority": "Critical", "category": "Data Protection", "details": "Use HSM for key management. Implement envelope encryption."},
            {"text": "Implement field-level encryption for SSN and DOB", "priority": "Critical", "category": "Data Protection", "details": "Separate key per data classification. Key rotation every 90 days."},
            {"text": "Apply data masking for all non-production environments", "priority": "High", "category": "Data Protection", "details": "Show last 4 digits only for SSN. Irreversible masking."},
            {"text": "Configure PII detection scanning for all data stores", "priority": "Medium", "category": "Data Protection", "details": "Automated scanning to discover and classify sensitive data."},
        ],
    },
    "payment": {
        "keywords": ["credit card", "payment", "visa", "mastercard", "card number", "pan", "cvv"],
        "abuse_cases": [
            {"threat": "Credit Card Skimming (Magecart)", "actor": "External Attacker", "description": "Malicious code injected to capture card details during payment.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "JavaScript injection, compromised third-party scripts", "stride_category": "Information Disclosure"},
            {"threat": "Payment Fraud via Stolen Cards", "actor": "External Attacker", "description": "Use of stolen credit card information for fraudulent payments.", "impact": "High", "likelihood": "High", "attack_vector": "Purchased card data, phishing", "stride_category": "Spoofing"},
            {"threat": "Transaction Manipulation", "actor": "External Attacker", "description": "Manipulation of payment amounts through parameter tampering.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "Request interception, parameter manipulation", "stride_category": "Tampering"},
        ],
        "requirements": [
            {"text": "Never store full PAN - use PCI-certified tokenization", "priority": "Critical", "category": "Financial & Transaction Security", "details": "Integrate with payment processor tokenization. Store only last 4 digits."},
            {"text": "Implement PCI DSS v4.0 controls for cardholder data", "priority": "Critical", "category": "Regulatory Compliance", "details": "Segment CDE network. Implement all 12 PCI DSS requirements."},
            {"text": "Deploy real-time fraud detection with ML-based scoring", "priority": "Critical", "category": "Financial & Transaction Security", "details": "Score transactions based on amount, frequency, location, device."},
            {"text": "Implement secure payment page isolation", "priority": "Critical", "category": "Financial & Transaction Security", "details": "Host payment forms on isolated subdomain. Strict CSP."},
        ],
    },
    "file_upload": {
        "keywords": ["upload", "file", "document", "attachment", "receipt", "image"],
        "abuse_cases": [
            {"threat": "Malware Upload", "actor": "External Attacker", "description": "Upload of malicious files disguised as legitimate documents.", "impact": "Critical", "likelihood": "High", "attack_vector": "File extension spoofing, MIME type manipulation", "stride_category": "Tampering"},
            {"threat": "Web Shell Upload", "actor": "External Attacker", "description": "Upload of server-side scripts for remote command execution.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "PHP/ASP shell upload, double extensions", "stride_category": "Elevation of Privilege"},
            {"threat": "Path Traversal via Filename", "actor": "External Attacker", "description": "Manipulated filenames to write files outside intended directory.", "impact": "High", "likelihood": "Medium", "attack_vector": "Filename manipulation (../)", "stride_category": "Tampering"},
        ],
        "requirements": [
            {"text": "Validate file uploads: type whitelist, magic bytes, size limits, AV scan", "priority": "Critical", "category": "Input Validation", "details": "Verify MIME type matches content. Scan with multiple AV engines."},
            {"text": "Validate and sanitize all file paths to prevent path traversal", "priority": "High", "category": "Input Validation", "details": "Use canonical path validation. Whitelist allowed directories."},
            {"text": "Implement request size limits on all upload endpoints", "priority": "High", "category": "Input Validation", "details": "Limit to 10MB for file uploads. Rate limit by IP and user."},
        ],
    },
    "wire_transfer": {
        "keywords": ["wire transfer", "routing number", "bank account", "transfer", "ach"],
        "abuse_cases": [
            {"threat": "Business Email Compromise (BEC)", "actor": "External Attacker", "description": "Impersonating executive to authorize fraudulent wire transfer.", "impact": "Critical", "likelihood": "High", "attack_vector": "Email spoofing, account compromise", "stride_category": "Spoofing"},
            {"threat": "Wire Transfer Redirection", "actor": "External Attacker", "description": "Manipulating beneficiary bank details to redirect funds.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "Account takeover, parameter tampering", "stride_category": "Tampering"},
        ],
        "requirements": [
            {"text": "Require dual authorization for wire transfers >$10,000", "priority": "Critical", "category": "Financial & Transaction Security", "details": "Two different authorized users must approve."},
            {"text": "Implement out-of-band verification for high-risk transactions", "priority": "High", "category": "Financial & Transaction Security", "details": "Send confirmation to registered phone/email."},
            {"text": "Deploy beneficiary verification with cooling-off period", "priority": "High", "category": "Financial & Transaction Security", "details": "24-hour delay for first transfer to new beneficiary."},
        ],
    },
    "health_data": {
        "keywords": ["medical", "health", "hsa", "diagnosis", "treatment", "hipaa", "phi", "patient"],
        "abuse_cases": [
            {"threat": "PHI Data Breach", "actor": "External Attacker", "description": "Mass exfiltration of protected health information.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "SQL injection, API abuse, insider theft", "stride_category": "Information Disclosure"},
            {"threat": "Medical Identity Theft", "actor": "External Attacker", "description": "Using stolen health information to obtain medical services.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "Data breach exploitation", "stride_category": "Spoofing"},
        ],
        "requirements": [
            {"text": "Deploy HIPAA Security Rule technical safeguards for PHI", "priority": "Critical", "category": "Regulatory Compliance", "details": "Access controls, audit controls, integrity controls per 45 CFR 164.312."},
            {"text": "Log all access to health records with full audit trail", "priority": "Critical", "category": "Audit Logging", "details": "Record who accessed what data, when, from where."},
            {"text": "Retain security logs for 6 years (HIPAA requirement)", "priority": "High", "category": "Audit Logging", "details": "Implement tiered storage. Ensure logs are immutable and searchable."},
        ],
    },
    "financial_data": {
        "keywords": ["investment", "portfolio", "financial", "retirement", "beneficiary", "account balance"],
        "abuse_cases": [
            {"threat": "Mass Data Exfiltration", "actor": "Malicious Insider", "description": "Authorized user exports large amounts of financial data.", "impact": "Critical", "likelihood": "Medium", "attack_vector": "Legitimate export functionality abuse", "stride_category": "Information Disclosure"},
        ],
        "requirements": [
            {"text": "Implement SOX IT controls with segregation of duties", "priority": "Critical", "category": "Regulatory Compliance", "details": "Separate dev, test, prod access. Change management controls."},
            {"text": "Configure GLBA Safeguards Rule controls", "priority": "High", "category": "Regulatory Compliance", "details": "Risk assessment, employee training, vendor management."},
            {"text": "Implement data loss prevention (DLP) at egress points", "priority": "High", "category": "Data Protection", "details": "Monitor and block sensitive data patterns in exports."},
        ],
    },
}

# Always-included baseline requirements
BASELINE_REQUIREMENTS = [
    {"text": "Enforce TLS 1.3 for all data in transit", "priority": "Critical", "category": "Data Protection", "details": "Disable TLS 1.0/1.1. Implement HSTS with 1-year max-age."},
    {"text": "Implement strict input validation whitelist on all user inputs", "priority": "Critical", "category": "Input Validation", "details": "Validate data type, length, format, and range."},
    {"text": "Use parameterized queries for all database operations", "priority": "Critical", "category": "Input Validation", "details": "Never concatenate user input into SQL."},
    {"text": "Log all authentication events with full context", "priority": "Critical", "category": "Audit Logging", "details": "Include timestamp, user ID, IP, user agent, geo-location."},
    {"text": "Implement tamper-evident logging with cryptographic chaining", "priority": "High", "category": "Audit Logging", "details": "Hash each log entry with previous entry hash."},
    {"text": "Deploy Content Security Policy (CSP) with strict-dynamic", "priority": "High", "category": "Input Validation", "details": "Disable unsafe-inline and unsafe-eval."},
    {"text": "Implement secrets management (e.g., Vault)", "priority": "Critical", "category": "Secure Architecture", "details": "Never store secrets in code or config files. Rotate automatically."},
    {"text": "Implement zero-trust network architecture", "priority": "High", "category": "Secure Architecture", "details": "Verify every access request. Least-privilege network access."},
]


def analyze_with_templates(title: str, description: str, acceptance_criteria: str | None = None) -> dict:
    text = f"{title} {description} {acceptance_criteria or ''}".lower()

    abuse_cases = []
    stride_threats = []
    requirements = []
    detected_categories = set()

    for pattern_name, pattern_data in PATTERNS.items():
        if any(kw in text for kw in pattern_data["keywords"]):
            detected_categories.add(pattern_name)
            for ac in pattern_data["abuse_cases"]:
                abuse_cases.append(ac)
            for req in pattern_data["requirements"]:
                requirements.append(req)

    # Add baseline
    requirements.extend(BASELINE_REQUIREMENTS)

    # Deduplicate by text
    seen_texts = set()
    unique_reqs = []
    for r in requirements:
        if r["text"] not in seen_texts:
            seen_texts.add(r["text"])
            unique_reqs.append(r)
    requirements = unique_reqs

    # Assign IDs
    for i, ac in enumerate(abuse_cases, 1):
        ac["id"] = _id("AC", i)
    for i, req in enumerate(requirements, 1):
        req["id"] = _id("SR", i)

    # Build STRIDE threats from abuse cases
    stride_categories = {}
    for ac in abuse_cases:
        cat = ac["stride_category"]
        if cat not in stride_categories:
            stride_categories[cat] = []
        stride_categories[cat].append(ac)

    for cat, cases in stride_categories.items():
        stride_threats.append({
            "category": cat,
            "threat": cases[0]["threat"],
            "description": f"{len(cases)} threat(s) identified in this category",
            "risk_level": cases[0]["impact"],
        })

    # Risk score
    critical = sum(1 for a in abuse_cases if a["impact"] == "Critical")
    high = sum(1 for a in abuse_cases if a["impact"] == "High")
    risk_score = min(100, critical * 12 + high * 6 + len(detected_categories) * 8)

    return {
        "abuse_cases": abuse_cases,
        "stride_threats": stride_threats,
        "security_requirements": requirements,
        "risk_score": risk_score,
    }
