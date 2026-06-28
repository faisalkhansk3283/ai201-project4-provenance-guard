import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"
DATABASE_FILE  = "provenance.db"
VALID_TIERS = {"likely_ai", "uncertain", "likely_human"}


# Confidence thresholds
HUMAN_THRESHOLD = 0.35    # below this = human
AI_THRESHOLD = 0.75       # above this = AI


# Signal weights
LLM_WEIGHT = 0.55
STYLO_WEIGHT = 0.35
INFORMAL_WEIGHT = 0.1