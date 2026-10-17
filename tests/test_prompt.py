"""Tests for prompt module, review prompt template, and pre-review checks (M3)."""
import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "facet", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import prompt
from prompt import (
    MAX_PROMPT_CHARS,
    PromptError,
    build_prompt,
    load_plan,
    load_template,
    scan_secrets,
    strip_appendix,
    validate_prior,
)


class TestStripAppendixAndLoadPlan(unittest.TestCase):
    """驗收條件 1: strip_appendix 與 load_plan 測試。"""

    def test_strip_appendix_with_marker(self):
        """附錄標記之後的內容被截掉，結尾空白被去掉。"""
        text = "計畫正文內容\n\n<!-- facet:appendix -->\n附錄一：補充資料"
        self.assertEqual(strip_appendix(text), "計畫正文內容")

    def test_strip_appendix_without_marker(self):
        """沒有標記時回傳整份，去掉結尾空白。"""
        text = "只有正文內容\n\n   \t"
        self.assertEqual(strip_appendix(text), "只有正文內容")

    def test_strip_appendix_two_markers(self):
        """標記出現兩次時以第一個為準。"""
        text = "正文\n<!-- facet:appendix -->\n附錄1\n<!-- facet:appendix -->\n附錄2"
        self.assertEqual(strip_appendix(text), "正文")

    def test_strip_appendix_trailing_whitespace(self):
        """正文結尾的多餘換行與空白皆被去掉。"""
        text = "正文最後有空白   \t\n  \n<!-- facet:appendix -->\n附錄"
        self.assertEqual(strip_appendix(text), "正文最後有空白")

    def test_load_plan_with_bom(self):
        """load_plan 能正確讀取帶有 UTF-8 BOM 的檔案。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "plan_with_bom.md")
            with open(p, "wb") as f:
                f.write("\ufeff# 標題\n正文內容\n<!-- facet:appendix -->\n附錄".encode("utf-8"))
            res = load_plan(p)
            self.assertEqual(res, "# 標題\n正文內容")

    def test_load_plan_without_bom(self):
        """load_plan 能正確讀取無 BOM 的檔案。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "plan_no_bom.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("# 無BOM\n計畫正文\n<!-- facet:appendix -->\n附錄")
            res = load_plan(p)
            self.assertEqual(res, "# 無BOM\n計畫正文")


class TestScanSecrets(unittest.TestCase):
    """驗收條件 2 & 3: scan_secrets 命中與誤判測試。"""

    def test_scan_secrets_all_six_patterns(self):
        """六種假金鑰各自命中，kind、line 與 match 正確，不外洩完整金鑰。"""
        k_aws = "AK" + "IA" + "Q" * 16
        k_gh = "gh" + "p_" + "a" * 36
        k_pat = "github" + "_pat_" + "B" * 30
        k_openai = "s" + "k-" + "x" * 24
        k_priv = "-----BEGIN " + "RSA " + "PRIVATE KEY-----"
        k_slack = "xo" + "xb-" + "1234567890ab"

        lines = [
            f"aws key is {k_aws}",
            f"github token is {k_gh}",
            f"pat token is {k_pat}",
            f"openai secret is {k_openai}",
            f"private key is {k_priv}",
            f"slack webhook token is {k_slack}",
        ]
        text = "\n".join(lines)
        hits = scan_secrets(text)
        self.assertEqual(len(hits), 6)

        expected = [
            {"kind": "aws_access_key", "line": 1, "key": k_aws},
            {"kind": "github_token", "line": 2, "key": k_gh},
            {"kind": "github_pat", "line": 3, "key": k_pat},
            {"kind": "openai_key", "line": 4, "key": k_openai},
            {"kind": "private_key", "line": 5, "key": k_priv},
            {"kind": "slack_token", "line": 6, "key": k_slack},
        ]

        hits_json = json.dumps(hits)
        for exp, actual in zip(expected, hits):
            self.assertEqual(actual["kind"], exp["kind"])
            self.assertEqual(actual["line"], exp["line"])
            masked = exp["key"][:4] + "…" + exp["key"][-2:]
            self.assertEqual(actual["match"], masked)
            self.assertNotIn(exp["key"], hits_json)

    def test_scan_secrets_clean_text(self):
        """正常計畫文字回傳空清單。"""
        clean_text = (
            "這是一份完全正常的計畫，沒有包含任何金鑰或敏感憑證資訊。\n"
            "步驟 1：開發模組。\n"
            "步驟 2：執行測試。"
        )
        self.assertEqual(scan_secrets(clean_text), [])

    def test_scan_secrets_no_false_positives(self):
        """驗收條件 3: 不符合規格的短字串或相似詞不誤判。"""
        false_positives = [
            "task-" + "x" * 30,
            "AK" + "IA" + "1" * 10,
            "gh" + "p_" + "a" * 10,
            "s" + "k-" + "x" * 5,
            "請勿把 PRIVATE KEY 貼進計畫",
        ]
        text = "\n".join(false_positives)
        self.assertEqual(scan_secrets(text), [])


