"""匹配逻辑 - 规则组匹配（组内AND，组间OR）"""

try:
    from .database import get_rule_groups, get_trait_rules
except ImportError:
    from database import get_rule_groups, get_trait_rules


def match_enchantment(attributes: list[dict], trait: dict | None) -> dict:
    """
    匹配附魔属性，返回判定结果。

    规则：
    1. 组合特性优先 - 勾选的特性等级满足即保留
    2. 规则组匹配 - 组内AND（全满足），组间OR（任一组满足即保留）

    参数:
        attributes: [{"name": "命中", "value": 12.0}, ...]
        trait: {"name": "名弓", "level": 1} 或 None

    返回:
        {
            "status": 1 或 0,
            "reason": "原因说明",
            "matched_group": 匹配的组名 或 None,
            "matched_details": [{"name": "命中", "value": 12.0, "threshold": 10.0, "matched": true}, ...],
            "trait_match": {"name": "名弓", "level": 1, "min_level": 1, "matched": true} 或 None
        }
    """
    # 构建属性映射 {属性名: 数值}
    attr_map = {a["name"]: a["value"] for a in attributes}

    # === 组合特性匹配 ===
    trait_rules = get_trait_rules()
    trait_map = {t["trait_name"]: t["min_level"] for t in trait_rules if t["enabled"]}

    trait_match = None
    if trait:
        trait_name = trait["name"]
        trait_level = trait["level"]
        min_level = trait_map.get(trait_name)
        if min_level is not None and trait_level >= min_level:
            trait_match = {
                "name": trait_name,
                "level": trait_level,
                "min_level": min_level,
                "matched": True,
            }
        elif min_level is not None:
            trait_match = {
                "name": trait_name,
                "level": trait_level,
                "min_level": min_level,
                "matched": False,
            }
        else:
            trait_match = {
                "name": trait_name,
                "level": trait_level,
                "min_level": None,
                "matched": False,
            }

    # 组合特性优先判定
    if trait and trait["name"] in trait_map:
        if trait_match and trait_match["matched"]:
            return _result(1, f"组合特性 {trait['name']}{trait['level']} 符合",
                         trait_match=trait_match)
        return _result(0, f"组合特性 {trait['name']}{trait['level']} 等级低于最低要求 {trait_map[trait['name']]}",
                     trait_match=trait_match)

    # === 规则组匹配（组内AND，组间OR）===
    rule_groups = get_rule_groups()

    if not rule_groups:
        return _result(0, "无规则组，默认不保留", trait_match=trait_match)

    for group in rule_groups:
        group_rules = group.get("rules", [])
        if not group_rules:
            continue

        all_matched = True
        matched_details = []

        for rule in group_rules:
            attr_value = attr_map.get(rule["attribute_name"])
            if attr_value is not None and attr_value >= rule["threshold"]:
                matched_details.append({
                    "name": rule["attribute_name"],
                    "value": attr_value,
                    "threshold": rule["threshold"],
                    "matched": True,
                })
            else:
                matched_details.append({
                    "name": rule["attribute_name"],
                    "value": attr_value,
                    "threshold": rule["threshold"],
                    "matched": False,
                })
                all_matched = False

        if all_matched:
            matched_names = ", ".join(
                f"{r['attribute_name']}>={r['threshold']}" for r in group_rules
            )
            return _result(
                1,
                f"满足规则组「{group['name']}」: {matched_names}",
                matched_details=matched_details,
                matched_group=group["name"],
                trait_match=trait_match,
            )

    # 所有组都不满足
    group_names = ", ".join(g["name"] for g in rule_groups)
    return _result(0, f"未满足任何规则组 ({group_names})", trait_match=trait_match)


def _result(status, reason, matched_details=None, matched_group=None, trait_match=None):
    return {
        "status": status,
        "reason": reason,
        "matched_group": matched_group,
        "matched_details": matched_details or [],
        "trait_match": trait_match,
    }
