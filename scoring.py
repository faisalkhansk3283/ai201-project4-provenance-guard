from config import LLM_WEIGHT, STYLO_WEIGHT, INFORMAL_WEIGHT, HUMAN_THRESHOLD, AI_THRESHOLD

def combine_signals(llm_score: float, stylometric_score: float, informality_score: float) -> float:
    confidence = (llm_score * LLM_WEIGHT) + (stylometric_score * STYLO_WEIGHT) + (informality_score * INFORMAL_WEIGHT)
    return round(confidence, 3)

def get_attribution(confidence: float) -> str:
    if confidence <= HUMAN_THRESHOLD:
        return "likely_human"
    elif confidence >= AI_THRESHOLD:
        return "likely_ai"
    else:
        return "uncertain"
    
def generate_label(attribution: str, confidence: float) -> str:
    score = round(confidence * 100)
    
    if attribution == "likely_ai":
        return f"⚠️ AI Generated\nThis content shows strong patterns of AI generation (confidence: {score}%).\nThis is automated analysis — the creator may appeal this classification."

    elif attribution == "likely_human":
        return f"✅ Human Written\nThis content shows strong patterns of human authorship (confidence: {score}% human)."

    else:
        return f"❓ Uncertain\nOur system could not confidently determine authorship (confidence: {score}%).\nThe creator may appeal this classification."