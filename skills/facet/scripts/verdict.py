"""Verdict parsing, schema validation, and evidence checking (docs/handoff.md §5, docs/PLAN.md §4.3)."""

import copy
import json
import os

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "references",
    "verdict.schema.json",
)
SUPPORTED_KEYWORDS = frozenset({"type", "properties", "required", "enum", "items"})

_TYPE_MAP = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
}


class VerdictError(Exception):
    """agy 的回覆不能用。kind 是 'parse_error' 或 'schema_error'（對應 PLAN §4.3 的 status）。"""

    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def load_schema(path=SCHEMA_PATH):
    """讀取 schema 檔（utf-8）並回傳 dict。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_response(text):
    """去掉外層 code fence 後 json.loads，回傳解析結果（任何 JSON 值）。"""
    if text is None:
        raise VerdictError("parse_error", "Response text is None")
    if not isinstance(text, str):
        raise VerdictError(
            "parse_error",
            f"Response text must be a string, got {type(text).__name__}",
        )
    stripped = text.strip()
    if not stripped:
        raise VerdictError("parse_error", "Response text is empty or whitespace")

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise VerdictError("parse_error", f"Failed to parse JSON: {exc}") from exc


def _validate_node(val, node, path):
    if not isinstance(node, dict):
        raise ValueError(f"Schema node at {path} must be a dict")

    # 1. 檢查 SUPPORTED_KEYWORDS 以外的鍵
    extra_keys = set(node.keys()) - SUPPORTED_KEYWORDS
    if extra_keys:
        raise ValueError(
            f"Unsupported schema keyword(s) {sorted(extra_keys)} at {path}"
        )

    # 2. 檢查 type
    if "type" in node:
        expected_type = node["type"]
        if expected_type not in _TYPE_MAP:
            raise ValueError(f"Unsupported schema type '{expected_type}' at {path}")
        if not _TYPE_MAP[expected_type](val):
            raise VerdictError("schema_error", f"{path}: expected {expected_type}")

    # 3. 檢查 enum
    if "enum" in node:
        allowed = node["enum"]
        if not isinstance(allowed, (list, tuple, set)):
            raise ValueError(f"'enum' at {path} must be a list")
        matched = False
        for item in allowed:
            if type(val) is type(item) and val == item:
                matched = True
                break
            elif (
                isinstance(val, (int, float))
                and isinstance(item, (int, float))
                and not isinstance(val, bool)
                and not isinstance(item, bool)
                and val == item
            ):
                matched = True
                break
        if not matched:
            raise VerdictError(
                "schema_error", f"{path}: value {val!r} not in enum {allowed}"
            )

    # 4. 檢查 required（值為 dict 時）
    if "required" in node and isinstance(val, dict):
        req_fields = node["required"]
        if not isinstance(req_fields, (list, tuple, set)):
            raise ValueError(f"'required' at {path} must be a list")
        for req_key in req_fields:
            if req_key not in val:
                raise VerdictError(
                    "schema_error", f"{path}.{req_key}: missing required field"
                )

    # 5. 檢查 properties（值為 dict 時）
    if "properties" in node and isinstance(val, dict):
        props = node["properties"]
        if not isinstance(props, dict):
            raise ValueError(f"'properties' at {path} must be a dict")
        for prop_key, prop_schema in props.items():
            if prop_key in val:
                _validate_node(val[prop_key], prop_schema, f"{path}.{prop_key}")

    # 6. 檢查 items（值為 list 時）
    if "items" in node and isinstance(val, list):
        item_schema = node["items"]
        if not isinstance(item_schema, dict):
            raise ValueError(f"'items' at {path} must be a dict")
        for i, item in enumerate(val):
            _validate_node(item, item_schema, f"{path}[{i}]")


def validate(obj, schema=None, round_no=1):
    """依 schema 驗證 obj，通過就回傳 obj；schema 為 None 時用 load_schema()。"""
    if schema is None:
        schema = load_schema()

    if round_no >= 2:
        schema = copy.deepcopy(schema)
        req = schema.get("required")
        if req is None:
            schema["required"] = ["resolved"]
        elif isinstance(req, list):
            if "resolved" not in req:
                req.append("resolved")
        elif isinstance(req, (set, tuple)):
            if "resolved" not in req:
                schema["required"] = list(req) + ["resolved"]

    _validate_node(obj, schema, "$")
    return obj


def evidence_found(evidence, plan_text):
    """evidence 在空白正規化後是否為 plan_text 的子字串。"""
    if not isinstance(evidence, str) or not isinstance(plan_text, str):
        return False
    norm_evidence = " ".join(evidence.split())
    if not norm_evidence:
        return False
    norm_plan = " ".join(plan_text.split())
    return norm_evidence in norm_plan
