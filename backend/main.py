"""FastAPI 入口 - 附魔分析系统API"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# 确保可以导入同级模块
sys.path.insert(0, os.path.dirname(__file__))

from database import (
    init_db, get_attribute_rules, add_attribute_rule, delete_attribute_rule,
    update_attribute_rule, get_trait_rules, save_trait_rules,
    get_match_config, save_match_config,
    add_analysis_history, get_analysis_history, get_history_count,
    delete_analysis_history,
)
from ocr_engine import recognize_image
from matcher import match_enchantment
from attribute_config import ATTRIBUTE_DEFINITIONS, TRAIT_DEFINITIONS, get_attribute_config

app = FastAPI(title="RO 附魔分析系统")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（前端）
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def startup():
    init_db()


# ===== 前端页面 =====

@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ===== 属性配置 API =====

class AttributeRuleRequest(BaseModel):
    attribute_name: str
    threshold: float


class AttributeRuleUpdate(BaseModel):
    threshold: float


@app.get("/api/attributes/definitions")
def api_attribute_definitions():
    """获取所有属性定义（含取值范围和预设）"""
    return ATTRIBUTE_DEFINITIONS


@app.get("/api/traits/definitions")
def api_trait_definitions():
    """获取所有组合特性定义"""
    return TRAIT_DEFINITIONS


@app.get("/api/rules/attributes")
def api_get_attribute_rules():
    """获取当前属性规则列表"""
    return {"rules": get_attribute_rules()}


@app.post("/api/rules/attributes")
def api_add_attribute_rule(req: AttributeRuleRequest):
    """添加/更新属性规则"""
    config = get_attribute_config(req.attribute_name)
    if not config:
        raise HTTPException(400, f"未知属性: {req.attribute_name}")
    rule = add_attribute_rule(req.attribute_name, req.threshold)
    return {"rule": rule}


@app.put("/api/rules/attributes/{rule_id}")
def api_update_attribute_rule(rule_id: int, req: AttributeRuleUpdate):
    """更新属性规则阈值"""
    rule = update_attribute_rule(rule_id, req.threshold)
    return {"rule": rule}


@app.delete("/api/rules/attributes/{rule_id}")
def api_delete_attribute_rule(rule_id: int):
    """删除属性规则"""
    ok = delete_attribute_rule(rule_id)
    if not ok:
        raise HTTPException(404, "规则不存在")
    return {"ok": True}


# ===== 组合特性配置 API =====

class TraitRuleItem(BaseModel):
    trait_name: str
    enabled: bool
    min_level: int


class TraitRulesRequest(BaseModel):
    traits: list[TraitRuleItem]


@app.get("/api/rules/traits")
def api_get_trait_rules():
    """获取组合特性规则"""
    return {"traits": get_trait_rules()}


@app.post("/api/rules/traits")
def api_save_trait_rules(req: TraitRulesRequest):
    """批量保存组合特性规则"""
    traits = save_trait_rules([t.model_dump() for t in req.traits])
    return {"traits": traits}


# ===== 匹配配置 API =====

class MatchConfigRequest(BaseModel):
    min_match_count: int


@app.get("/api/config/match")
def api_get_match_config():
    """获取匹配配置"""
    return get_match_config()


@app.post("/api/config/match")
def api_save_match_config(req: MatchConfigRequest):
    """保存匹配配置"""
    return save_match_config(req.min_match_count)


# ===== 分析 API =====

class AnalyzeRequest(BaseModel):
    filename: str


@app.get("/api/enchantment/analyze")
def api_analyze_get(filename: str):
    """分析附魔截图（GET方式）"""
    return _do_analyze(filename)


@app.post("/api/enchantment/analyze")
def api_analyze(req: AnalyzeRequest):
    """分析附魔截图（POST方式）"""
    return _do_analyze(req.filename)


def _do_analyze(filename: str):
    """分析附魔截图核心逻辑"""
    try:
        ocr_result = recognize_image(filename)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"OCR识别失败: {str(e)}")

    # 匹配判定
    match_result = match_enchantment(ocr_result["attributes"], ocr_result["trait"])

    # 记录到历史
    try:
        add_analysis_history(
            filename=filename,
            attributes=ocr_result["attributes"],
            trait=ocr_result["trait"],
            status=match_result["status"],
            reason=match_result["reason"],
            matched_rules=match_result["matched_details"],
        )
    except Exception:
        pass  # 历史记录失败不影响结果

    return {
        "status": match_result["status"],
        "attributes": ocr_result["attributes"],
        "trait": ocr_result["trait"],
        "reason": match_result["reason"],
        "matched_details": match_result["matched_details"],
        "trait_match": match_result["trait_match"],
        "matched_count": match_result["matched_count"],
        "min_match_count": match_result["min_match_count"],
        "raw_text": ocr_result["raw_text"],
    }


# ===== 历史记录 API =====

class HistoryQuery(BaseModel):
    limit: int = 50
    offset: int = 0
    status: int | None = None


@app.get("/api/history")
def api_get_history(limit: int = 50, offset: int = 0, status: int | None = None):
    """获取分析历史"""
    records = get_analysis_history(limit=limit, offset=offset, status=status)
    total = get_history_count(status=status)
    return {"records": records, "total": total}


@app.delete("/api/history/{history_id}")
def api_delete_history(history_id: int):
    """删除历史记录"""
    ok = delete_analysis_history(history_id)
    if not ok:
        raise HTTPException(404, "记录不存在")
    return {"ok": True}


# ===== 文件列表 API =====

@app.get("/api/files")
def api_list_files():
    """列出可用的图片文件"""
    image_dir = os.path.dirname(__file__) + "/.."
    files = []
    for f in sorted(os.listdir(image_dir)):
        if f.lower().endswith((".png", ".jpg", ".jpeg")):
            files.append(f)
    return {"files": files}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
