# Facet_skill 知識庫

> Claude、Gemini 與 sub-agent 共用的專案規範。每段工作完成後只補「新的架構決策、新慣例、踩到的坑」，不要寫進度或流水帳。不要寫本機絕對路徑或 commit hash。

## 文件指引

| 想知道 | 看哪裡 |
| :-- | :-- |
| facet skill 的原始需求 | `docs/handoff.md`（交接文件） |
| 整體實作計畫、目錄結構、未決事項 | `docs/PLAN.md` |
| rgs 里程碑的需求、設計、進度 | `docs/rgs/requirements.md`、`docs/rgs/design.md` |
| 各里程碑規格與審查裁決 | `docs/rgs/specs/`、`docs/rgs/reviews/` |
| 怎麼測試 | 本檔「常用指令」 |

## 環境

| 項目 | 值 |
| :-- | :-- |
| 語言 | Python 3.10 以上，**只用標準函式庫**（PLAN §4.1） |
| 測試框架 | `unittest`（PLAN Phase 2 驗收） |
| 必要的本機設定 | 無 |

## 架構規範

- 目錄結構依 `docs/PLAN.md` §4.1：skill 本體在 `skills/facet/`（`SKILL.md`、`references/`、`scripts/`），repo 工具在 `scripts/`，測試在 `tests/`。
- `skills/facet/references/` 放給 agy 或 Claude 讀的資料（prompt 範本、摘要格式、JSON Schema），不放程式。
- `skills/facet/scripts/` 的 Python 模組只用標準函式庫，安裝後會被複製到 `~/.claude/skills/facet/`，所以只能用相對於模組自身位置（`os.path.dirname(__file__)`）的路徑找 `references/`。
- 給 `agy --json-schema` 用的 schema 只用已驗證的關鍵字子集：`type`、`properties`、`required`、`enum`、`items`（見 `docs/rgs/design.md` D-1）。

## 機密規則（不可違反）

- 目前沒有機密檔。任何 agent 都不得讀取、列印或 commit `.env`、`*.pem`、`*.key` 等檔案。
- 測試中的假金鑰（例如密鑰掃描測試）在執行時組出來，不要寫成字面值。

## 常用指令

| 目的 | 指令 |
| :-- | :-- |
| 快速檢查 | `python -m unittest discover -s tests -v` |
| 完整驗證 | `python -m unittest discover -s tests -v` |

## 慣例

- Commit：`type(scope): 摘要`（繁體中文）；內文說明原因。
- 分支：`feat/…`、`fix/…`、`chore/…`。
- 測試：`tests/test_<模組>.py`，`unittest.TestCase`；測試檔用 `os.path.dirname(__file__)` 推算 repo 根目錄，再把 `skills/facet/scripts` 加進 `sys.path`，不依賴目前工作目錄。

## 設計模式

（尚無）

## 踩坑紀錄

<!-- 依領域分組；每條寫「現象 → 原因 → 做法」。 -->

（尚無）
