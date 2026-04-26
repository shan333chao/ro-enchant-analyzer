"""OCR引擎 - 识别附魔截图"""

import re
import os
import tempfile

import cv2
import numpy as np

# 禁用 oneDNN 避免 paddlepaddle 3.x 在 Windows 上的兼容性问题
os.environ["FLAGS_use_mkldnn"] = "0"

try:
    from .attribute_config import resolve_attribute_name, ATTRIBUTE_DEFINITIONS
except ImportError:
    from attribute_config import resolve_attribute_name, ATTRIBUTE_DEFINITIONS

IMAGE_DIR = os.path.join(os.path.dirname(__file__), "..")

# OCR常见识别错误映射（属性名）
TRAIT_OCR_ALIASES = {
    "名引": "名弓",
    "名利": "名弓",
    "名刃": "名弓",
    "破甲": "破甲",
    "褻读": "褻渎",
    "亵读": "褻渎",
    "亵渎": "褻渎",
}


def recognize_image(filename: str) -> dict:
    """
    识别附魔截图，返回结构化数据。

    参数:
        filename: 图片文件名（相对于项目根目录）

    返回:
        {
            "attributes": [{"name": "命中", "value": 12.0}, ...],
            "trait": {"name": "名弓", "level": 1} 或 None,
            "raw_text": "原始OCR文本"
        }
    """
    filepath = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"图片文件不存在: {filepath}")

    # 预处理图片
    preprocessed_path = _preprocess_image(filepath)

    # 懒加载 PaddleOCR
    ocr = _get_ocr()
    result = ocr.ocr(preprocessed_path)

    # 清理临时文件
    if preprocessed_path != filepath:
        try:
            os.unlink(preprocessed_path)
        except OSError:
            pass

    if not result or not result[0]:
        raise ValueError("OCR识别失败，未检测到文字")

    # 提取所有文本，按位置排序
    items = []
    for line in result[0]:
        text = line[1][0]
        confidence = line[1][1]
        if confidence > 0.5:
            box = line[0]
            cy = sum(p[1] for p in box) / 4
            cx = sum(p[0] for p in box) / 4
            items.append((cy, cx, text))

    # 按行分组：cy相近的归为同一行，行内按cx排序（左到右）
    if items:
        items.sort(key=lambda x: x[0])  # 先按cy排序
        rows = []
        current_row = [items[0]]
        for item in items[1:]:
            # 如果cy差距小于行高的一半，归为同一行
            if abs(item[0] - current_row[0][0]) < 30:
                current_row.append(item)
            else:
                current_row.sort(key=lambda x: x[1])  # 行内按cx排序
                rows.extend(current_row)
                current_row = [item]
        current_row.sort(key=lambda x: x[1])
        rows.extend(current_row)
        raw_texts = [text for _, _, text in rows]
    else:
        raw_texts = []
    raw_text = "\n".join(raw_texts)

    # 解析属性
    attributes, trait = parse_attributes(raw_texts)

    return {
        "attributes": attributes,
        "trait": trait,
        "raw_text": raw_text,
    }


def _preprocess_image(filepath: str) -> str:
    """
    预处理图片以提高OCR精度。
    1. 4x放大 - 小图(501x185)文字太小
    2. 灰度 + CLAHE对比度增强 - 处理游戏UI渐变背景
    """
    img = cv2.imread(filepath)
    if img is None:
        return filepath

    h, w = img.shape[:2]

    # 只对小图做预处理（宽<800 或 高<400）
    if w >= 800 and h >= 400:
        return filepath

    # 4x 放大
    scale = 4
    scaled = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    # 灰度
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)

    # CLAHE 对比度增强
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 保存到临时文件
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, enhanced)
    tmp.close()
    return tmp.name


_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            det_db_thresh=0.2,
            det_db_box_thresh=0.3,
            det_db_unclip_ratio=2.0,
            use_dilation=True,
        )
    return _ocr_instance


