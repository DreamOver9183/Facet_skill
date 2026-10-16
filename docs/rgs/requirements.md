# 需求：facet 審查者 verdict 的格式與驗證

| 項目 | 內容 |
| :-- | :-- |
| 版本 | v1 |
| 日期 | 2026-10-17 |
| 來源 | `docs/handoff.md` §5（verdict JSON 格式）、`docs/PLAN.md` §4.3 步驟 7、§4.5（第二輪起的 `resolved`） |

## 背景

facet 用 `agy -p` 請 Gemini 審查計畫，審查者必須回傳結構化的 verdict。PLAN Phase 2 第 1 項要求 `skills/facet/references/verdict.schema.json`，第 2 項的「解析與驗證邏輯」不依賴 Phase 1 預檢結果，可以先做。這兩項也是之後 `facet_review.py` 的基礎。

本次同時用來實測 rgs `/rgs-pr` 流程中與 GitHub 有關的部分（開 PR、留言、堆疊 PR、發佈）。

## 需求清單

| 編號 | 需求 | 優先度 | 驗收條件 |
| :-- | :-- | :-- | :-- |
| R-1 | 提供審查者 verdict 的 JSON Schema 檔 `skills/facet/references/verdict.schema.json` | 必要 | 是合法 JSON；頂層必填 `verdict`、`findings`、`coverage`、`limitations`；`verdict` 只能是 `APPROVED`、`REVISE`、`BLOCKED`；每條 finding 必填 `id`、`severity`、`evidence`、`issue`、`suggestion`，`severity` 只能是 `high`、`medium`、`low`；選填的 `resolved` 為陣列，每項必填 `id`、`status`（`resolved` 或 `unresolved`）、`note`；只用 D-1 的關鍵字子集 |
| R-2 | 提供 `skills/facet/scripts/verdict.py`，解析 agy 回覆並依 R-1 的 schema 驗證 | 必要 | `parse_response` 能去掉 code fence 後解析 JSON，無法解析時丟出 `VerdictError`（`kind == "parse_error"`）；`validate` 依 schema 檢查必填、型別、enum，第二輪起（`round_no >= 2`）`resolved` 必填，違反時丟出 `VerdictError`（`kind == "schema_error"`，訊息指出欄位路徑）；`evidence_found` 以空白正規化後的子字串比對判斷 evidence 是否出現在計畫本文 |

## 非功能需求

- 只用 Python 3.10 以上的標準函式庫。
- `verdict.py` 用相對於自身位置的路徑讀取 schema，安裝到 `~/.claude/skills/facet/` 後仍可用。
- 測試用 `python -m unittest discover -s tests -v` 執行，不依賴目前工作目錄。

## 非目標

- 呼叫 agy、組 prompt、完整性快照、密鑰掃描（屬於之後的 `facet_review.py`）。
- 通用 JSON Schema 驗證器：只支援 D-1 的子集。
- PLAN §3 的 D1–D6 決策（本次不涉及）。

## 待釐清

- [x] base 分支：沿用 `ccr-a267cbbf-nsxfdf`（已決定，2026-10-17）。
