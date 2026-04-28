"""属性配置数据 - 预设取值范围和阈值"""

# 所有属性定义：名称 -> (最小值, 最大值, 类型, 预设[极差,普通,优秀,极品])
ATTRIBUTE_DEFINITIONS = {
    # 素质点
    "力量":  {"min": 4, "max": 10, "type": "integer",  "presets": [5, 6, 8, 9]},
    "体质":  {"min": 4, "max": 10, "type": "integer",  "presets": [5, 6, 8, 9]},
    "灵巧":  {"min": 4, "max": 10, "type": "integer",  "presets": [5, 6, 8, 9]},
    "敏捷":  {"min": 4, "max": 10, "type": "integer",  "presets": [5, 6, 8, 9]},
    "智力":  {"min": 4, "max": 10, "type": "integer",  "presets": [5, 6, 8, 9]},
    "幸运":  {"min": 4, "max": 8,  "type": "integer",  "presets": [5, 6, 7, 8]},
    # 固定值
    "MaxHp":      {"min": 60,  "max": 600, "type": "integer", "presets": [100, 200, 350, 500]},
    "MaxSp":      {"min": 12,  "max": 120, "type": "integer", "presets": [20, 40, 70, 100]},
    "物理攻击":   {"min": 12,  "max": 60,  "type": "integer", "presets": [20, 30, 45, 55]},
    "魔法攻击":   {"min": 12,  "max": 60,  "type": "integer", "presets": [20, 30, 45, 55]},
    "物理防御":   {"min": 6,   "max": 30,  "type": "integer", "presets": [10, 15, 22, 27]},
    "魔法防御":   {"min": 6,   "max": 30,  "type": "integer", "presets": [10, 15, 22, 27]},
    "命中":       {"min": 5,   "max": 30,  "type": "integer", "presets": [10, 15, 22, 27]},
    "暴击":       {"min": 1,   "max": 10,  "type": "integer", "presets": [2, 4, 7, 9]},
    "闪避":       {"min": 5,   "max": 30,  "type": "integer", "presets": [10, 15, 22, 27]},
    "暴击防护":   {"min": 1,   "max": 10,  "type": "integer", "presets": [2, 4, 7, 9]},
    # 百分比
    "MaxHp%":     {"min": 2,   "max": 10,  "type": "percent", "presets": [3.0, 5.0, 7.0, 9.0]},
    "MaxSp%":     {"min": 1,   "max": 5,   "type": "percent", "presets": [1.5, 2.5, 3.5, 4.5]},
    "爆伤%":      {"min": 1,   "max": 10,  "type": "percent", "presets": [2.0, 4.0, 7.0, 9.0]},
    "爆伤减免%":  {"min": 1,   "max": 10,  "type": "percent", "presets": [2.0, 4.0, 7.0, 9.0]},
    "治疗加成%":  {"min": 1,   "max": 5,   "type": "percent", "presets": [1.5, 2.5, 3.5, 4.5]},
    "受治疗加成%":{"min": 1,   "max": 5,   "type": "percent", "presets": [1.5, 2.5, 3.5, 4.5]},
    "物伤加成%":  {"min": 1,   "max": 4,   "type": "percent", "presets": [1.5, 2.0, 3.0, 3.5]},
    "物伤减免%":  {"min": 1,   "max": 4,   "type": "percent", "presets": [1.5, 2.0, 3.0, 3.5]},
    "装备攻速%":  {"min": 1,   "max": 4,   "type": "percent", "presets": [1.5, 2.0, 3.0, 3.5]},
    # 抗性
    "沉默抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "冰冻抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "石化抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "晕眩抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "灼烧抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "中毒抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "定身抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "恐惧抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
    "诅咒抵抗":   {"min": 1, "max": 25, "type": "resistance", "presets": [5.0, 10.0, 15.0, 20.0]},
}

