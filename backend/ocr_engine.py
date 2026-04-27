"""OCR引擎 - 识别附魔截图"""

import re
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

try:
    from .attribute_config import resolve_attribute_name, ATTRIBUTE_DEFINITIONS, AMBIGUOUS_OCR_NAMES
except ImportError:
    from attribute_config import resolve_attribute_name, ATTRIBUTE_DEFINITIONS, AMBIGUOUS_OCR_NAMES

IMAGE_DIR = os.path.join(os.path.dirname(__file__), "..")

# 日志目录
LOG_DIR = Path(IMAGE_DIR) / "logs" / "ocr"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# OCR常见识别错误映射（属性名）
# OCR属性名常见误识别纠正（在垃圾过滤前应用）
OCR_TEXT_ALIASES = {
    "%dHXDW": "MaxHp%",
    "dHXDW": "MaxHp%",
    "MaxHpX": "MaxHp%",
    "Maxtp%": "MaxSp%",
}


def _correct_ocr_text(text: str) -> str:
    """纠正OCR常见误识别文本"""
    return OCR_TEXT_ALIASES.get(text, text)


TRAIT_OCR_ALIASES = {
    "名引": "名弓",
    "名利": "名弓",
    "名刃": "名弓",
    "破甲": "破甲",
    "褻读": "褻渎",
    "亵读": "褻渎",
    "亵渎": "褻渎",
}


def _is_valid_text(text: str) -> bool:
    """过滤垃圾文本（水印、UI元素等）"""
    # 过滤单个特殊字符（不含数字）
    if len(text.strip()) <= 1 and not any(c.isdigit() for c in text):
        return False
    # 过滤明显的水印/UI垃圾
    garbage_patterns = ['©', '%dHXDW', 'dHXDW', '□', '■', '◆', '●', '○']
    if any(pat in text for pat in garbage_patterns):
        return False
    # 过滤纯符号或乱码
    valid_chars = set('0123456789.%+·•-')
    if all(c in valid_chars for c in text.replace(' ', '')) and not any(c.isdigit() for c in text):
        return False
    return True


def recognize_image(filename: str) -> dict:
    """
    识别附魔截图，返回结构化数据。

    参数:
        filename: 图片文件名（相对于项目根目录）

    返回:
        {
            "attributes": [{"name": "命中", "value": 12.0}, ...],
            "trait": {"name": "名弓", "level": 1} 或 None,
            "raw_text": "原始OCR文本",
            "log_id": "日志ID"
        }
    """
    # 生成日志ID
    log_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    filepath = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"图片文件不存在: {filepath}")

    # 预处理图片（返回多版本用于双通OCR）
    preprocessed = _preprocess_image(filepath)

    # 懒加载 PaddleOCR
    ocr = _get_ocr()

    # 优先尝试固定布局OCR（501x185小图，按行裁剪分别识别）
    fixed_texts = _ocr_fixed_layout(filepath, ocr)

    # 收集所有OCR检测结果（文本 + 位置 + 置信度）

    # 收集所有OCR检测结果（文本 + 位置 + 置信度）
    # 每项: (cy, cx, text, confidence)
    all_items = []

    if preprocessed:
        # 双通OCR：分别对彩色版和CLAHE灰度版识别，合并结果
        for img_version in preprocessed:
            result = ocr.ocr(img_version)
            if result and result[0]:
                for line in result[0]:
                    text = _correct_ocr_text(line[1][0])
                    confidence = line[1][1]
                    if confidence > 0.5 and _is_valid_text(text):
                        box = line[0]
                        cy = sum(p[1] for p in box) / 4
                        cx = sum(p[0] for p in box) / 4
                        all_items.append((cy, cx, text, confidence))
    else:
        # 大图直接识别
        result = ocr.ocr(filepath)
        if not result or not result[0]:
            raise ValueError("OCR识别失败，未检测到文字")
        for line in result[0]:
            text = _correct_ocr_text(line[1][0])
            confidence = line[1][1]
            if confidence > 0.5 and _is_valid_text(text):
                box = line[0]
                cy = sum(p[1] for p in box) / 4
                cx = sum(p[0] for p in box) / 4
                all_items.append((cy, cx, text, confidence))

    if not all_items:
        raise ValueError("OCR识别失败，未检测到文字")

    # 双通去重：位置相近(cy<30且cx<50)的合并，保留置信度更高的
    if preprocessed:
        merged = []
        for item in all_items:
            is_dup = False
            for i, existing in enumerate(merged):
                if abs(item[0] - existing[0]) < 30 and abs(item[1] - existing[1]) < 50:
                    # 位置重叠，保留置信度更高的；若置信度相同则保留文本更长的
                    if item[3] > existing[3] or (item[3] == existing[3] and len(item[2]) > len(existing[2])):
                        merged[i] = item
                    is_dup = True
                    break
            if not is_dup:
                merged.append(item)
        all_items = merged

    # 按行分组：cy相近的归为同一行，行内按cx排序（左到右）
    all_items.sort(key=lambda x: x[0])  # 先按cy排序
    rows = []
    current_row = [all_items[0]]
    for item in all_items[1:]:
        # 如果cy差距小于行高的一半，归为同一行
        if abs(item[0] - current_row[0][0]) < 30:
            current_row.append(item)
        else:
            current_row.sort(key=lambda x: x[1])  # 行内按cx排序
            rows.extend(current_row)
            current_row = [item]
    current_row.sort(key=lambda x: x[1])
    rows.extend(current_row)
    raw_texts = [item[2] for item in rows]
    raw_text = "\n".join(raw_texts)

    # 解析属性
    attributes, trait = parse_attributes(raw_texts)

    # 如果全图OCR属性不足3条，且固定布局有结果，尝试补充
    if len(attributes) < 3 and fixed_texts is not None:
        fixed_attrs, fixed_trait = parse_attributes(fixed_texts)
        # 固定布局结果更多则替换
        if len(fixed_attrs) > len(attributes):
            attributes = fixed_attrs
            trait = fixed_trait
            raw_texts = fixed_texts
            raw_text = "\n".join(raw_texts)

    # 写入日志
    log_data = {
        "log_id": log_id,
        "timestamp": timestamp,
        "filename": filename,
        "raw_texts": raw_texts,
        "raw_text": raw_text,
        "attributes": attributes,
        "trait": trait,
    }
    log_file = LOG_DIR / f"{log_id}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    # 追加到文本日志
    log_txt_file = LOG_DIR / "ocr_log.txt"
    with open(log_txt_file, "a", encoding="utf-8") as f:
        f.write(f"[{log_id}] {timestamp} | {filename}\n")
        for i, txt in enumerate(raw_texts):
            f.write(f"  [{i}] {txt}\n")
        f.write(f"  解析: {len(attributes)}个属性, {trait['name'] if trait else '无特性'}\n")
        f.write("-" * 80 + "\n")

    return {
        "attributes": attributes,
        "trait": trait,
        "raw_text": raw_text,
        "log_id": log_id,
    }


