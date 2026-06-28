def generate_label(attribution: str, confidence: float) -> str:
    score = round(confidence * 100)
    
    if attribution == "likely_ai":
        return f"⚠️ AI Generated\nThis content shows strong patterns of AI generation (confidence: {score}%).\nThis is automated analysis — the creator may appeal this classification."
    elif attribution == "likely_human":
        return f"✅ Human Written\nThis content shows strong patterns of human authorship (confidence: {score}% human)."
    else:
        return f"❓ Uncertain\nOur system could not confidently determine authorship (confidence: {score}%).\nThe creator may appeal this classification."