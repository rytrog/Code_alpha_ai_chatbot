"""
Scope Checker — rejects non-university questions before any AI call.
"""
import re
import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "university_keywords.json"

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _KEYWORDS: list[str] = [k.lower() for k in json.load(_f).get("keywords", [])]

# Core university context keywords (explicitly related to AITD Kanpur)
CORE_CONTEXT: set[str] = {
    "aaveg", "abdul", "abhishek", "abhiyan", "abilities", "abvrc", "academic", "academic calendar", 
    "academics", "accenture", "accepted", "accepts", "access", "accessibility", "accessible", "accommodates", 
    "accommodation", "according", "accreditation", "accuracy", "accurate", "achieved", "achievements", "act", 
    "acting", "active", "activities", "activity", "acts", "additional", "address", "addressed", 
    "administration", "administrative", "admission", "admissions", "admitted", "affairs", "affect", "affiliated", 
    "affiliations", "affordable", "agarwal", "aicte", "aimed", "aiml", "aims", "airport", 
    "aitd", "aith", "akn", "aktu", "align", "allocated", "almirah", "alpha", 
    "alumni", "ambedkar", "amenities", "analyst", "anchoring", "anil", "announcements", "annual", 
    "answer", "answers", "anti", "anti-ragging", "anuj", "appearing", "applicable", "applications", 
    "applied", "approval", "approved", "approximate", "aptean", "aptitude", "architecture", "architectures", 
    "area", "areas", "arrange", "arrangements", "arranges", "artificial", "artistic", "arts", 
    "ashutosh", "asia", "assignments", "assist", "assistance", "assistant", "assistantship", "assists", 
    "associate", "assurance", "asthana", "atal", "athletics", "atmosphere", "attendance", "attitude", 
    "attractiveness", "auditorium", "augmented", "authored", "authorities", "authority", "auto", "automated", 
    "automating", "available", "awadhesh", "awadhpuri", "awareness", "background", "backup", "badminton", 
    "balanced", "banking", "barrier", "barriers", "based", "basic", "basketball", "beauty", 
    "bed", "beds", "behavior", "belongings", "belongs", "benefit", "benefits", "beverages", 
    "bharat", "bihari", "biotech", "biotechnology", "block", "board", "boards", "bodies", 
    "book", "books", "boys", "branches", "breaks", "browse", "bsnl", "bte", 
    "btech", "build", "building", "buildings", "bus", "business", "butler", "cab", 
    "calendar", "cameras", "campus", "candidates", "canteen", "capabilities", "capacity", "carbon", 
    "card", "career", "careers", "carrom", "category", "caused", "cctv", "celebrations", 
    "cell", "cells", "center", "centered", "central", "centralized", "ceremony", "certificate", 
    "chair", "chairman", "chairs", "chandra", "channels", "charges", "chatbot", "chauraha", 
    "chemical", "chemistry", "chess", "chosen", "circular", "circulars", "class", "classroom", 
    "classrooms", "cleanliness", "clearance", "clinical", "closely", "closing", "club", "clubs", 
    "code", "coding", "collaboration", "collaborations", "collection", "college", "comfort", "comfortable", 
    "commitment", "committed", "committee", "committees", "common", "communication", "communications", "community", 
    "commuting", "companies", "company", "competence", "competencies", "competition", "competitions", "competitive", 
    "complaints", "complete", "completed", "components", "comprehensive", "compulsory", "computer", "computing", 
    "concepts", "concerns", "concessions", "conduct", "conducts", "conference", "conferences", "confident", 
    "confirmation", "confusing", "confusion", "connect", "connected", "connections", "connectivity", "connects", 
    "considerations", "consistency", "consistent", "consists", "consuming", "contact", "content", "continue", 
    "continuing", "continuous", "contribute", "contributed", "contributes", "contributions", "control", "convenience", 
    "convenient", "conversational", "convocation", "cooperation", "coordinate", "coordinated", "coordination", "coordinator", 
    "core", "council", "councils", "counseling", "counselling", "course", "courses", "create", 
    "created", "creative", "creativity", "credit", "cricket", "criteria", "cse", "cube", 
    "cuet", "cultural", "current", "curricular", "curriculum", "customer", "cycle", "daily", 
    "damage", "dance", "dancing", "date", "dduqip", "deadline", "dean", "debate", 
    "debit", "decades", "decision", "decisions", "decoration", "dedicated", "deeper", "degree", 
    "deliver", "delivers", "delivery", "demand", "demonstrates", "dental", "department", "departmental", 
    "departments", "dependency", "depends", "deposit", "derived", "design", "designated", "designation", 
    "designed", "designing", "destination", "details", "develop", "developed", "developer", "development", 
    "developments", "dharmendra", "dietary", "different", "digital", "dignity", "diploma", "direct", 
    "directions", "directly", "director", "directorship", "disabilities", "disability", "discipline", "disciplines", 
    "discussion", "discussions", "disruption", "dissertations", "distribution", "diverse", "diversity", "division", 
    "divyang", "divyangjan", "doctoral", "documents", "draft", "drama", "driven", "driver", 
    "drives", "duration", "dwivedi", "earned", "ease", "easily", "easy", "education", 
    "educational", "effective", "effectively", "efficiency", "efficient", "efficiently", "effort", "efforts", 
    "elastic", "elective", "electricity", "electronics", "eligibility", "email", "emerging", "employability", 
    "employable", "employers", "employment", "empowering", "empowerment", "enabled", "enables", "encourages", 
    "energiaa", "engagement", "engineer", "engineering", "english", "enhance", "enhanced", "enhancement", 
    "enhances", "enrollment", "enrolment", "ensure", "ensures", "entertainment", "entire", "entrance", 
    "entrepreneurial", "entrepreneurship", "entry", "environment", "environmental", "equal", "equipped", "essential", 
    "established", "establishment", "estimated", "ethical", "evaluation", "event", "events", "exam", 
    "examination", "examinations", "exams", "excellence", "exceptionally", "executive", "exhibition", "exit", 
    "expansion", "expectations", "expected", "experience", "experiments", "expert", "experts", "exposure", 
    "extracurricular", "facilitates", "facilities", "facility", "faculty", "failures", "familiar", "fashion", 
    "faster", "faults", "favor", "features", "featuring", "fee", "feel", "fees", 
    "fellow", "female", "fest", "festival", "festivals", "ffdc", "fiber", "final", 
    "finance", "financial", "fine", "fitness", "focus", "focused", "focuses", "follow", 
    "following", "follows", "food", "football", "form", "foundation", "founded", "fourth", 
    "fresher", "freshers", "friendly", "friendships", "fulfill", "fun", "functions", "funded", 
    "funding", "furnished", "future", "games", "gate", "gathering", "gatherings", "gaurav", 
    "general", "generated", "generation", "girl", "girls", "global", "goal", "goals", 
    "governance", "government", "governors", "governs", "graduation", "graphics", "green", "greenery", 
    "grievance", "grounds", "group", "grow", "growth", "guest", "guests", "guidance", 
    "guided", "guidelines", "gurudev", "gymnasium", "hackathon", "halls", "handicapped", "hands", 
    "harcourt", "hardworking", "hari", "hbti", "hbtu", "hcl", "head", "healthcare", 
    "healthy", "help", "helps", "highlights", "highly", "hindi", "hire", "history", 
    "hod", "holistic", "hostel", "hostels", "hosts", "hours", "houses", "human", 
    "humanity", "hygienic", "hysel", "identify", "iit", "important", "improve", "improved", 
    "improvement", "improvements", "improves", "improving", "incharge", "include", "included", "includes", 
    "including", "inclusion", "inclusive", "inclusiveness", "increase", "increases", "independence", "independent", 
    "india", "individual", "indoor", "indrakesh", "industrial", "industries", "industry", "informal", 
    "information", "informed", "infosys", "infotech", "infrastructure", "initiatives", "innovation", "innovative", 
    "innovators", "installation", "installed", "instant", "instantly", "institute", "institution", "institutional", 
    "institutions", "intake", "integrating", "integration", "intelligence", "intelligent", "interaction", "interactive", 
    "interface", "intermediate", "international", "internet", "internship", "internships", "interruptions", "interview", 
    "invite", "iqac", "issued", "jee", "jeecup", "jhakarkati", "job", "joined", 
    "joining", "joint", "journals", "jump", "kabaddi", "kalam", "kalyanpur", "kamani", 
    "kannauj", "kanpur", "kaushalendra", "key", "keywords", "kho", "knowledge", "kumar", 
    "kwp", "lab", "laboratories", "labs", "landmarks", "language", "late", "later", 
    "lateral", "latest", "leadership", "learn", "learning", "lecture", "lecturer", "lectures", 
    "led", "leisure", "library", "life", "limitations", "links", "literary", "live", 
    "living", "locate", "location", "locations", "long", "lucknow", "machine", "macleods", 
    "magazine", "mahindra", "main", "maintain", "maintained", "maintaining", "maintains", "maintenance", 
    "major", "male", "manage", "management", "manish", "manual", "manually", "map", 
    "march", "market", "materials", "mathematics", "matters", "meal", "meals", "measures", 
    "mechanisms", "medical", "meet", "meets", "member", "members", "memorandums", "mess", 
    "methods", "metro", "minimizes", "minor", "minutes", "mishra", "mission", "mobile", 
    "mobility", "modern", "modernization", "mom", "monitor", "monitoring", "mous", "movement", 
    "mrs", "mtech", "multilingual", "multiple", "music", "musical", "naac", "natak", 
    "nath", "national", "natural", "naturally", "nba", "near", "need", "needs", 
    "net", "network", "networking", "networks", "newly", "newsletter", "night", "nodal", 
    "non", "note", "notes", "notice", "notices", "notifications", "nss", "nukkad", 
    "nutritious", "objective", "objectives", "obtain", "offer", "offered", "offers", "office", 
    "offices", "official", "officials", "ola", "online", "open", "operational", "operations", 
    "opportunities", "opposite", "optic", "optical", "optimization", "optimum", "optimus", "options", 
    "ordinance", "organizations", "organize", "organized", "organizes", "oriented", "original", "originally", 
    "outdoor", "outside", "overall", "overcome", "overview", "owners", "pace", "package", 
    "paid", "papers", "parents", "parking", "participate", "participating", "participation", "partnered", 
    "parts", "party", "passed", "pathways", "pay", "payable", "payment", "pdfs", 
    "peaceful", "performance", "performances", "periods", "permanent", "personal", "personalities", "personality", 
    "personnel", "persons", "pharmaceutical", "pharmaceuticals", "philosophy", "phone", "photography", "physical", 
    "physics", "pkk", "place", "placement", "placements", "planning", "plant", "platform", 
    "play", "playground", "pleasant", "poetry", "point", "policies", "policy", "popular", 
    "positions", "positive", "possible", "posters", "potential", "power", "prabhakar", "practical", 
    "practice", "practices", "practo", "pradesh", "premises", "preparation", "prepare", "preparing", 
    "prescribed", "present", "presentations", "prestigious", "prevent", "primary", "principal", "principle", 
    "prize", "problem", "proceedings", "process", "processes", "production", "prof", "professional", 
    "professionals", "professor", "profile", "program", "programme", "programming", "programs", "prohibited", 
    "project", "projects", "promote", "promoted", "promotes", "promoting", "property", "proportion", 
    "protection", "provide", "provided", "provides", "providing", "public", "publications", "published", 
    "punishable", "purpose", "pursuing", "qualifications", "quality", "question", "questions", "quickly", 
    "quiet", "race", "rachna", "ragging", "railway", "rajesh", "rajput", "rama", 
    "ramps", "reach", "readiness", "ready", "real", "receive", "received", "recognition", 
    "recognized", "recommended", "records", "recreation", "recreational", "recruiter", "recruiters", "recruitment", 
    "reduce", "reduces", "reducing", "refer", "reference", "reflects", "refreshments", "refundable", 
    "regarding", "registrar", "registration", "regular", "regularly", "regulation", "regulations", "related", 
    "relationship", "relaxation", "relevant", "reliability", "reliable", "remaining", "renamed", "representative", 
    "reputed", "required", "requirement", "requirements", "research", "reservation", "reserved", "resident", 
    "residential", "residents", "resource", "resources", "respect", "respectful", "respective", "responses", 
    "responsible", "restoration", "result", "results", "retrieval", "revised", "rickshaw", "rickshaws", 
    "rights", "robotics", "rohit", "role", "roles", "rooms", "roorkee", "route", 
    "routes", "rubik", "rule", "rules", "rusa", "sac", "sachan", "safe", 
    "safety", "salary", "sankhnad", "satisfaction", "scattered", "schedule", "scheme", "scholars", 
    "scholarship", "scholarships", "school", "science", "scientific", "scores", "search", "searching", 
    "seat", "seating", "seats", "second", "secretarial", "section", "sectors", "secure", 
    "secured", "security", "seeking", "semester", "seminar", "seminars", "seniors", "separate", 
    "separately", "serve", "served", "serves", "service", "services", "serving", "sessions", 
    "seven", "shankhnaad", "sharma", "showcase", "showcases", "shree", "shree nath", "shukla", 
    "shweta", "signed", "significant", "significantly", "simple", "simplify", "singh", "singing", 
    "single", "skill", "skilled", "skills", "smart", "smooth", "snacks", "social", 
    "society", "soft", "software", "solar", "solve", "solves", "source", "sources", 
    "spaces", "spacious", "special", "specialized", "specializes", "specially", "specific", "specifically", 
    "sponsored", "sports", "sportsmanship", "sri", "sri nath", "srivastava", "staff", "stage", 
    "stakeholders", "standards", "startup", "startups", "statcon", "state", "statement", "station", 
    "stay", "step", "storage", "street", "strict", "strictly", "strong", "structure", 
    "structures", "student", "students", "studies", "study", "subjects", "submission", "succeed", 
    "success", "successful", "successfully", "sufi", "suitable", "supervise", "supervised", "supervising", 
    "supply", "support", "supported", "supportive", "supports", "surroundings", "surveillance", "survivability", 
    "survivable", "syllabus", "systems", "table", "tables", "tailored", "talent", "talents", 
    "talks", "taxi", "tcs", "teachers", "teaching", "team", "teamwork", "tech", 
    "technical", "technologies", "technology", "technozion", "television", "tennis", "teqip", "term", 
    "terminal", "terminology", "textbooks", "theoretical", "thesis", "thirty", "time table", "timetable", 
    "timing", "timings", "titled", "toilets", "total", "traditionally", "training", "transcript", 
    "transformation", "transition", "transparency", "transport", "transportation", "travel", "trends", "tripathi", 
    "tuition", "uba", "uber", "ucertify", "ugc", "unauthorized", "understand", "understanding", 
    "uninterrupted", "unique", "universal", "university", "unnat", "upadhyay", "updated", "updates", 
    "upi", "uptu", "user", "users", "ust", "uttar", "vajpayee", "value", 
    "values", "vary", "vehicle", "vehicles", "venue", "venues", "video", "vishakhdutt", 
    "vishal", "vision", "visitor", "visitors", "visits", "viva", "vocational", "volleyball", 
    "waiting", "warden", "water", "web", "webpages", "website", "welcome", "welfare", 
    "wheelchair", "wing", "wipro", "work", "worked", "workload", "workplace", "works", 
    "workshop", "workshops", "world", "xlayer", "yes", 
}