def _ocr_fixed_layout(filepath: str, ocr) -> list[str]:
    """
    对501x185固定布局的小图，按行裁剪属性名和数值区域，分别放大+CLAHE后单独OCR。
    返回有序文本列表。
    """
    img = cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None

    h, w = img.shape[:2]
    if not (490 <= w <= 520 and 175 <= h <= 195):
        return None

    # 行定义：(y_start, y_end)
    rows = [(5, 40), (42, 77), (79, 114)]
    trait_row = (116, 165)
    name_x = (10, 200)
    value_x = (280, 460)
    trait_x = (10, 400)

    def ocr_crop(crop, scale=8):
        """裁剪→放大→CLAHE→OCR，返回文本列表"""
        scaled = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        result = ocr.ocr(bgr)
        texts = []
        if result and result[0]:
            for line in result[0]:
                text = _correct_ocr_text(line[1][0]).strip()
                if text and _is_valid_text(text):
                    texts.append(text)
        return texts

    texts = []
    for y1, y2 in rows:
        # 属性名
        name_texts = ocr_crop(img[y1:y2, name_x[0]:name_x[1]])
        texts.extend(name_texts)
        # 数值
        val_texts = ocr_crop(img[y1:y2, value_x[0]:value_x[1]])
        texts.extend(val_texts)

    # 第4行组合特性
    trait_texts = ocr_crop(img[trait_row[0]:trait_row[1], trait_x[0]:trait_x[1]])
    texts.extend(trait_texts)

    return texts if texts else None


def _preprocess_image(filepath: str) -> list[np.ndarray]:
    """
    预处理图片，返回多个版本用于双通OCR合并。
    对于501x185固定布局的小图：按行裁剪属性名和数值区域，分别放大后拼接。
    对于其他小图：整体4x放大。
    """
    # 使用 np.fromfile + cv2.imdecode 支持 Unicode 路径（中文目录）
    try:
        img = cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        img = None
    if img is None:
        return []

    h, w = img.shape[:2]

    # 只对小图做预处理
    if w >= 800 and h >= 400:
        return []

    # 固定布局小图已由 _ocr_fixed_layout 处理，此处走通用放大
    # 其他小图：4x放大
    scale = 4
    scaled = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    # CLAHE 灰度版（转回BGR以兼容OCR输入）
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    return [scaled, enhanced]


_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from .onnxocr.onnx_paddleocr import ONNXPaddleOcr
        except ImportError:
            from onnxocr.onnx_paddleocr import ONNXPaddleOcr
        _ocr_instance = ONNXPaddleOcr(
            use_angle_cls=True,
            use_gpu=False,
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

        # 检查是否是属性名（歧义名需要先获取值再消歧）
        attr_name = None
        is_ambiguous = text in AMBIGUOUS_OCR_NAMES
        if not is_ambiguous:
            for name in all_names:
                if resolve_attribute_name(text) == name:
                    attr_name = name
                    break
        else:
            # 歧义名：先提取下一行的值用于消歧
            peek_value = None
            if i + 1 < len(texts):
                next_text = texts[i + 1].strip()
                if not _parse_trait(next_text):
                    peek_value = _extract_value(next_text, text)
            resolved = resolve_attribute_name(text, value=peek_value)
            if resolved in ATTRIBUTE_DEFINITIONS:
                attr_name = resolved

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