# 组合特性定义
# effect_base: 等级1时的效果值，总效果 = effect_base * level
# attrs: 触发组合特性需要的两个属性
TRAIT_DEFINITIONS = {
    "神佑": {"desc": "魔法伤害减免", "attrs": ["体质", "魔法防御"], "effect_base": 2.5, "effect_unit": "%", "max_level": 4},
    "破甲": {"desc": "物理穿刺", "attrs": ["力量", "灵巧"], "effect_base": 1.5, "effect_unit": "%", "max_level": 4},
    "洞察": {"desc": "忽视魔法防御", "attrs": ["MaxSp%", "智力"], "effect_base": 5, "effect_unit": "%", "max_level": 4},
    "破魔": {"desc": "魔法穿刺", "attrs": ["智力", "灵巧"], "effect_base": 1.5, "effect_unit": "%", "max_level": 4},
    "尖锐": {"desc": "暴击伤害提升", "attrs": ["敏捷", "幸运"], "effect_base": 5, "effect_unit": "%", "max_level": 4},
    "奥法": {"desc": "魔伤加成", "attrs": ["MaxSp%", "魔法攻击"], "effect_base": 2, "effect_unit": "%", "max_level": 4},
    "斗志": {"desc": "忽视物理防御", "attrs": ["力量", "物理攻击"], "effect_base": 5, "effect_unit": "%", "max_level": 4},
    "魔力": {"desc": "吟唱速度缩短", "attrs": ["智力", "魔法攻击"], "effect_base": 2.5, "effect_unit": "%", "max_level": 4},
    "名弓": {"desc": "远程物攻增加", "attrs": ["灵巧", "命中"], "effect_base": 2.5, "effect_unit": "%", "max_level": 4},
    "利刃": {"desc": "近战物攻增加", "attrs": ["装备攻速%", "物伤加成%"], "effect_base": 2.5, "effect_unit": "%", "max_level": 4},
    "坚韧": {"desc": "物理伤害减免", "attrs": ["暴击", "物理防御"], "effect_base": 2.5, "effect_unit": "%", "max_level": 4},
    "褻渎": {"desc": "技能伤害减免", "attrs": ["体质", "智力"], "effect_base": 2.5, "effect_unit": "%", "max_level": 4},
    "狂热": {"desc": "普攻伤害增加", "attrs": ["装备攻速%", "爆伤%"], "effect_base": 2.5, "effect_unit": "%", "max_level": 4},
    "铁甲": {"desc": "暴击防护增加", "attrs": ["体质", "爆伤减免%"], "effect_base": 5, "effect_unit": "", "max_level": 4},
}

# OCR识别名称映射（处理OCR常见错误）
NAME_ALIASES = {
    "物里防御": "物理防御",
    "魔决防御": "魔法防御",
    "魔法防卸": "魔法防御",
    "物理防卸": "物理防御",
    "暴伤%": "爆伤%",
    "暴伤减免%": "爆伤减免%",
    "沉默扺抗": "沉默抵抗",
    "冰冻扺抗": "冰冻抵抗",
    "石化扺抗": "石化抵抗",
    "晕眩扺抗": "晕眩抵抗",
    "灼烧扺抗": "灼烧抵抗",
    "中毒扺抗": "中毒抵抗",
    "定身扺抗": "定身抵抗",
    "恐惧扺抗": "恐惧抵抗",
    "诅咒扺抗": "诅咒抵抗",
    # OCR可能漏掉%号（MaxHp/MaxSp 同时有固定值和百分比值，不能互转）
    "爆伤": "爆伤%",
    "爆伤减免": "爆伤减免%",
    "治疗加成": "治疗加成%",
    "受治疗加成": "受治疗加成%",
    "物伤加成": "物伤加成%",
    "物伤减免": "物伤减免%",
    "装备攻速": "装备攻速%",
    # OCR字形混淆
    "幸邉": "幸运",
}

# 值范围消歧义映射：OCR可能把多个不同属性读成同一个错误文字
# 根据属性值范围判断实际属性名
AMBIGUOUS_OCR_NAMES = {
    "母侣": ["命中", "幸运"],  # 命中(5~30) vs 幸运(4~8)，值<=4→幸运
}


def resolve_attribute_name(raw_name: str, value: float | None = None) -> str:
    """解析OCR识别的属性名，处理别名。支持值范围消歧义。"""
    # 先查确定性别名
    if raw_name in NAME_ALIASES:
        return NAME_ALIASES[raw_name]
    # 查歧义别名，用值范围消歧
    if raw_name in AMBIGUOUS_OCR_NAMES and value is not None:
        candidates = AMBIGUOUS_OCR_NAMES[raw_name]
        for name in candidates:
            cfg = ATTRIBUTE_DEFINITIONS.get(name)
            if cfg and cfg["min"] <= value <= cfg["max"]:
                return name
        # 值不在任何范围内，返回第一个候选
        return candidates[0]
    return raw_name

def get_attribute_names():
    """获取所有属性名列表"""
    return list(ATTRIBUTE_DEFINITIONS.keys())

def get_attribute_config(name: str) -> dict:
    """获取属性配置"""
    return ATTRIBUTE_DEFINITIONS.get(name)
