import sqlite3
import os
from datetime import datetime
from config import DATABASE_FILE

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            content_id TEXT PRIMARY KEY,
            creator_id TEXT,
            text TEXT,
            attribution TEXT,
            confidence REAL,
            llm_score REAL,
            stylometric_score REAL,
            informality_score REAL,
            label TEXT,
            status TEXT DEFAULT 'classified',
            appeal_reasoning TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_creators (
            creator_id TEXT PRIMARY KEY,
            verified_at TEXT,
            statement TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_submission(content_id, creator_id, text, attribution, 
                    confidence, llm_score, stylometric_score, 
                    informality_score, label):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO submissions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        content_id,
        creator_id,
        text,
        attribution,
        confidence,
        llm_score,
        stylometric_score,
        informality_score,
        label,
        "classified",
        None,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def save_appeal(content_id, creator_reasoning):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE submissions 
        SET status = ?, appeal_reasoning = ?
        WHERE content_id = ?
    """, ("under_review", creator_reasoning, content_id))
    conn.commit()
    conn.close()

def get_log(limit=20):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def verify_creator(creator_id, statement):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO verified_creators VALUES (?, ?, ?)",
        (creator_id, datetime.now().isoformat(), statement)
    )
    conn.commit()
    conn.close()

def is_verified(creator_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT creator_id FROM verified_creators WHERE creator_id = ?",
        (creator_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None