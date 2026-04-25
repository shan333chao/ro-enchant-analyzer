"""SQLite 数据库操作"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "enchantment.db")


def get_db():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS attribute_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attribute_name TEXT NOT NULL UNIQUE,
            threshold REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS trait_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trait_name TEXT NOT NULL UNIQUE,
            enabled INTEGER DEFAULT 0,
            min_level INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS match_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            min_match_count INTEGER DEFAULT 1,
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            attributes TEXT NOT NULL,
            trait TEXT,
            status INTEGER NOT NULL DEFAULT 0,
            reason TEXT,
            matched_rules TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # 初始化默认匹配配置
    conn.execute(
        "INSERT OR IGNORE INTO match_config (id, min_match_count) VALUES (1, 1)"
    )
    conn.commit()
    conn.close()


# === 属性规则 CRUD ===

def get_attribute_rules() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM attribute_rules ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_attribute_rule(attribute_name: str, threshold: float) -> dict:
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO attribute_rules (attribute_name, threshold, updated_at) VALUES (?, ?, datetime('now', 'localtime'))",
        (attribute_name, threshold),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM attribute_rules WHERE attribute_name = ?", (attribute_name,)).fetchone()
    conn.close()
    return dict(row)


def delete_attribute_rule(rule_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM attribute_rules WHERE id = ?", (rule_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


def update_attribute_rule(rule_id: int, threshold: float) -> dict:
    conn = get_db()
    conn.execute(
        "UPDATE attribute_rules SET threshold = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (threshold, rule_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM attribute_rules WHERE id = ?", (rule_id,)).fetchone()
    conn.close()
    return dict(row)


# === 组合特性规则 ===

def get_trait_rules() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM trait_rules ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_trait_rules(traits: list[dict]) -> list[dict]:
    """批量保存组合特性配置"""
    conn = get_db()
    for t in traits:
        conn.execute(
            "INSERT OR REPLACE INTO trait_rules (trait_name, enabled, min_level, updated_at) VALUES (?, ?, ?, datetime('now', 'localtime'))",
            (t["trait_name"], 1 if t["enabled"] else 0, t["min_level"]),
        )
    conn.commit()
    rows = conn.execute("SELECT * FROM trait_rules ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# === 匹配配置 ===

def get_match_config() -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM match_config WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {"min_match_count": 1}


def save_match_config(min_match_count: int) -> dict:
    conn = get_db()
    conn.execute(
        "UPDATE match_config SET min_match_count = ?, updated_at = datetime('now', 'localtime') WHERE id = 1",
        (min_match_count,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM match_config WHERE id = 1").fetchone()
    conn.close()
    return dict(row)


# === 分析历史 ===

def add_analysis_history(
    filename: str,
    attributes: list[dict],
    trait: str | None,
    status: int,
    reason: str,
    matched_rules: list[dict] | None = None,
) -> dict:
    conn = get_db()
    conn.execute(
        "INSERT INTO analysis_history (filename, attributes, trait, status, reason, matched_rules) VALUES (?, ?, ?, ?, ?, ?)",
        (
            filename,
            json.dumps(attributes, ensure_ascii=False),
            trait,
            status,
            reason,
            json.dumps(matched_rules, ensure_ascii=False) if matched_rules else None,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM analysis_history ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row)


def get_analysis_history(limit: int = 50, offset: int = 0, status: int | None = None) -> list[dict]:
    conn = get_db()
    if status is not None:
        rows = conn.execute(
            "SELECT * FROM analysis_history WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM analysis_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        item = dict(r)
        item["attributes"] = json.loads(item["attributes"])
        item["matched_rules"] = json.loads(item["matched_rules"]) if item["matched_rules"] else []
        result.append(item)
    return result


def get_history_count(status: int | None = None) -> int:
    conn = get_db()
    if status is not None:
        row = conn.execute("SELECT COUNT(*) as cnt FROM analysis_history WHERE status = ?", (status,)).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) as cnt FROM analysis_history").fetchone()
    conn.close()
    return row["cnt"]


def delete_analysis_history(history_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM analysis_history WHERE id = ?", (history_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0
