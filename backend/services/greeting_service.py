"""
Greeting Service — instant responses for greetings (no AI call).
Loaded once at module level for <50 ms response time.
"""
import difflib
import json
import random
import re
import time
from pathlib import Path

# ── Load greetings data once ──
_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "greetings.json"

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _GREETINGS_DATA = json.load(_f)

_GREETING_WORDS = [g.lower() for g in _GREETINGS_DATA.get("greetings", [])]
_RESPONSES = _GREETINGS_DATA.get("responses", [
    "Hello! Welcome to the University Assistant. How can I help you today?"
])

# Standard greeting/appellation filler words allowed in a pure greeting
_ALLOWED_GREETING_WORDS = {
    "bot", "assistant", "there", "everyone", "all", "buddy", "friend", "bro", "man",
    "u", "you", "to", "the", "a", "an", "am", "i", "is", "are", "good", "morning",
    "afternoon", "evening", "night", "day", "again", "back", "still", "busy", "here",
    "ready", "how", "are", "you", "wow", "wow!", "woah", "woah!", "yay", "yay!", "super", "superb",
    "oh ok", "oh okay", "ah ok", "ah okay", "oh", "ohh", "ahh",
    "okay clear", "ok clear", "ah", "whoa", "whoa!", "goodnight", "noon", "goodnoon"
}
# Dynamically add all words from greetings.json list
for _g in _GREETING_WORDS:
    for _word in _g.split():
        _ALLOWED_GREETING_WORDS.add(_word)

# Fuzzy matching set (only single word greetings from settings)
_SINGLE_WORD_GREETINGS = {w for w in _GREETING_WORDS if " " not in w}

# Store greeting state: {session_id: {"consecutive_count": int, "last_response": str, "last_time": float}}
_session_greeting_states = {}

_GENTLE_SECOND_RESPONSES = [
    "Hello again! 😊 Great to see you back. What else can I assist you with today?",
    "Hi there! Back so soon? Let me know how I can help you now.",
    "Hey! Good to hear from you again. Feel free to ask any questions about AITD Kanpur.",
    "Hello again! I'm still here and ready to guide you. What's on your mind?",
    "Greetings again! Always happy to assist you. What would you like to explore next?"
]

_GENTLE_THIRD_RESPONSES = [
    "Hi! Still greeting? I'm always happy to say hello, but feel free to dive right into any questions you have about courses, admissions, or placements! 🎓",
    "Hello! I appreciate the warm welcome, but please don't hesitate to ask whatever you're looking for at AITD Kanpur. 😊",
    "Hey there! Ready to help you with anything you need. What specific information can I find for you?",
    "Hi! If you have any queries about fees, department details, or campus facilities, just type them in. I'm all ears!"
]

_GENTLE_MANY_RESPONSES = [
    "Haha, looks like we are in a greeting loop! 🔄 Let's get down to business — ask me anything about AITD Kanpur and I'll do my best to help you.",
    "Still here! Ready for your questions whenever you are. 🚀 Just type in what you'd like to know about the college.",
    "Hello! I'm here and fully prepared to assist. What can I do for you today? 😊",
    "Always happy to chat, but let's see how I can help you with your college queries! Ask away."
]

def _cleanup_old_sessions():
    now = time.time()
    # Remove sessions older than 30 minutes (1800 seconds)
    to_delete = [
        sid for sid, state in _session_greeting_states.items()
        if now - state.get("last_time", 0) > 1800
    ]
    for sid in to_delete:
        _session_greeting_states.pop(sid, None)

def _reset_consecutive(state):
    if state:
        state["consecutive_count"] = 0

def _get_random_response(responses, last_response=None):
    if len(responses) > 1 and last_response:
        available = [r for r in responses if r != last_response]
        if available:
            return random.choice(available)
    return random.choice(responses)