# Bot capability and conversational context pronouns
BOT_CONTEXT: set[str] = {
    "you", "your", "me", "i", "we", "chatbot", "bot", "assistant",
    "creator", "developer", "developers", "engineered"
}

# Allowed combinations for bot queries
SAFE_BOT_COMBINATIONS: set[str] = {
    "located", "situated", "where", "address", "contact", "phone", "email",
    "name", "who", "help", "capability", "capabilities", "do you", "can you",
    "about you", "who is this"
}

# Explicit rejection phrases for common off-topic domains
_BLOCKED_PATTERNS: list[str] = [
    # General off-topic subjects
    "capital of", "president of", "prime minister", "who won",
    "recipe for", "movie", "song", "cricket", "football", "ipl",
    "messi", "ronaldo", "politics", "religion", "god",
    "boyfriend", "girlfriend", "dating", "love advice", "love story",
    "weather", "forecast", "climate", "temperature",
    # External personalities
    "trump", "biden", "obama", "modi", "gandhi", "nehru", "putin",
    "elon musk", "bill gates", "steve jobs", "mark zuckerberg",
    # Coding general queries
    "write code", "write python", "write java", "write program", "programming tutorial",
    "code to", "how to write a program", "write a code", "write a python",
    # External organizations / companies
    "google", "microsoft", "apple", "amazon", "facebook", "netflix", "tesla",
    # Other universities
    "hbtu", "iet", "knit", "iit", "nit", "mit", "harvard", "stanford", "oxford",
    # General non-college locations/countries
    "america", "usa", "united states", "uk", "london", "paris", "washington", "new york", "australia", "iran", "china", "pakistan"
]

