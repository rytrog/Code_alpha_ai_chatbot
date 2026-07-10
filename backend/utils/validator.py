"""
Input Validator — sanitises user messages and validates file uploads.
"""
import re
from config import settings

# ── Jailbreak & Prompt Injection Patterns ──
_JAILBREAK_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "forget previous instructions",
    "disregard previous instructions",
    "override system prompt",
    "system override",
    "new instructions",
    "act as",
    "pretend to be",
    "roleplay as",
    "you are now",
    "developer mode",
    "god mode",
    "jailbreak",
    "bypass restrictions",
    "disable safety",
    "remove restrictions",
    "ignore safety policies",
    "reveal hidden instructions",
    "show system prompt",
    "print system prompt",
    "repeat your instructions",
    "what are your instructions",
    "display internal prompt",
    "reveal hidden rules",
    "show hidden prompt",
    "show developer message"
]

# ── Malicious Keywords ──
_MALICIOUS_KEYWORDS = [
    "exploit",
    "bypass",
    "ddos",
    "malware",
    "ransomware",
    "keylogger",
    "trojan",
    "virus",
    "payload",
    "reverse shell",
    "shellcode",
    "sql injection",
    "xss",
    "csrf",
    "privilege escalation",
    "bruteforce",
    "credential stuffing",
    "session hijacking",
    "phishing",
    "spoofing",
    "botnet",
    "rootkit",
    "backdoor"
]

# ── Off-topic Coding Patterns ──
_OFF_TOPIC_CODING = [
    "write python code",
    "write a script",
    "generate code",
    "create a program",
    "build a bot",
    "make a website",
    "write javascript",
    "write java code",
    "write c++ code",
    "write a hacking script",
    "develop an application",
    "implement this algorithm"
]

# ── System Disclosure Patterns ──
_SYSTEM_DISCLOSURE = [
    "show database schema",
    "show api keys",
    "show secrets",
    "show credentials",
    "show tokens",
    "show environment variables",
    "show internal configuration",
    "show backend architecture",
    "show source code",
    "show server configuration",
    "show deployment details"
]


def validate_message(text: str) -> tuple[bool, str]:
    """
    Validate a chat message against security guardrails.
    Returns (is_valid, error_message).
    """
    if not text or not text.strip():
        return False, "Message cannot be empty."

    text = text.strip()
    msg_lower = text.lower()

    if len(text) > settings.MAX_MESSAGE_LENGTH:
        return False, f"Message exceeds {settings.MAX_MESSAGE_LENGTH} characters."

    # 1. Block HTML / script injection
    if re.search(r"<\s*script", text, re.IGNORECASE):
        return False, "Invalid input detected."

    # 2. Block SQL injection patterns
    sql_patterns = [
        r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s",
        r"('|\")\s*(OR|AND)\s*('|\")\s*=\s*('|\")",
        r"UNION\s+SELECT",
    ]
    for pattern in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Invalid input detected."

    # Generate normalized variations for security checks to catch obfuscation bypasses
    import unicodedata
    norm_text = unicodedata.normalize("NFKD", msg_lower)
    
    var_spaced_list = []
    var_stripped_list = []
    strip_chars = {'*', '_', '`', "'", '"', '\u200b', '\u200c', '\u200d', '\ufeff'}
    
    for c in norm_text:
        if c.isalnum() or c.isspace():
            var_spaced_list.append(c)
            var_stripped_list.append(c)
        elif c in strip_chars:
            var_spaced_list.append(" ")
            # skipped in stripped variation
        else:
            var_spaced_list.append(" ")
            var_stripped_list.append(" ")
            
    var_spaced = " ".join("".join(var_spaced_list).split())
    var_stripped = " ".join("".join(var_stripped_list).split())
    
    variations = {msg_lower, var_spaced, var_stripped}

    # 3. Guardrail: Block Jailbreak / Prompt Injection attempts
    for pat in _JAILBREAK_PATTERNS:
        for var in variations:
            if pat in var:
                return False, "Security check failed: Request contains instruction override patterns."

    # 4. Guardrail: Block Malicious hacking keywords
    for kw in _MALICIOUS_KEYWORDS:
        for var in variations:
            if kw in var:
                return False, "Invalid input detected: Security keywords blocked."

    # 5. Guardrail: Block obvious off-topic coding requests
    for pat in _OFF_TOPIC_CODING:
        for var in variations:
            if pat in var:
                return False, "Sorry, I can only answer queries related to AITD, Kanpur."

    # 6. Guardrail: Block System Disclosure queries
    for pat in _SYSTEM_DISCLOSURE:
        for var in variations:
            if pat in var:
                return False, "Security check failed: Unauthorized system disclosure request."

    return True, ""


def validate_file(filename: str, file_size_bytes: int) -> tuple[bool, str]:
    """
    Validate an uploaded file by extension and size.
    Returns (is_valid, error_message).
    """
    if not filename:
        return False, "No filename provided."

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
        return False, f"File type '.{ext}' not allowed. Accepted: {allowed}."

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        return False, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit."

    return True, ""