def parse_attributes(texts: list[str]) -> tuple[list[dict], dict | None]:
    """
    解析OCR文本为属性列表和组合特性。

    参数:
        texts: OCR识别的文本行列表

    返回:
        (属性列表, 组合特性)
    """
    attributes = []
    trait = None

    # 所有已知的属性名（按长度降序匹配，避免短名称误匹配）
    all_names = sorted(ATTRIBUTE_DEFINITIONS.keys(), key=len, reverse=True)

    i = 0
    while i < len(texts):
        text = texts[i].strip()
        if not text:
            i += 1
            continue

        # 检查是否为组合特性行
        trait_result = _parse_trait(text)
        if trait_result:
            trait = trait_result
            i += 1
            continue

        # 检查是否是属性名
        attr_name = None
        for name in all_names:
            if resolve_attribute_name(text) == name:
                attr_name = name
                break

        if attr_name:
            # 检查下一行是否是数值
            value = None
            if i + 1 < len(texts):
                next_text = texts[i + 1].strip()
                # 不消费组合特性行作为属性值
                if _parse_trait(next_text):
                    value = _extract_value(text, attr_name)
                    i += 1
                else:
                    value = _extract_value(next_text, attr_name)
                    if value is not None:
                        # 找到配对的数值
                        i += 2
                    else:
                        # 下一行不是数值，尝试在同一行找
                        value = _extract_value(text, attr_name)
                        i += 1
            else:
                # 没有下一行，尝试在同一行找
                value = _extract_value(text, attr_name)
                i += 1

            if value is not None:
                resolved_name = resolve_attribute_name(attr_name)
                if not any(a["name"] == resolved_name for a in attributes):
                    attributes.append({
                        "name": resolved_name,
                        "value": value,
                    })
        else:
            # 尝试单行解析（属性名+数值在同一行）
            attr = _parse_attribute(text, all_names)
            if attr:
                if not any(a["name"] == attr["name"] for a in attributes):
                    attributes.append(attr)
            i += 1

    return attributes, trait


def _parse_trait(text: str) -> dict | None:
    """解析组合特性行"""
    # 匹配: 【组合特性】名弓1 或 组合特性名弓1 或 名弓1:远程物理攻击增加2.5%
    # 包含OCR常见错误别名
    trait_names = "神佑|破甲|洞察|破魔|尖锐|奥法|斗志|魔力|名弓|名引|名利|利刃|坚韧|褻渎|亵渎|亵读|褻读|狂热|铁甲"
    trait_pattern = rf"(?:【组合特性】)?(?:组合特性)?\s*({trait_names})\s*(\d)"
    match = re.search(trait_pattern, text)
    if match:
        name = TRAIT_OCR_ALIASES.get(match.group(1), match.group(1))
        return {
            "name": name,
            "level": int(match.group(2)),
        }
    return None


def _parse_attribute(text: str, all_names: list[str]) -> dict | None:
    """解析单行属性文本"""
    # 尝试匹配属性名 + 数值
    # 常见格式: "命中 12" "暴伤% 7.1" "物理攻击 +37" "MaxHp 260" "沉默抵抗 15.5"

    for attr_name in all_names:
        if attr_name in text:
            # 提取数值
            value = _extract_value(text, attr_name)
            if value is not None:
                resolved_name = resolve_attribute_name(attr_name)
                return {
                    "name": resolved_name,
                    "value": value,
                }
    return None


def _extract_value(text: str, attr_name: str) -> float | None:
    """从文本中提取属性值"""
    # 移除属性名
    remaining = text.replace(attr_name, "").strip()
    # 移除常见干扰字符
    remaining = remaining.replace("+", "").replace("：", ":").replace("=", "")

    # 匹配数字（支持小数和百分号）
    # 百分比
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", remaining)
    if pct_match:
        return float(pct_match.group(1))

    # 普通数字
    num_match = re.search(r"(\d+(?:\.\d+)?)", remaining)
    if num_match:
        return float(num_match.group(1))

    return None