class TestLoadTemplate(unittest.TestCase):
    """驗收條件 4: load_template 解析與錯誤處理。"""

    def test_load_real_template(self):
        """實際範本檔能正確解析，五段都不是空字串。"""
        tpl = load_template()
        self.assertIn("base", tpl)
        self.assertIn("lens", tpl)
        self.assertIn("round2", tpl)
        self.assertIn("logic", tpl["lens"])
        self.assertIn("gaps", tpl["lens"])
        self.assertIn("verifiability", tpl["lens"])
        self.assertTrue(len(tpl["base"].strip()) > 0)
        self.assertTrue(len(tpl["lens"]["logic"].strip()) > 0)
        self.assertTrue(len(tpl["lens"]["gaps"].strip()) > 0)
        self.assertTrue(len(tpl["lens"]["verifiability"].strip()) > 0)
        self.assertTrue(len(tpl["round2"].strip()) > 0)

    def _make_valid_template_content(self):
        return (
            "# Title\n\n"
            "## base\n```text\nbase content {LENS} {LENS_CHECKLIST} {ROUND2_BLOCK} {PLAN}\n```\n\n"
            "## lens: logic\n```text\nlogic checklist\n```\n\n"
            "## lens: gaps\n```text\ngaps checklist\n```\n\n"
            "## lens: verifiability\n```text\nverifiability checklist\n```\n\n"
            "## round2\n```text\nround2 content {PRIOR_JSON}\n```\n"
        )

    def test_load_template_missing_section(self):
        """缺段時丟出 ValueError，訊息含段落名稱。"""
        content = self._make_valid_template_content().replace(
            "## round2\n```text\nround2 content {PRIOR_JSON}\n```\n", ""
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "bad_template.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            with self.assertRaises(ValueError) as cm:
                load_template(p)
            self.assertIn("round2", str(cm.exception))

    def test_load_template_duplicate_section(self):
        """段落重複時丟出 ValueError，訊息含段落名稱。"""
        content = self._make_valid_template_content() + "## base\n```text\ndup base\n```\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "dup_template.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            with self.assertRaises(ValueError) as cm:
                load_template(p)
            self.assertIn("base", str(cm.exception))

    def test_load_template_missing_text_block(self):
        """某段缺 ```text 區塊時丟出 ValueError，訊息含段落名稱。"""
        content = self._make_valid_template_content().replace(
            "## lens: logic\n```text\nlogic checklist\n```\n",
            "## lens: logic\njust plain text\n",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "missing_fence.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            with self.assertRaises(ValueError) as cm:
                load_template(p)
            self.assertIn("lens: logic", str(cm.exception))

    def test_load_template_unclosed_text_block(self):
        """某段 ```text 區塊沒有結束行時丟出 ValueError，訊息含段落名稱。"""
        content = self._make_valid_template_content().replace(
            "## lens: gaps\n```text\ngaps checklist\n```\n",
            "## lens: gaps\n```text\nunclosed gaps\n",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "unclosed_fence.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            with self.assertRaises(ValueError) as cm:
                load_template(p)
            self.assertIn("lens: gaps", str(cm.exception))


class TestBuildPromptRound1(unittest.TestCase):
    """驗收條件 5: 第一輪 prompt 組裝。"""

    def test_build_prompt_round1_three_lenses(self):
        """三個視角各一個案例，驗證視角內容、無混入、無前輪區塊、無佔位符殘留。"""
        logic_first = "- 步驟之間、步驟與目標或驗收條件之間，有沒有互相矛盾。"
        gaps_first = "- 遺漏的邊界條件與異常輸入（空值、超長、編碼、權限、同時執行）。"
        verif_first = "- 每條驗收條件能不能客觀判定通過或失敗；「正常」「完全相同」這類寫法要附上比對方式。"

        cases = [
            ("logic", logic_first, [gaps_first, verif_first]),
            ("gaps", gaps_first, [logic_first, verif_first]),
            ("verifiability", verif_first, [logic_first, gaps_first]),
        ]

        for lens, expected_line, other_lines in cases:
            with self.subTest(lens=lens):
                prompt_text = build_prompt("這是待審核的計畫內文。", lens, round_no=1)
                self.assertIn(f"從「{lens}」角度審查以下計畫", prompt_text)
                self.assertIn(expected_line, prompt_text)
                for other_line in other_lines:
                    self.assertNotIn(other_line, prompt_text)
                self.assertIn("這是待審核的計畫內文。", prompt_text)
                self.assertIn('"verdict":"APPROVED|REVISE|BLOCKED"', prompt_text)
                self.assertNotIn("===== 前輪處置 =====", prompt_text)
                self.assertNotIn("{LENS}", prompt_text)
                self.assertNotIn("{LENS_CHECKLIST}", prompt_text)
                self.assertNotIn("{ROUND2_BLOCK}", prompt_text)
                self.assertNotIn("{PLAN}", prompt_text)


class TestBuildPromptRound2(unittest.TestCase):
    """驗收條件 6: 第二輪 prompt 組裝。"""

    def test_build_prompt_round2(self):
        """第二輪含前輪處置、中文未跳脫之 JSON、resolved 要求，無 PRIOR_JSON 殘留。"""
        prior = {
            "changes_summary": "依前輪建議補強錯誤處理與邊界條件說明",
            "prior_findings": [
                {
                    "id": "F1",
                    "severity": "high",
                    "issue": "缺少例外處理說明",
                    "disposition": "accepted",
                    "reason": "已在第 3 步加入例外處理流程",
                }
            ],
        }
        prompt_text = build_prompt("新版修訂計畫正文", "logic", round_no=2, prior=prior)
        self.assertIn("===== 前輪處置 =====", prompt_text)
        self.assertIn("===== 前輪處置結束 =====", prompt_text)
        self.assertIn("依前輪建議補強錯誤處理與邊界條件說明", prompt_text)
        self.assertIn("缺少例外處理說明", prompt_text)
        self.assertIn("已在第 3 步加入例外處理流程", prompt_text)
        self.assertIn('"resolved"', prompt_text)
        self.assertNotIn("{PRIOR_JSON}", prompt_text)


class TestPlaceholderSinglePass(unittest.TestCase):
    """驗收條件 7: 佔位符替換只做一次，計畫內文含佔位符字樣原樣保留。"""

    def test_placeholder_single_pass(self):
        """計畫內文含有 {PLAN}、{LENS}、{PRIOR_JSON} 時原樣保留在第一輪與第二輪輸出中。"""
        tricky_plan = "步驟 {PLAN} 與 {LENS} 與 {PRIOR_JSON} 測試"

        p1 = build_prompt(tricky_plan, "logic", round_no=1)
        self.assertIn(tricky_plan, p1)

        prior = {"changes_summary": "修訂計畫", "prior_findings": []}
        p2 = build_prompt(tricky_plan, "logic", round_no=2, prior=prior)
        self.assertIn(tricky_plan, p2)


class TestPriorValidation(unittest.TestCase):
    """驗收條件 8: 前輪資料驗證與錯誤處理。"""

    def test_round1_with_prior_raises_error(self):
        """第一輪提供 prior 丟出 PromptError(kind='invalid_prior')。"""
        prior = {"changes_summary": "修訂", "prior_findings": []}
        with self.assertRaises(PromptError) as cm:
            build_prompt("計畫", "logic", round_no=1, prior=prior)
        self.assertEqual(cm.exception.kind, "invalid_prior")
        self.assertIn("Round 1", str(cm.exception))

    def test_round2_without_prior_raises_error(self):
        """第二輪未提供 prior 丟出 PromptError(kind='invalid_prior')。"""
        with self.assertRaises(PromptError) as cm:
            build_prompt("計畫", "logic", round_no=2, prior=None)
        self.assertEqual(cm.exception.kind, "invalid_prior")
        self.assertIn("Round 2", str(cm.exception))

    def test_prior_missing_required_field(self):
        """前輪資料缺少必要欄位丟出 PromptError，訊息含欄位路徑。"""
        bad_prior = {
            "changes_summary": "修訂",
            "prior_findings": [
                {
                    "id": "F1",
                    "severity": "high",
                    "issue": "缺少說明",
                    "reason": "已修復",
                }
            ],
        }
        with self.assertRaises(PromptError) as cm:
            build_prompt("計畫", "logic", round_no=2, prior=bad_prior)
        self.assertEqual(cm.exception.kind, "invalid_prior")
        self.assertIn("$.prior_findings[0].disposition", str(cm.exception))

    def test_prior_invalid_disposition(self):
        """前輪資料 disposition 不合法丟出 PromptError，訊息含欄位路徑。"""
        bad_prior = {
            "changes_summary": "修訂",
            "prior_findings": [
                {
                    "id": "F1",
                    "severity": "high",
                    "issue": "缺少說明",
                    "disposition": "postponed",
                    "reason": "已修復",
                }
            ],
        }
        with self.assertRaises(PromptError) as cm:
            build_prompt("計畫", "logic", round_no=2, prior=bad_prior)
        self.assertEqual(cm.exception.kind, "invalid_prior")
        self.assertIn("$.prior_findings[0].disposition", str(cm.exception))

    def test_prior_empty_findings_accepted(self):
        """prior_findings 為空陣列時可以通過驗證。"""
        empty_prior = {"changes_summary": "修訂計畫", "prior_findings": []}
        p = build_prompt("計畫內文", "logic", round_no=2, prior=empty_prior)
        self.assertIn('"prior_findings": []', p)


class TestPromptLengthLimit(unittest.TestCase):
    """驗收條件 9: 長度上限邊界檢查。"""

    def test_prompt_length_limit(self):
        """剛好等於上限通過，多 1 個字元丟出 PromptError(kind='plan_too_long')。"""
        overhead = len(build_prompt("x", "logic", round_no=1)) - 1
        exact_len = MAX_PROMPT_CHARS - overhead
        exact_plan = "a" * exact_len

        p = build_prompt(exact_plan, "logic", round_no=1)
        self.assertEqual(len(p), MAX_PROMPT_CHARS)

        too_long_plan = "a" * (exact_len + 1)
        with self.assertRaises(PromptError) as cm:
            build_prompt(too_long_plan, "logic", round_no=1)
        self.assertEqual(cm.exception.kind, "plan_too_long")
        self.assertIn(str(MAX_PROMPT_CHARS + 1), str(cm.exception))
        self.assertIn(str(MAX_PROMPT_CHARS), str(cm.exception))


class TestInvalidArguments(unittest.TestCase):
    """驗收條件 10: 參數型別與邊界錯誤檢查。"""

    def test_unknown_lens(self):
        """未知視角丟出 ValueError。"""
        with self.assertRaises(ValueError):
            build_prompt("計畫", "security")

    def test_invalid_round_no(self):
        """round_no 為 0、True 或字串皆丟出 ValueError。"""
        for bad_round in [0, -1, True, False, "2", 1.5]:
            with self.subTest(bad_round=bad_round):
                with self.assertRaises(ValueError):
                    build_prompt("計畫", "logic", round_no=bad_round)

    def test_invalid_plan_text(self):
        """空白或非字串計畫丟出 ValueError。"""
        for bad_plan in ["", "   ", " \t \n ", 12345, None, []]:
            with self.subTest(bad_plan=bad_plan):
                with self.assertRaises(ValueError):
                    build_prompt(bad_plan, "logic")


if __name__ == "__main__":
    unittest.main()
