from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import uuid

from config import *
from database import init_db, save_submission, save_appeal, get_log
from signals import get_llm_score, get_stylometric_score, get_informality_score
from scoring import combine_signals, get_attribution
from labels import generate_label

from database import init_db, save_submission, save_appeal, get_log, verify_creator, is_verified    

load_dotenv()

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute; 100 per day")
def submit():
    data = request.get_json()
    text = data.get("text", "")
    creator_id = data.get("creator_id", "")

    if not text or not creator_id:
        return jsonify({"error": "text and creator_id required"}), 400

    content_id = str(uuid.uuid4())
    verified = is_verified(creator_id)

    llm_score = get_llm_score(text)
    stylometric_score = get_stylometric_score(text)
    informality_score = get_informality_score(text)

    confidence = combine_signals(llm_score, stylometric_score, informality_score)
    attribution = get_attribution(confidence)
    label = generate_label(attribution, confidence)

    save_submission(content_id, creator_id, text, attribution,
                    confidence, llm_score, stylometric_score,
                    informality_score, label)

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signals": {
            "llm_score": llm_score,
            "stylometric_score": stylometric_score,
            "informality_score": informality_score
        },
        "status": "classified",
        "verified_creator": verified,
        "badge": "✅ Verified Human Creator" if verified else None
    })


@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json()
    content_id = data.get("content_id", "")
    creator_reasoning = data.get("creator_reasoning", "")

    if not content_id or not creator_reasoning:
        return jsonify({"error": "content_id and creator_reasoning required"}), 400

    save_appeal(content_id, creator_reasoning)

    return jsonify({
        "message": "Appeal received. Your submission is now under review.",
        "content_id": content_id,
        "status": "under_review"
    })


@app.route("/log", methods=["GET"])
def log():
    entries = get_log()
    return jsonify({"entries": entries})


@app.route("/status/<content_id>", methods=["GET"])
def status(content_id):
    entries = get_log()
    for entry in entries:
        if entry["content_id"] == content_id:
            return jsonify(entry)
    return jsonify({"error": "content_id not found"}), 404


@app.route("/analytics", methods=["GET"])
def analytics():
    entries = get_log(limit=1000)
    
    total = len(entries)
    distribution = {"likely_ai": 0, "uncertain": 0, "likely_human": 0}
    appeal_count = 0
    
    for entry in entries:
        distribution[entry["attribution"]] += 1
        if entry["appeal_reasoning"]:
            appeal_count += 1
    
    avg_confidence = round(
        sum(e["confidence"] for e in entries) / total, 3
    ) if total > 0 else 0
    
    return jsonify({
        "total_submissions": total,
        "attribution_distribution": distribution,
        "appeal_rate": round(appeal_count / total, 3) if total > 0 else 0,
        "average_confidence": avg_confidence
    })


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json()
    creator_id = data.get("creator_id", "")
    statement = data.get("statement", "")

    if not creator_id or not statement:
        return jsonify({"error": "creator_id and statement required"}), 400

    verify_creator(creator_id, statement)

    return jsonify({
        "message": "Creator verified successfully.",
        "creator_id": creator_id,
        "badge": "✅ Verified Human Creator"
    })




if __name__ == "__main__":
    init_db()
    app.run(debug=True)
