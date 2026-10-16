# 設計與計畫：facet 審查者 verdict 的格式與驗證

> 單一事實來源。每個里程碑合併後由 Claude 更新「狀態總覽」「追溯矩陣」「教訓清單」。

| 項目 | 內容 |
| :-- | :-- |
| 版本 | v1（修訂歷史見文末） |
| 需求 | `docs/rgs/requirements.md` |
| 查證基準 | `docs/handoff.md` §5、`docs/PLAN.md` §4.1、§4.3、§4.5；agy 1.4.0 |

## 狀態總覽

| 里程碑 | 狀態 | 分支／PR | 測試數 | 備註 |
| :-- | :-- | :-- | :-- | :-- |
| M1 | 已合併 | `feat/m1-verdict-schema`／#1 | 6 | agy 合併閘門 PASS，無意見 |
| M2 | 審查中 | `feat/m2-verdict-parser`／#2 | 31（累計） | 原本堆疊在 M1 上；M1 合併後已 retarget 到 base |

狀態只用：未開始、實作中、審查中、待合併、已合併、延後。

## 已查證事實

| 項目 | 結果 | 對實作的影響 |
| :-- | :-- | :-- |
| agy 1.4.0 `--json-schema` | rgs 的 `review.py` 以 `type`、`properties`、`required`、`enum`、`items` 組成的 schema 實測可用，結果在 JSON 外殼的 `structured_output` | verdict schema 只用這個子集（D-1） |
| 交接文件 §5 的 verdict 格式 | 頂層 `verdict`、`findings`、`coverage`、`limitations`；finding 有 `id`、`severity`、`evidence`、`issue`、`suggestion` | R-1 的欄位 |
| PLAN §4.5 | 第二輪起多輸出 `resolved: [{id, status: resolved\|unresolved, note}]`，只在第二輪起必填 | `resolved` 在 schema 中選填，由 `verdict.py` 依輪次檢查（D-2） |
| repo 現況 | 只有 `docs/`，沒有程式與測試 | M1 建立 `tests/` 與第一個測試檔 |

## 決策紀錄

| 編號 | 決策 | 理由與替代方案 | 日期 |
| :-- | :-- | :-- | :-- |
| D-1 | verdict schema 只用 `type`、`properties`、`required`、`enum`、`items` | 這個子集已在 agy 1.4.0 驗證可用，`verdict.py` 也只需支援這些。沒採用：`$ref`、`oneOf`、`additionalProperties`（未驗證 agy 是否接受）；第三方 `jsonschema` 套件（違反只用標準函式庫） | 2026-10-17 |
| D-2 | `resolved` 在 schema 選填，「第二輪起必填」由 `validate(..., round_no)` 檢查 | 一份 schema 供每一輪使用；之後 `facet_review.py` 可在第二輪起於執行時把 `resolved` 加進 `required` 再傳給 agy。沒採用：兩份 schema 檔（重複維護） | 2026-10-17 |
| D-3 | `VerdictError` 帶 `kind`（`parse_error`、`schema_error`），對應 PLAN §4.3 的 status | `facet_review.py` 可直接把 `kind` 當 status 回報 | 2026-10-17 |

## 架構

```text
skills/facet/
├── references/verdict.schema.json   # M1：審查者回覆的結構
└── scripts/verdict.py               # M2：parse_response → validate → evidence_found
tests/
├── test_verdict_schema.py           # M1
└── test_verdict.py                  # M2
```

之後的 `facet_review.py` 流程：取出 agy JSON 外殼的 `response`（或 `structured_output`）→ `parse_response` → `validate(obj, load_schema(), round_no)` → 對每條 finding 呼叫 `evidence_found` 並寫入 `evidence_found` 欄位。

## 風險

| 風險 | 機率／影響 | 對策 |
| :-- | :-- | :-- |
| agy 不接受某些 schema 關鍵字 | 低／中 | D-1 只用已驗證的子集 |
| 子集驗證器漏掉 schema 中新增的關鍵字 | 中／中 | `validate` 遇到不支援的關鍵字直接丟錯，而不是默默略過；測試涵蓋 |

## 里程碑

### M1：verdict JSON Schema

- 需求：R-1
- 相依：無
- 主要檔案：`skills/facet/references/verdict.schema.json`、`tests/test_verdict_schema.py`
- 測試：schema 是合法 JSON、必填欄位、enum 值、`resolved` 結構、只用 D-1 子集
- 驗證：`python -m unittest discover -s tests -v`

### M2：verdict 解析與驗證

- 需求：R-2
- 相依：M1（讀取 M1 的 schema 檔；堆疊在 M1 分支上）
- 主要檔案：`skills/facet/scripts/verdict.py`、`tests/test_verdict.py`
- 測試：code fence 去除、無法解析、必填缺漏、型別錯誤、enum 錯誤、第二輪 `resolved` 必填、`evidence_found` 空白正規化、不支援的關鍵字
- 驗證：`python -m unittest discover -s tests -v`

## 追溯矩陣

| 需求 | 里程碑 | 測試 | PR |
| :-- | :-- | :-- | :-- |
| R-1 | M1 | `tests/test_verdict_schema.py` | #1 |
| R-2 | M2 | `tests/test_verdict.py` | #2 |

## 教訓清單

<!-- 審查中反覆出現的錯誤，寫進之後每份 spec 的「先前的教訓」。 -->

（尚無）

## 修訂歷史

| 版本 | 日期 | 變更 |
| :-- | :-- | :-- |
| v1 | 2026-10-17 | 初版 |