# Compile with word boundaries to avoid false positives (e.g. "ipl" in "diploma" or "god" in "pagoda")
_BLOCKED_REGEXES: list[re.Pattern] = [
    re.compile(r'\b' + re.escape(pattern) + r'\b', re.IGNORECASE)
    for pattern in _BLOCKED_PATTERNS
]

# Simple greetings, thanks, acknowledgements, and goodbyes
_ALLOWED_CONVERSATIONAL_EXACT: set[str] = {
    # Greetings
    "hy", "bot", "hi bot", "hello", "hi", "hi there", "hey", "greetings",
    "good morning", "good afternoon", "good evening", "good night", "morning",
    "evening", "afternoon", "night", "howdy", "hola", "namaste", "hii", "helloo",
    "hiii", "yo", "sup", "how are you", "hi buddy", "hi friend", "hi bro",
    "hi man", "hlo", "hello everyone", "greet", "hi all", "hi everyone",
    # Thanks
    "thanks", "thank you", "thankyou", "ty", "tysm", "thank", "thanks a lot",
    "thanks so much", "thank u", "thx", "many thanks", "thanks!", "thank you!",
    "thanks.", "grateful", "appreciate it", "you are great", "you are awesome",
    "you are nice", "you are amazing", "thankful", "great job", "good job",
    "great work", "good work", "thanks for help", "thanks for helping",
    # Acknowledgements / Confirmations
    "ok", "okay", "okey", "k", "kk", "kay", "got it", "gotcha", "understood",
    "i understand", "makes sense", "that makes sense", "clear", "all clear",
    "crystal clear", "noted", "duly noted", "noted thanks", "sure", "sure!",
    "absolutely", "certainly", "fine", "alright", "all right", "right", "cool",
    "cool!", "cool thanks", "nice", "nice!", "great", "great!", "awesome",
    "awesome!", "perfect", "perfect!", "excellent", "fantastic", "wonderful",
    "okay thanks", "ok thanks", "thanks got it", "got it thanks", "understood thanks",
    "sounds good", "looks good", "good", "good enough", "fair enough", "roger",
    "roger that", "copy that", "works", "that works", "it works", "works for me",
    "yep", "yeah", "yup", "yupp", "indeed", "exactly", "thank you got it",
    "okay understood", "okay noted", "done", "done thanks", "wow", "wow!",
    "woah", "woah!", "yay", "yay!", "super", "superb", "oh ok", "oh okay",
    "ah ok", "ah okay", "oh", "ohh", "ahh", "okay clear", "ok clear", "ah",
    "whoa", "whoa!", "goodnight", "noon", "goodnoon",
    # Goodbyes
    "bye", "goodbye", "bye bye", "see you", "see ya", "see you later",
    "take care", "exit", "quit", "bye!", "goodbye!", "see you!", "cya",
    "byebye", "adios"
}

