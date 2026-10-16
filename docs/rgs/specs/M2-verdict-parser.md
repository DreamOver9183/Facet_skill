# M2：verdict 解析與驗證

> /rgs-pr 的里程碑規格。由 Claude 依 design.md 撰寫；PR 合併時一併存進 `docs/rgs/specs/`。

| 項目 | 內容 |
| :-- | :-- |
| 對應需求 | R-2 |
| 相依 | M1（堆疊在 `feat/m1-verdict-schema` 上；讀取 M1 的 `skills/facet/references/verdict.schema.json`） |
| 分支 | `feat/m2-verdict-parser` |

## 目標

新增 `skills/facet/scripts/verdict.py`：把 agy 的回覆文字解析成 JSON，依 M1 的 schema 驗證，並判斷 finding 引用的 evidence 是否真的出現在計畫本文。之後的 `facet_review.py` 會直接呼叫這三個函式（PLAN §4.3 步驟 7）。

## 可修改的檔案

<!-- rgs.py 只讀取這個標題下的 `路徑` 清單，guard 會擋下清單以外的寫入。 -->

- `skills/facet/scripts/verdict.py`（新檔）：解析與驗證模組
- `tests/test_verdict.py`（新檔）：`verdict.py` 的測試

## 設計

只用標準函式庫（`copy`、`json`、`os`）。公開介面：

```python
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'references', 'verdict.schema.json')
SUPPORTED_KEYWORDS = frozenset({'type', 'properties', 'required', 'enum', 'items'})


class VerdictError(Exception):
    """agy 的回覆不能用。kind 是 'parse_error' 或 'schema_error'（對應 PLAN §4.3 的 status）。"""
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def load_schema(path=SCHEMA_PATH):
    """讀取 schema 檔（utf-8）並回傳 dict。"""


def parse_response(text):
    """去掉外層 code fence 後 json.loads，回傳解析結果（任何 JSON 值）。"""


def validate(obj, schema=None, round_no=1):
    """依 schema 驗證 obj，通過就回傳 obj；schema 為 None 時用 load_schema()。"""


def evidence_found(evidence, plan_text):
    """evidence 在空白正規化後是否為 plan_text 的子字串。"""
```

### parse_response

1. `text` 為 `None`、空字串或只有空白 → `VerdictError('parse_error', ...)`。
2. 先 `strip()`。若以 ```` ``` ```` 開頭：去掉第一行（可能是 ```` ``` ```` 或 ```` ```json ````），若最後一行（`strip()` 後）是 ```` ``` ```` 也去掉，再 `strip()`。
3. `json.loads`；`json.JSONDecodeError` → `VerdictError('parse_error', ...)`，訊息包含原本的錯誤說明。
4. 不處理「JSON 前後夾雜說明文字」的情況（解析失敗就是 `parse_error`）。

### validate

1. `schema` 為 `None` 時呼叫 `load_schema()`。
2. `round_no >= 2` 時，用 `copy.deepcopy` 複製 schema，把 `'resolved'` 加進頂層 `required`（已在其中就不重複加）。**不可修改呼叫者傳入的 schema 物件**（D-2）。
3. 遞迴檢查，路徑格式：根是 `$`，物件欄位是 `$.findings`，陣列元素是 `$.findings[0]`，巢狀是 `$.findings[0].severity`。每個 schema 節點依序檢查：
   - 節點中有 `SUPPORTED_KEYWORDS` 以外的鍵 → 丟出 **`ValueError`**（不是 `VerdictError`，因為這是 schema 檔本身的問題，不是 agy 回覆的問題），訊息列出不支援的關鍵字與路徑。
   - `type`：`object` → `dict`；`array` → `list`；`string` → `str`；`integer` → `int` 但不是 `bool`；`number` → `int` 或 `float` 但不是 `bool`；`boolean` → `bool`。其他 type 名稱 → `ValueError`。型別不符 → `VerdictError('schema_error', f'{path}: expected {type}')`，並且**不再往下檢查這個節點**。
   - `enum`：值不在清單中 → `VerdictError('schema_error', ...)`，訊息含路徑與允許的值。
   - `required`（值為 dict 時）：缺少的鍵 → `VerdictError('schema_error', f'{path}.{key}: missing required field')`。
   - `properties`（值為 dict 時）：對每個**存在於值中**的欄位遞迴檢查 `f'{path}.{key}'`。不在 `properties` 中的多餘欄位不報錯。
   - `items`（值為 list 時）：對每個元素遞迴檢查 `f'{path}[{i}]'`。
4. 遇到第一個錯誤就丟出（不需要收集全部錯誤）。

### evidence_found

