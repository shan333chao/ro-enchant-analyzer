"""匹配逻辑 - 规则组匹配（组内AND，组间OR）"""

try:
    from .database import get_rule_groups
except ImportError:
    from database import get_rule_groups


def match_enchantment(attributes: list[dict], trait: dict | None) -> dict:
    """
    匹配附魔属性，返回判定结果。

    规则：
    每个规则组独立判定：
    - 有组合特性的组：特性等级>=要求 AND 所有属性规则满足
    - 无组合特性的组：所有属性规则满足
    组间OR：任一组满足即保留
    """
    # 构建属性映射 {属性名: 数值}
    attr_map = {a["name"]: a["value"] for a in attributes}

    # === 规则组匹配（组内AND，组间OR）===
    rule_groups = get_rule_groups()

    if not rule_groups:
        return _result(0, "无规则组，默认不保留")

    for group in rule_groups:
        group_rules = group.get("rules", [])

        # === 检查组合特性 ===
        group_trait_name = group.get("trait_name")
        group_trait_level = group.get("trait_level", 4)

        if group_trait_name:
            # 组有关联特性：必须有该特性且等级达标
            if not trait or trait["name"] != group_trait_name:
                continue  # 特性不匹配，跳过此组
            if trait["level"] < group_trait_level:
                continue  # 特性等级不足，跳过此组

        # === 检查属性规则（组内AND）===
        if not group_rules:
            # 无属性规则的组，有特性匹配就够了
            if group_trait_name:
                matched_details = _build_details([], attr_map)
                return _result(
                    1,
                    f"满足规则组「{group['name']}」: {group_trait_name}{group_trait_level}",
                    matched_details=matched_details,
                    matched_group=group["name"],
                    trait_match=_build_trait_match(trait, group_trait_name, group_trait_level),
                )
            continue  # 无特性也无规则，跳过

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
            # 构建匹配原因
            parts = []
            if group_trait_name:
                parts.append(f"{group_trait_name}{group_trait_level}")
            rule_str = ", ".join(f"{r['attribute_name']}>={r['threshold']}" for r in group_rules)
            if rule_str:
                parts.append(rule_str)
            reason = f"满足规则组「{group['name']}」: {' + '.join(parts)}"

            return _result(
                1,
                reason,
                matched_details=matched_details,
                matched_group=group["name"],
                trait_match=_build_trait_match(trait, group_trait_name, group_trait_level),
            )

    # 所有组都不满足
    group_names = ", ".join(g["name"] for g in rule_groups)
    return _result(0, f"未满足任何规则组 ({group_names})")


def _build_trait_match(trait, group_trait_name, group_trait_level):
    """构建特性匹配详情"""
    if not trait or not group_trait_name:
        return None
    matched = trait["name"] == group_trait_name and trait["level"] >= group_trait_level
    return {
        "name": trait["name"],
        "level": trait["level"],
        "min_level": group_trait_level,
        "matched": matched,
    }


def _build_details(rules, attr_map):
    """构建空规则组的详情"""
    return []


def _result(status, reason, matched_details=None, matched_group=None, trait_match=None):
    return {
        "status": status,
        "reason": reason,
        "matched_group": matched_group,
        "matched_details": matched_details or [],
        "trait_match": trait_match,
    }
