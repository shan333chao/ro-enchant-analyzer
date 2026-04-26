"""SQLite 数据库操作 - 规则组模型"""

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
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS rule_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '未命名组',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS group_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            attribute_name TEXT NOT NULL,
            threshold REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (group_id) REFERENCES rule_groups(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS trait_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trait_name TEXT NOT NULL UNIQUE,
            enabled INTEGER DEFAULT 0,
            min_level INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS config_schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            data TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
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
    conn.commit()
    conn.close()


# === 规则组 CRUD ===

def get_rule_groups() -> list[dict]:
    """获取所有规则组（含组内规则）"""
    conn = get_db()
    groups = conn.execute("SELECT * FROM rule_groups ORDER BY id").fetchall()
    result = []
    for g in groups:
        group = dict(g)
        rules = conn.execute(
            "SELECT * FROM group_rules WHERE group_id = ? ORDER BY id",
            (g["id"],)
        ).fetchall()
        group["rules"] = [dict(r) for r in rules]
        result.append(group)
    conn.close()
    return result


def create_rule_group(name: str = "未命名组") -> dict:
    """创建新规则组"""
    conn = get_db()
    conn.execute(
        "INSERT INTO rule_groups (name) VALUES (?)",
        (name,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM rule_groups ORDER BY id DESC LIMIT 1").fetchone()
    group = dict(row)
    group["rules"] = []
    conn.close()
    return group


def update_rule_group(group_id: int, name: str) -> dict | None:
    """更新规则组名称"""
    conn = get_db()
    conn.execute(
        "UPDATE rule_groups SET name = ? WHERE id = ?",
        (name, group_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM rule_groups WHERE id = ?", (group_id,)).fetchone()
    conn.close()
    if not row:
        return None
    group = dict(row)
    group["rules"] = get_group_rules(group_id)
    return group


def delete_rule_group(group_id: int) -> bool:
    """删除规则组（级联删除组内规则）"""
    conn = get_db()
    conn.execute("DELETE FROM rule_groups WHERE id = ?", (group_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


# === 组内规则 CRUD ===

def get_group_rules(group_id: int) -> list[dict]:
    """获取组内所有规则"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM group_rules WHERE group_id = ? ORDER BY id",
        (group_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_group_rule(group_id: int, attribute_name: str, threshold: float) -> dict | None:
    """向组内添加规则"""
    conn = get_db()
    # 检查组是否存在
    group = conn.execute("SELECT id FROM rule_groups WHERE id = ?", (group_id,)).fetchone()
    if not group:
        conn.close()
        return None
    conn.execute(
        "INSERT INTO group_rules (group_id, attribute_name, threshold) VALUES (?, ?, ?)",
        (group_id, attribute_name, threshold),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM group_rules ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row)


def update_group_rule(rule_id: int, threshold: float) -> dict | None:
    """更新组内规则阈值"""
    conn = get_db()
    conn.execute(
        "UPDATE group_rules SET threshold = ? WHERE id = ?",
        (threshold, rule_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM group_rules WHERE id = ?", (rule_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def delete_group_rule(rule_id: int) -> bool:
    """删除组内规则"""
    conn = get_db()
    conn.execute("DELETE FROM group_rules WHERE id = ?", (rule_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


# === 配置方案 ===

def get_schemes() -> list[dict]:
    """获取所有配置方案"""
    conn = get_db()
    rows = conn.execute("SELECT id, name, created_at FROM config_schemes ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_scheme(scheme_id: int) -> dict | None:
    """获取单个方案详情"""
    conn = get_db()
    row = conn.execute("SELECT * FROM config_schemes WHERE id = ?", (scheme_id,)).fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["data"] = json.loads(result["data"])
    return result


def save_scheme(name: str, data: dict) -> dict:
    """保存配置方案"""
    conn = get_db()
    conn.execute(
        "INSERT INTO config_schemes (name, data) VALUES (?, ?)",
        (name, json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()
    row = conn.execute("SELECT id, name, created_at FROM config_schemes ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row)


def delete_scheme(scheme_id: int) -> bool:
    """删除配置方案"""
    conn = get_db()
    conn.execute("DELETE FROM config_schemes WHERE id = ?", (scheme_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


def load_scheme_to_config(scheme_id: int) -> dict | None:
    """加载方案并应用到当前配置（清空现有规则组+特性，写入方案内容）"""
    conn = get_db()
    row = conn.execute("SELECT * FROM config_schemes WHERE id = ?", (scheme_id,)).fetchone()
    if not row:
        conn.close()
        return None

    scheme_data = json.loads(row["data"])

    # 清空现有规则组和组内规则
    conn.execute("DELETE FROM group_rules")
    conn.execute("DELETE FROM rule_groups")

    # 清空现有特性规则
    conn.execute("DELETE FROM trait_rules")

    # 写入方案中的规则组
    for group_data in scheme_data.get("groups", []):
        conn.execute("INSERT INTO rule_groups (name) VALUES (?)", (group_data["name"],))
        group_row = conn.execute("SELECT id FROM rule_groups ORDER BY id DESC LIMIT 1").fetchone()
        group_id = group_row["id"]
        for rule_data in group_data.get("rules", []):
            conn.execute(
                "INSERT INTO group_rules (group_id, attribute_name, threshold) VALUES (?, ?, ?)",
                (group_id, rule_data["attribute_name"], rule_data["threshold"]),
            )

    # 写入方案中的特性配置
    for trait_data in scheme_data.get("traits", []):
        conn.execute(
            "INSERT INTO trait_rules (trait_name, enabled, min_level) VALUES (?, ?, ?)",
            (trait_data["trait_name"], 1 if trait_data.get("enabled") else 0, trait_data.get("min_level", 1)),
        )

    conn.commit()
    conn.close()
    return scheme_data


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
            json.dumps(trait, ensure_ascii=False) if trait else None,
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
        item["trait"] = json.loads(item["trait"]) if item["trait"] else None
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