_IDENTITY_QUERIES: set[str] = {
    "who are you", "what is your name", "what are you", "tell me about yourself",
    "who is this", "your identity"
}

_DEV_QUERIES: set[str] = {
    "who made you", "who developed you", "who created you", "who is the developer",
    "who are the developers", "developer team", "developers", "creator",
    "who is your creator", "creators", "origin of this chatbot", "origin of the chatbot",
    "origin", "your origin", "who handles you", "who designed you",
    "who engineered you", "designed by", "engineered by", "credits",
    "project head", "project supervisor", "who is the creator", "who built you",
    "who programmed you", "who make you"
}

OUT_OF_SCOPE_REPLY = (
    "Sorry, I can only answer queries related to AITD, Kanpur. "
    "Please ask questions about admissions, fees, courses, placements, "
    "hostel, faculty, departments, or other AITD-related matters."
)


def is_in_scope(message: str) -> bool:
    """
    Return True if the message should be processed by the chatbot.
    """
    msg = message.lower().strip()

    # 1. Quick reject for obviously off-topic queries (using word boundaries)
    for rx in _BLOCKED_REGEXES:
        if rx.search(msg):
            return False

    # 2. Check if the message is a simple greeting or thanks
    clean_msg = re.sub(r'[^\w\s]', '', msg).strip()
    if clean_msg in _ALLOWED_CONVERSATIONAL_EXACT:
        return True

    # Check for prefix greeting/thanks roots (e.g. "thanks bro", "hello sir")
    _ALLOWED_GREETING_ROOTS = {
        "hi", "hello", "hey", "hy", "thanks", "thank", "ty", "tysm", "thx",
        "good morning", "good afternoon", "good evening", "good night", "morning",
        "evening", "afternoon", "night", "hola", "namaste", "hlo", "yo", "sup",
        "bye", "goodbye", "ok", "okay", "roger"
    }
    if any(clean_msg.startswith(root + " ") for root in _ALLOWED_GREETING_ROOTS):
        return True

    # 3. Check for specific bot/developer identity queries
    if clean_msg in _IDENTITY_QUERIES or clean_msg in _DEV_QUERIES:
        return True

    # 4. Strict Context Matching
    # Verify if query contains at least one CORE_CONTEXT keyword as a standalone word
    has_core = False
    for kw in CORE_CONTEXT:
        if re.search(r'\b' + re.escape(kw) + r'\b', msg):
            has_core = True
            break

    if has_core:
        return True

    # 5. Safe Bot Context Matching
    # Check if query contains a BOT_CONTEXT word combined with a SAFE_BOT_COMBINATIONS keyword
    has_bot = False
    for kw in BOT_CONTEXT:
        if re.search(r'\b' + re.escape(kw) + r'\b', msg):
            has_bot = True
            break

    if has_bot:
        has_safe_combo = False
        for combo in SAFE_BOT_COMBINATIONS:
            if re.search(r'\b' + re.escape(combo) + r'\b', msg):
                has_safe_combo = True
                break
        if has_safe_combo:
            return True

    return False

