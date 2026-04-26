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
    init_db,
    get_rule_groups, create_rule_group, update_rule_group, delete_rule_group,
    add_group_rule, update_group_rule, delete_group_rule,
    get_trait_rules, save_trait_rules,
    get_schemes, get_scheme, save_scheme, delete_scheme, load_scheme_to_config,
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


# ===== 属性定义 API =====

@app.get("/api/attributes/definitions")
def api_attribute_definitions():
    """获取所有属性定义（含取值范围和预设）"""
    return ATTRIBUTE_DEFINITIONS


@app.get("/api/traits/definitions")
def api_trait_definitions():
    """获取所有组合特性定义"""
    return [{"name": k, **v} for k, v in TRAIT_DEFINITIONS.items()]


# ===== 规则组 API =====

class CreateGroupRequest(BaseModel):
    name: str = "未命名组"


class UpdateGroupRequest(BaseModel):
    name: str


class AddRuleRequest(BaseModel):
    attribute_name: str
    threshold: float


class UpdateRuleRequest(BaseModel):
    threshold: float


@app.get("/api/rules/groups")
def api_get_rule_groups():
    """获取所有规则组（含组内规则）"""
    return {"groups": get_rule_groups()}


@app.post("/api/rules/groups")
def api_create_rule_group(req: CreateGroupRequest):
    """创建新规则组"""
    group = create_rule_group(req.name)
    return {"group": group}


@app.put("/api/rules/groups/{group_id}")
def api_update_rule_group(group_id: int, req: UpdateGroupRequest):
    """更新规则组名称"""
    group = update_rule_group(group_id, req.name)
    if not group:
        raise HTTPException(404, "规则组不存在")
    return {"group": group}


@app.delete("/api/rules/groups/{group_id}")
def api_delete_rule_group(group_id: int):
    """删除规则组"""
    ok = delete_rule_group(group_id)
    if not ok:
        raise HTTPException(404, "规则组不存在")
    return {"ok": True}


@app.post("/api/rules/groups/{group_id}/rules")
def api_add_group_rule(group_id: int, req: AddRuleRequest):
    """向组内添加规则"""
    config = get_attribute_config(req.attribute_name)
    if not config:
        raise HTTPException(400, f"未知属性: {req.attribute_name}")
    rule = add_group_rule(group_id, req.attribute_name, req.threshold)
    if not rule:
        raise HTTPException(404, "规则组不存在")
    return {"rule": rule}


@app.put("/api/rules/groups/{group_id}/rules/{rule_id}")
def api_update_group_rule(group_id: int, rule_id: int, req: UpdateRuleRequest):
    """更新组内规则阈值"""
    rule = update_group_rule(rule_id, req.threshold)
    if not rule:
        raise HTTPException(404, "规则不存在")
    return {"rule": rule}


@app.delete("/api/rules/groups/{group_id}/rules/{rule_id}")
def api_delete_group_rule(group_id: int, rule_id: int):
    """删除组内规则"""
    ok = delete_group_rule(rule_id)
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


# ===== 配置方案 API =====

class SaveSchemeRequest(BaseModel):
    name: str


@app.get("/api/schemes")
def api_get_schemes():
    """获取所有配置方案"""
    return {"schemes": get_schemes()}


@app.get("/api/schemes/{scheme_id}")
def api_get_scheme(scheme_id: int):
    """获取方案详情"""
    scheme = get_scheme(scheme_id)
    if not scheme:
        raise HTTPException(404, "方案不存在")
    return scheme


@app.post("/api/schemes")
def api_save_scheme(req: SaveSchemeRequest):
    """将当前配置保存为新方案"""
    groups = get_rule_groups()
    traits = get_trait_rules()
    # 序列化：只保留规则组名+规则内容，去掉id
    scheme_data = {
        "groups": [
            {
                "name": g["name"],
                "rules": [
                    {"attribute_name": r["attribute_name"], "threshold": r["threshold"]}
                    for r in g["rules"]
                ],
            }
            for g in groups
        ],
        "traits": [
            {"trait_name": t["trait_name"], "enabled": bool(t["enabled"]), "min_level": t["min_level"]}
            for t in traits
        ],
    }
    scheme = save_scheme(req.name, scheme_data)
    return {"scheme": scheme}


@app.post("/api/schemes/{scheme_id}/load")
def api_load_scheme(scheme_id: int):
    """加载方案到当前配置"""
    result = load_scheme_to_config(scheme_id)
    if not result:
        raise HTTPException(404, "方案不存在")
    return {"ok": True, "data": result}


@app.delete("/api/schemes/{scheme_id}")
def api_delete_scheme(scheme_id: int):
    """删除配置方案"""
    ok = delete_scheme(scheme_id)
    if not ok:
        raise HTTPException(404, "方案不存在")
    return {"ok": True}


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
        "matched_group": match_result["matched_group"],
        "raw_text": ocr_result["raw_text"],
    }


# ===== 历史记录 API =====

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