1. 正規化：`' '.join(s.split())`（把連續空白、換行、tab 合成一個空格並去頭尾）。
2. 正規化後的 `evidence` 為空字串 → `False`。
3. 否則回傳「正規化後的 evidence 是否為正規化後 plan_text 的子字串」。

## 實作要點

1. 模組開頭寫一行 docstring，說明用途並指向 `docs/handoff.md` §5 與 `docs/PLAN.md` §4.3。
2. 測試檔用 `os.path.dirname(os.path.abspath(__file__))` 推算 repo 根目錄，把 `skills/facet/scripts` 用 `sys.path.insert(0, ...)` 加進路徑後 `import verdict`；不要依賴目前工作目錄。
3. 測試用的合法 verdict 範例放在測試檔內的函式（每次回傳新的 dict），避免測試之間共用並修改同一個物件。
4. 驗證錯誤的測試要同時斷言 `kind` 與訊息中的路徑（例如 `assertIn('$.findings[0].severity', str(cm.exception))`）。

## 不要做

- 不要修改上面清單以外的檔案，包括 M1 的 `verdict.schema.json` 與 `tests/test_verdict_schema.py`、`CLAUDE.md`、`docs/`、README。
- 不要呼叫 agy、不要做密鑰掃描或完整性快照（屬於之後的 `facet_review.py`）。
- 不要加入第三方套件，不要建立 `__init__.py`。

## 驗收條件

- [ ] 1. `parse_response` 能解析純 JSON、```` ```json ```` 與 ```` ``` ```` 包住（前後可有空白）的 JSON。
- [ ] 2. `parse_response` 遇到空白或無法解析的文字丟出 `VerdictError`，`kind == 'parse_error'`。
- [ ] 3. `validate` 對合法的第一輪 verdict（沒有 `resolved`）回傳原物件。
- [ ] 4. `validate` 對缺欄位、型別錯誤、enum 錯誤丟出 `VerdictError`，`kind == 'schema_error'`，訊息含正確路徑。
- [ ] 5. `round_no >= 2` 時缺 `resolved` 會報錯，`resolved` 合法時通過；呼叫後傳入的 schema 沒有被修改。
- [ ] 6. schema 含不支援的關鍵字或 type 時丟出 `ValueError`，且不是 `VerdictError`。
- [ ] 7. `evidence_found` 做空白正規化比對；空 evidence 回傳 `False`。
- [ ] 8. `load_schema()` 不帶參數時讀到 M1 的 schema 檔。

## 必要測試

| 測試檔 | 案例 | 對應驗收條件 |
| :-- | :-- | :-- |
| `tests/test_verdict.py` | 純 JSON；```` ```json ```` 包住；```` ``` ```` 包住且前後有空白與換行 | 1 |
| `tests/test_verdict.py` | 空字串、只有空白、`None`、壞掉的 JSON → `parse_error` | 2 |
| `tests/test_verdict.py` | 合法第一輪 verdict 通過，回傳值 `is` 原物件 | 3 |
| `tests/test_verdict.py` | 缺 `coverage`（`$.coverage`）；`findings` 是字串（`$.findings`）；`verdict` 為 `OK`（`$.verdict`）；`severity` 為 `critical`（`$.findings[0].severity`）；finding 缺 `evidence`（`$.findings[0].evidence`） | 4 |
| `tests/test_verdict.py` | 第二輪缺 `resolved`（`$.resolved`）；第二輪 `resolved` 合法通過；`resolved[0].status` 為 `done`（`$.resolved[0].status`）；同一個 schema 物件先跑第二輪再跑第一輪，第一輪仍不要求 `resolved` | 5 |
| `tests/test_verdict.py` | 自訂 schema 含 `additionalProperties` → `ValueError` 且 `assertNotIsInstance(..., VerdictError)`；自訂 schema 的 type 為 `null` → `ValueError`；`{'type': 'integer'}` 對 `True` → `schema_error` | 6 |
| `tests/test_verdict.py` | 計畫中有換行與多個空格、evidence 是單一空格版本 → `True`；不存在 → `False`；空字串與只有空白 → `False` | 7 |
| `tests/test_verdict.py` | `load_schema()` 回傳的 dict 中 `properties` 含 `verdict`、`findings`、`coverage`、`limitations`、`resolved` | 8 |

## 先前里程碑的教訓

1. 你無法執行測試：寫完後逐行檢查 import、檔案路徑、例外類別名稱與 f-string 的括號。
2. 測試要真的驗證行為：錯誤案例同時斷言 `kind` 與路徑，不要只斷言「有丟例外」。
3. 測試資料每次重新建立，避免某個測試修改後影響其他測試。