def _handle_time_greeting(clean_msg: str) -> str | None:
    """
    Detect if query is a time-specific greeting (morning, afternoon, evening, night).
    Returns a time-accurate response or a friendly, gently funny correction.
    """
    time_categories = {
        "morning": ["good morning", "morning"],
        "afternoon": ["good afternoon", "afternoon", "good noon", "noon"],
        "evening": ["good evening", "evening"],
        "night": ["good night", "goodnight", "night"]
    }

    detected_cat = None
    matched_phrase = None
    for cat, phrases in time_categories.items():
        for phrase in phrases:
            if clean_msg == phrase or clean_msg.startswith(phrase + " ") or clean_msg.startswith(phrase + "!") or clean_msg.startswith(phrase + ","):
                # Ensure no substantive content exists in the query remainder
                rest = clean_msg[len(phrase):].strip()
                rest_clean = re.sub(r"[^a-z0-9\s]", "", rest)
                rest_words = rest_clean.split()
                if not rest_words or all(w in _ALLOWED_GREETING_WORDS for w in rest_words):
                    detected_cat = cat
                    matched_phrase = phrase
                    break
        if detected_cat:
            break

    if not detected_cat:
        return None

    # Determine actual time slot of the server
    from datetime import datetime
    hour = datetime.now().hour

    if 5 <= hour < 12:
        actual_cat = "morning"
        actual_reply = "Good morning! ☀️"
    elif 12 <= hour < 17:
        actual_cat = "afternoon"
        actual_reply = "Good afternoon! 😊"
    elif 17 <= hour < 21:
        actual_cat = "evening"
        actual_reply = "Good evening! 🌇"
    else:
        actual_cat = "night"
        actual_reply = "Good night! 🌙"

    # If the user says good night or goodnight, and the actual time is night, wish them sweet dreams directly and exit early.
    # We do not want to ask them "How can I help you today?" as they are going to bed.
    if detected_cat == "night" and actual_cat == "night":
        return random.choice([
            "Good night! Sleep tight and sweet dreams! 🌙",
            "Good night! Wishing you a peaceful sleep and sweet dreams. 🌙",
            "Good night! Sleep tight, sweet dreams! 😴✨",
            "Good night! Rest well and sweet dreams! 🌙",
            "Good night! Have a peaceful sleep and sweet dreams! 🌙"
        ])

    if detected_cat == actual_cat:
        return f"{actual_reply} How can I help you today? 🎓"
    else:
        # User greeted with the wrong time of day: return a gently funny, conversational correction
        if actual_cat == "morning":
            if detected_cat in ("afternoon", "evening", "night"):
                return "Really!😂 It's actually morning here ☀️, but good morning! Skipping straight to the end of the day? 😄So,how can I help you today?"
            else:
                return "It's actually morning here ☀️, but good morning! How can I help you today?"
        elif actual_cat == "afternoon":
            if detected_cat in ("morning", "evening", "night"):
                return "It's actually afternoon here 😊, but good afternoon! Did your morning coffee kick in a bit late? 😄 How can I help you?"
            else:
                return "It's actually afternoon here 😊, but good afternoon! How can I help you?"
        elif actual_cat == "evening":
            if detected_cat in ("morning", "afternoon", "night"):
                return "It's actually evening here 🌇, but good evening! Are you living in a different time zone or just testing my clock? 😉 How can I help you?"
            else:
                return "It's actually evening here 🌇, but good evening! How can I help you?"
        else:  # night
            if detected_cat in ("morning", "afternoon"):
                return "It's actually night here 🌙, but good evening! Did you just wake up from a very long nap? 😄 How can I help you?"
            else:
                return "Good evening! 🌇 How can I help you today? 🎓"


