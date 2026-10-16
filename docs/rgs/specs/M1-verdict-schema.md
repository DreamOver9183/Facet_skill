# M1：verdict JSON Schema

> /rgs-pr 的里程碑規格。由 Claude 依 design.md 撰寫；PR 合併時一併存進 `docs/rgs/specs/`。

| 項目 | 內容 |
| :-- | :-- |
| 對應需求 | R-1 |
| 相依 | 無 |
| 分支 | `feat/m1-verdict-schema` |

## 目標

新增審查者 verdict 的 JSON Schema 檔，之後 `facet_review.py` 會把它傳給 `agy --json-schema`，`verdict.py`（M2）也用它驗證 agy 的回覆。完成後 repo 有第一個測試檔，`python -m unittest discover -s tests -v` 可以執行。

## 可修改的檔案

<!-- rgs.py 只讀取這個標題下的 `路徑` 清單，guard 會擋下清單以外的寫入。 -->

- `skills/facet/references/verdict.schema.json`（新檔）：verdict 的 JSON Schema
- `tests/test_verdict_schema.py`（新檔）：schema 的測試

## 設計

schema 必須**完全等於**下面的結構（鍵的順序可以不同，縮排用 2 個空格，檔尾換行）。只用 design.md D-1 的關鍵字：`type`、`properties`、`required`、`enum`、`items`。不要加 `$schema`、`title`、`description`、`additionalProperties` 或任何其他關鍵字。

```json
{
  "type": "object",
  "properties": {
    "verdict": {"type": "string", "enum": ["APPROVED", "REVISE", "BLOCKED"]},
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "severity": {"type": "string", "enum": ["high", "medium", "low"]},
          "evidence": {"type": "string"},
          "issue": {"type": "string"},
          "suggestion": {"type": "string"}
        },
        "required": ["id", "severity", "evidence", "issue", "suggestion"]
      }
    },
    "coverage": {"type": "string"},
    "limitations": {"type": "string"},
    "resolved": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "status": {"type": "string", "enum": ["resolved", "unresolved"]},
          "note": {"type": "string"}
        },
        "required": ["id", "status", "note"]
      }
    }
  },
  "required": ["verdict", "findings", "coverage", "limitations"]
}
```

`resolved` 刻意不放在頂層 `required`：第二輪起才必填，由 M2 的 `verdict.py` 依輪次檢查（D-2）。

## 實作要點

1. 測試檔用 `unittest`，只用標準函式庫（`json`、`os`、`unittest`）。
2. 測試檔用 `os.path.dirname(os.path.abspath(__file__))` 推算 repo 根目錄，再組出 `skills/facet/references/verdict.schema.json` 的路徑；不要依賴目前工作目錄。讀檔時指定 `encoding='utf-8'`。
3. 「只用 D-1 子集」的測試要遞迴走訪整份 schema：每個 schema 節點的鍵都必須屬於 `{"type", "properties", "required", "enum", "items"}`。注意 `properties` 的值是「欄位名 → schema 節點」的對應表，欄位名本身（例如 `verdict`）不是關鍵字，要走進它的值再檢查；`items` 的值是單一 schema 節點。
4. 測試要比對完整的集合或清單（例如 `assertEqual(set(schema["required"]), {...})`），不要只檢查「包含某一項」。

## 不要做

- 不要修改上面清單以外的檔案，包括 `CLAUDE.md`、`docs/`、README。
- 不要建立 `tests/__init__.py`、`skills/facet/scripts/` 底下的任何檔案（屬於 M2）。
- 不要加入第三方套件（例如 `jsonschema`）。

## 驗收條件

- [ ] 1. `verdict.schema.json` 是合法 JSON，頂層 `type` 為 `object`，結構與「設計」一節完全相同。
- [ ] 2. 頂層 `required` 恰為 `verdict`、`findings`、`coverage`、`limitations`，不含 `resolved`。
- [ ] 3. `verdict` 的 enum 恰為 `APPROVED`、`REVISE`、`BLOCKED`。
- [ ] 4. finding 的 `required` 恰為 `id`、`severity`、`evidence`、`issue`、`suggestion`；`severity` 的 enum 恰為 `high`、`medium`、`low`。
- [ ] 5. `resolved` 是陣列，項目的 `required` 恰為 `id`、`status`、`note`；`status` 的 enum 恰為 `resolved`、`unresolved`。
- [ ] 6. 整份 schema 只用 D-1 的五個關鍵字。

## 必要測試

| 測試檔 | 案例 | 對應驗收條件 |
| :-- | :-- | :-- |
| `tests/test_verdict_schema.py` | 載入成功、頂層 type 為 object | 1 |
| `tests/test_verdict_schema.py` | 頂層 required 集合相等、`resolved` 不在其中但在 properties 中 | 2 |
| `tests/test_verdict_schema.py` | verdict enum 相等 | 3 |
| `tests/test_verdict_schema.py` | finding required 與 severity enum 相等；每個 finding 欄位的 type 為 string | 4 |
| `tests/test_verdict_schema.py` | resolved 為 array，items 的 required 與 status enum 相等 | 5 |
| `tests/test_verdict_schema.py` | 遞迴檢查只用五個關鍵字（含 properties 底下與 items 底下的節點） | 6 |

## 先前里程碑的教訓

1. 你無法執行測試：寫完後逐行檢查 import、檔案路徑與 JSON 語法（逗號、引號）。
2. 測試要真的驗證行為：用完整集合比對，不要只呼叫一下或只斷言非空。
