# Facet_skill 知識庫

> Claude、Gemini 與 sub-agent 共用的專案規範。每段工作完成後只補「新的架構決策、新慣例、踩到的坑」，不要寫進度或流水帳。不要寫本機絕對路徑或 commit hash。

## 文件指引

| 想知道 | 看哪裡 |
| :-- | :-- |
| facet skill 的原始需求 | `docs/handoff.md`（交接文件） |
| 整體實作計畫、目錄結構、未決事項 | `docs/PLAN.md` |
| agy 在本機的實測行為（旗標、模型、寫檔、耗時） | `docs/preflight-results.md` |
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
- 跨平台（Windows、macOS、Linux）：不依賴 bash、`timeout`、`find`、`/dev/null`；子程序的 stdin 用 `subprocess.DEVNULL`；直譯器名稱不寫死 `python3`；終止 process 樹依作業系統分開處理（`docs/PLAN.md` D7）。
- 審查者的唯讀保障靠 agy 工作區的 PreToolUse hook（只放行 `finish`、`wait`），不靠 `--sandbox` 或 `--mode plan`（`docs/rgs/design.md` D-4）。

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

- 驗證器分兩段：先靜態檢查整個 schema（不支援的關鍵字、型別名稱、結構），再比對資料；範例是 `skills/facet/scripts/verdict.py` 的 `_check_schema` 與 `_validate_node`。

## 踩坑紀錄

<!-- 依領域分組；每條寫「現象 → 原因 → 做法」。 -->

### agy

- agy 不加防護會寫到工作目錄以外 → 使用者的 agy 設定是 `toolPermission: always-proceed`，`--sandbox`、`--mode plan` 都擋不住 → 一律在工作區放 PreToolUse hook，並在事後比對快照。
- agy 的 `--json-schema` 結果不能從 `response` 解析 → `response` 是模型自己寫的 JSON 加上 `finish` 工具參數兩段接在一起 → 只讀 `structured_output`。
- agy hook 沒有執行、agy 以 `invalid UTF-8` 錯誤結束 → Windows 上 hook 以 `cmd /c` 執行，沒有空白的路徑加了引號就會失敗 → 執行檔路徑只在含空白時加引號。
- 少傳 `--model` 時審查者變成 Claude → 使用者的 agy 預設模型是 Claude Opus 5.5 → `--model` 必傳，且必須以 `gemini-` 開頭。

### Windows 終端機

- 在 Git Bash 用 `python -c` 讀含中文的管道輸出會變亂碼 → 預設用系統編碼（cp950）解碼 → 讀 `sys.stdin.buffer` 再用 UTF-8 解碼，輸出前 `sys.stdout.reconfigure(encoding="utf-8")`。