def check_greeting(message: str, session_id: str | None = None) -> str | None:
    """
    Return a random greeting response if *message* is a greeting,
    otherwise return None.  No AI call is made.
    """
    msg = message.lower().strip()
    
    # Strip basic trailing punctuation for exact comparison
    clean_msg = msg.rstrip("?!.,;:")

    # Get session state first if session_id is provided, to reset consecutively if needed
    if session_id:
        _cleanup_old_sessions()
        if session_id not in _session_greeting_states:
            _session_greeting_states[session_id] = {
                "consecutive_count": 0,
                "last_response": None,
                "last_time": 0.0
            }
        state = _session_greeting_states[session_id]
        state["last_time"] = time.time()
    else:
        state = None

    # ── Time-Aware Smart Greeting Matcher ──
    time_reply = _handle_time_greeting(clean_msg)
    if time_reply:
        if state:
            _reset_consecutive(state)
        return time_reply

    # Check for thanks / appreciation
    thanks_words = {
        "thanks", "thank you", "thankyou", "ty", "tysm", "thank", "thanks a lot", "thanks so much", "thank u",
        "thx", "many thanks", "thanks!", "thank you!", "thanks.", "grateful", "appreciate it", "you are great",
        "you are awesome", "you are nice", "you are amazing", "thankful", "great job", "good job", "great work",
        "good work", "thanks for help", "thanks for helping", "thanks for guidance", "thanks for guiding",
        "thanks for the information", "thanks for providing the information", "thanks for providing the answer",
        "thanks for giving answer", "thanks for the help", "thanks for the guidance", "thanks for the answer"
    }
    if clean_msg in thanks_words:
        _reset_consecutive(state)
        return random.choice([
            "You're welcome! 😊 Happy to help. Feel free to ask me anything about AITD Kanpur.",
            "Anytime! 🚀 That's what I'm here for.",
            "Glad I could help! Let me know if you need anything else.",
            "You're most welcome! 🎓 Wishing you a great day at AITD Kanpur.",
            "No worries! I'm always ready for the next question. 😎",
            "Happy to help! If curiosity strikes again, you know where to find me. 🤖",
            "My pleasure! Feel free to explore more information about AITD Kanpur.",
            "You're welcome! 🌟 Thanks for visiting the AITD Kanpur AI Assistant.",
            "Mission accomplished! ✅ What's next on your mind?",
            "Glad I could be useful today. 😊",
            "You're welcome! Hope I saved you a few clicks. 😄",
            "AI Assistant: 1 | Confusion: 0 😎",
            "Always happy to help! 🚀",
            "You're welcome! Have an amazing day ahead.",
            "Consider me your digital campus guide. 🎓✨",
            "No problem at all! Ask away if you need anything else.",
            "You're welcome! May your assignments be short and your grades be high. 😆",
            "Happy to help! 🤝",
            "You're welcome! Don't hesitate to come back with more questions.",
            "Achievement Unlocked: Information Received 🏆😄"
        ])

    # Check for acknowledgments / confirmation / reactions
    ack_words = {
        "ok", "okay", "okey", "k", "kk", "kay",
        "got it", "gotcha", "understood", "i understand",
        "makes sense", "that makes sense", "clear",
        "all clear", "crystal clear",
        "noted", "duly noted", "noted thanks",
        "sure", "sure!", "absolutely", "certainly",
        "fine", "alright", "all right", "right",
        "cool", "cool!", "cool thanks",
        "nice", "nice!", "great", "great!",
        "awesome", "awesome!", "perfect", "perfect!",
        "excellent", "fantastic", "wonderful",
        "okay thanks", "ok thanks", "thanks got it",
        "got it thanks", "understood thanks",
        "sounds good", "looks good", "good",
        "good enough", "fair enough",
        "roger", "roger that", "copy that",
        "works", "that works", "it works",
        "works for me",
        "yep", "yeah", "yup", "yupp",
        "indeed", "exactly",
        "thank you got it",
        "okay understood",
        "okay noted",
        "done",
        "done thanks",
        "wow", "wow!", "woah", "woah!", "yay", "yay!", "super", "superb",
        "oh ok", "oh okay", "ah ok", "ah okay", "oh", "ohh", "ahh",
        "okay clear", "ok clear", "ah", "whoa", "whoa!"
    }
    if clean_msg in ack_words:
        _reset_consecutive(state)
        return random.choice([
            "Perfect! Let me know if there's anything else you'd like to know.",
            "Great! I'm here whenever you need more information.",
            "Awesome! Feel free to ask another question anytime.",
            "Glad that helped! 😊",
            "Sounds good! What would you like to know next?",
            "Got it 👍 I'm here if you need anything else.",
            "Happy to help! Feel free to continue exploring.",
            "Excellent! Let me know if another question comes up.",
            "Wonderful! I'm ready whenever you are.",
            "Great! 🚀 What can I help you with next?",
            "All set then! Feel free to ask about admissions, courses, placements, or campus facilities.",
            "Nice! Let me know if you'd like more details on anything.",
            "Glad we're on the same page! 😄",
            "Perfect! Your AI assistant is standing by. 🤖",
            "Awesome! Ready for the next question whenever you are.",
            "Sounds good! Thanks for using the chatbot.",
            "Cool! 😎 What would you like to explore next?",
            "Great! Hope that cleared things up.",
            "Roger that! 🚀",
            "Mission understood. Awaiting your next question. 🤖"
        ])

    # Check for goodbyes / chat end
    goodbye_words = {
        "bye", "goodbye", "bye bye", "see you", "see ya", "see you later", "take care", "goodnight", "good night",
        "exit", "quit", "bye!", "goodbye!", "see you!", "cya", "byebye", "adios"
    }
    if clean_msg in goodbye_words:
        _reset_consecutive(state)
        return random.choice([
            "Goodbye! Have a wonderful day ahead. 😊",
            "Bye! Feel free to chat again if you have more questions about AITD Kanpur.",
            "Take care! Hope to help you again soon. 👋",
            "Goodbye! Wishing you all the best in your studies. 🎓",
            "Bye for now! Let me know if you need anything else later."
        ])

    # Check if the entire message is a greeting or starts with one
    is_greeting = False
    for word in _GREETING_WORDS:
        if clean_msg == word:
            is_greeting = True
            break
        elif clean_msg.startswith(word + " ") or clean_msg.startswith(word + "!") or clean_msg.startswith(word + ","):
            # Ensure the rest of the message has no substantive content
            rest = clean_msg[len(word):].strip()
            rest_clean = re.sub(r"[^a-z0-9\s]", "", rest)
            rest_words = rest_clean.split()
            if not rest_words or all(w in _ALLOWED_GREETING_WORDS for w in rest_words):
                is_greeting = True
                break

    # Fuzzy match fallback for spelling mistakes in greetings
    if not is_greeting:
        words_in_msg = clean_msg.split()
        if words_in_msg:
            first_word = words_in_msg[0]
            # Fuzzy match first word to single-word greetings
            matches = difflib.get_close_matches(first_word, list(_SINGLE_WORD_GREETINGS), n=1, cutoff=0.8)
            if matches:
                matched_word = matches[0]
                rest_words = words_in_msg[1:]
                # Clean punctuation from rest words to match in _ALLOWED_GREETING_WORDS
                clean_rest_words = [re.sub(r"[^a-z0-9]", "", w) for w in rest_words]
                if not clean_rest_words or all(w in _ALLOWED_GREETING_WORDS for w in clean_rest_words):
                    is_greeting = True

    if is_greeting:
        if state:
            state["consecutive_count"] += 1
            count = state["consecutive_count"]
        else:
            count = 1

        # Select response based on count
        if count == 1:
            last_resp = state["last_response"] if state else None
            response = _get_random_response(_RESPONSES, last_resp)
        elif count == 2:
            response = random.choice(_GENTLE_SECOND_RESPONSES)
        elif count == 3:
            response = random.choice(_GENTLE_THIRD_RESPONSES)
        else:
            response = random.choice(_GENTLE_MANY_RESPONSES)

        if state:
            state["last_response"] = response

        return response

    _reset_consecutive(state)
    return None


