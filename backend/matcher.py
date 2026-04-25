"""匹配逻辑 - 判定附魔是否保留"""

try:
    from .database import get_attribute_rules, get_trait_rules, get_match_config
except ImportError:
    from database import get_attribute_rules, get_trait_rules, get_match_config


def match_enchantment(attributes: list[dict], trait: dict | None) -> dict:
    """
    匹配附魔属性，返回判定结果。

    参数:
        attributes: [{"name": "命中", "value": 12.0}, ...]
        trait: {"name": "名弓", "level": 1} 或 None

    返回:
        {
            "status": 1 或 0,
            "reason": "原因说明",
            "matched_count": 匹配的属性数,
            "matched_details": [{"name": "命中", "value": 12.0, "threshold": 10.0, "matched": true}, ...],
            "trait_match": {"name": "名弓", "level": 1, "min_level": 1, "matched": true} 或 None
        }
    """
    # 获取规则
    attr_rules = get_attribute_rules()
    trait_rules = get_trait_rules()
    match_config = get_match_config()
    min_match_count = match_config["min_match_count"]

    # 构建规则映射 {属性名: 阈值}
    rule_map = {r["attribute_name"]: r["threshold"] for r in attr_rules}
    rules_empty = len(rule_map) == 0

    # 构建组合特性映射 {特性名: min_level}
    trait_map = {t["trait_name"]: t["min_level"] for t in trait_rules if t["enabled"]}
    traits_empty = len(trait_map) == 0

    # === 逐条属性匹配 ===
    matched_details = []
    matched_count = 0
    for attr in attributes:
        name = attr["name"]
        value = attr["value"]
        threshold = rule_map.get(name)
        if threshold is not None and value >= threshold:
            matched = True
            matched_count += 1
        else:
            matched = False
        matched_details.append({
            "name": name,
            "value": value,
            "threshold": threshold,
            "matched": matched,
        })

    # === 组合特性匹配 ===
    trait_match = None
    trait_matched = False
    if trait:
        trait_name = trait["name"]
        trait_level = trait["level"]
        min_level = trait_map.get(trait_name)
        if min_level is not None and trait_level >= min_level:
            trait_matched = True
            trait_match = {
                "name": trait_name,
                "level": trait_level,
                "min_level": min_level,
                "matched": True,
            }
        else:
            trait_match = {
                "name": trait_name,
                "level": trait_level,
                "min_level": min_level,
                "matched": False,
            }

    # === 判定逻辑 ===
    has_trait = trait is not None
    has_trait_in_rules = trait_name in trait_map if trait else False

    # 情况1: 有组合特性且在勾选列表中 → 只要特性满足就保留
    if has_trait and has_trait_in_rules:
        if not trait_matched:
            return _result(0, f"组合特性 {trait['name']}{trait['level']} 等级低于最低要求 {trait_map[trait_name]}",
                         matched_count, matched_details, trait_match, min_match_count)
        reason = f"组合特性 {trait['name']}{trait['level']} 符合"
        return _result(1, reason, matched_count, matched_details, trait_match, min_match_count)

    # 情况2: 有组合特性但不在勾选列表中 → 按无组合特性处理
    if has_trait and not has_trait_in_rules:
        if rules_empty:
            return _result(0, "无匹配规则且组合特性未勾选",
                         matched_count, matched_details, trait_match, min_match_count)
        if matched_count >= min_match_count:
            return _result(1, f"属性匹配 {matched_count}/{min_match_count} 条（组合特性 {trait['name']} 未勾选）",
                         matched_count, matched_details, trait_match, min_match_count)
        return _result(0, f"属性仅匹配 {matched_count}/{min_match_count} 条",
                     matched_count, matched_details, trait_match, min_match_count)

    # 情况3: 无组合特性 + 有规则
    if not has_trait and not rules_empty:
        if matched_count >= min_match_count:
            return _result(1, f"无组合特性，属性匹配 {matched_count}/{min_match_count} 条",
                         matched_count, matched_details, trait_match, min_match_count)
        return _result(0, f"无组合特性，属性仅匹配 {matched_count}/{min_match_count} 条",
                     matched_count, matched_details, trait_match, min_match_count)

    # 情况4: 无组合特性 + 无规则
    return _result(0, "无匹配规则，默认不保留",
                 matched_count, matched_details, trait_match, min_match_count)


def _result(status, reason, matched_count, matched_details, trait_match, min_match_count):
    return {
        "status": status,
        "reason": reason,
        "matched_count": matched_count,
        "min_match_count": min_match_count,
        "matched_details": matched_details,
        "trait_match": trait_match,
    }
