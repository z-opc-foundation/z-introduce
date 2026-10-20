#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""z-introduce README 定量主张自守卫。

对应 lead 仓 README「项目仓 README 口径（2026-09-30 全量收口）」第 5 条「能力可追溯」：
README 里写死的数字与名单必须能从源码 / 事实表重算出来 —— README 改了就红，
事实表变了 README 没跟上也得红。

判据口径（踩过的坑，勿随意改）：

* **事实对象只装事实侧的值**；README 侧的数字在核对当下从被核对的那份 README 现解析。
  两边都从同一份 README 取数 ⇒ 做的是恒等式比较，README 怎么改都是绿的。
* 同一个数在 README 里出现多处（标题标语 / 正文）时**每一处都单独钉**，各自不同锚点。
* **数量之外还要钉名单**：目录清单要双向核对（少一个文件、多一个文件都得红）。
* 锚点用**唯一文本 + 结构特征**，不拿数字本身当定位标签（短数字是长数字的子串）。
* 语义判定允许 **±1 行窗口**（否定词常在下一行）。
* 主张抠不到（锚点被删/被改）必须**红**，不许静默跳过。

跑法：``python3 tools/test_readme_claims.py``（或 ``python3 -m unittest discover -s tools``）。
"""
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORG = os.path.dirname(REPO)
README = os.path.join(REPO, "README.md")
MANIFEST = os.path.join(ORG, "z-opc-foundation-lead", "003_辅助能力", "bootstrap", "manifest.json")
DATA_JSON = os.path.join(REPO, "assets", "data.json")
GENERATE = os.path.join(REPO, "tools", "generate.py")
CHECK_SECRETS = os.path.join(REPO, "tools", "check_secrets.py")
INTERACTIONS = os.path.join(REPO, "tools", "test_interactions.py")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def readme_text():
    return read(README)


# ---------------------------------------------------------------- 事实侧（源码 / 事实表）

def active_manifest_repos():
    """lead manifest 里非 retired 的仓名集合（生成器的口径：status == retired 整仓排除）。"""
    data = json.loads(read(MANIFEST))
    return {r["name"] for r in data["repositories"] if r.get("status") != "retired"}


def manifest_active_count():
    return str(len(active_manifest_repos()))


def site_projects_count():
    """站点实际收录的仓数（assets/data.json 的 projects 条数）。"""
    return str(len(json.loads(read(DATA_JSON))["projects"]))


def layers_count():
    """generate.py 里 LAYERS 的层数。"""
    src = read(GENERATE)
    body = re.search(r"(?ms)^LAYERS\s*=\s*\[(.*?)\n\]", src).group(1)
    return str(len(re.findall(r'"id"\s*:', body)))


def layer_repo_names():
    body = re.search(r"(?ms)^LAYERS\s*=\s*\[(.*?)\n\]", read(GENERATE)).group(1)
    return set(re.findall(r'"(z-[a-z0-9-]+)"', body))


def tag_names():
    body = re.search(r"(?ms)^TAGS\s*=\s*\{(.*?)\n\}", read(GENERATE)).group(1)
    return set(re.findall(r'"(z-[a-z0-9-]+)"\s*:', body))


def secret_pattern_count():
    """check_secrets.py 里 PATTERNS 的正则条数。"""
    body = re.search(r"(?ms)^PATTERNS\s*=\s*\{(.*?)\n\}", read(CHECK_SECRETS)).group(1)
    return str(len(re.findall(r'^\s*"[^"]+"\s*:', body, flags=re.M)))


def interaction_step_count():
    """test_interactions.py 里探针的断言步数（``step('`` 开头的调用，不含函数定义本身）。"""
    return str(len(re.findall(r"step\('", read(INTERACTIONS))))


def generated_files():
    """仓里受 README「目录」块管辖的实际文件集：assets/ + tools/ + index.html。

    排除 __pycache__ / *.pyc（运行 Python 会生成，属运行态不是源文件）。
    """
    out = {"index.html"}
    for sub in ("assets", "tools"):
        d = os.path.join(REPO, sub)
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            if name.endswith(".pyc"):
                continue
            out.add("%s/%s" % (sub, name))
    return sorted(out)


def gap_check_before_write():
    """生成器的 LAYERS/TAGS 覆盖校验必须**走在写盘之前**。

    先写后校验的话，半旧数据已经落进 assets/ 了，README 那句
    「不会产出一个『卡片有仓、分层表里没有』的半旧站点」就是假的。
    """
    src = read(GENERATE)
    gap_at = src.find("未被 LAYERS/TAGS 覆盖")
    write_at = src.find('with open(p, "w"')
    if gap_at < 0 or write_at < 0:
        return False
    return gap_at < write_at


# ---------------------------------------------------------------- README 侧（核对当下现解析）

def _only_match(text, pattern, what):
    hits = re.findall(pattern, text, flags=re.M)
    if not hits:
        raise AssertionError("README 里抠不到%s（正则 %s）" % (what, pattern))
    if len(set(hits)) > 1:
        raise AssertionError("README 里%s抠出多个互不相同的值：%s" % (what, sorted(set(hits))))
    return hits[0]


def _one_line(text, pattern, what):
    hits = [l for l in text.splitlines() if re.search(pattern, l)]
    if not hits:
        raise AssertionError("README 里定位不到%s（正则 %s）" % (what, pattern))
    if len(hits) > 1:
        raise AssertionError("README 里%s定位不唯一（命中 %d 行）" % (what, len(hits)))
    return hits[0]


def dir_block_lines(text):
    """「## 目录」那个围栏代码块里的逐行内容。

    必须把定位**收窄到块内**：``check_secrets.py`` / ``test_interactions.py``
    在「自查」段里还会再出现一次，全文找就会命中多行。
    """
    m = re.search(r"(?ms)^## 目录\s*\n+```[a-z]*\n(.*?)\n```", text)
    if not m:
        raise AssertionError("README 里定位不到「## 目录」的代码块")
    return [l for l in m.group(1).splitlines() if l.strip()]


def _one_line_in(block, pattern, what):
    hits = [l for l in block if re.search(pattern, l)]
    if not hits:
        raise AssertionError("%s里定位不到%s（正则 %s）" % (what, what, pattern))
    if len(hits) > 1:
        raise AssertionError("%s里%s定位不唯一（命中 %d 行）" % (what, what, len(hits)))
    return hits[0]


def readme_repo_count_headline(text):
    return _only_match(text, r"当前登记 \*\*(\d+) 仓\*\*", "标题标语的仓数")


def readme_repo_count_body(text):
    return _only_match(text, r"全仓事实表（当前 (\d+) 条）", "生成段的条数")


def readme_secret_pattern_count(text):
    line = _one_line_in(dir_block_lines(text), r"check_secrets\.py", "「目录」块")
    return _only_match(line, r"（(\d+) 项正则）", "凭据自查的正则条数")


def readme_interaction_count(text):
    line = _one_line_in(dir_block_lines(text), r"test_interactions\.py", "「目录」块")
    return _only_match(line, r"（(\d+) 项断言）", "交互回归的断言条数")


def readme_layer_count(text):
    return _only_match(text, r"分层归属（(\d+) 层）", "数据口径表里的层数")


def readme_dir_listing(text):
    """「目录」代码块里逐行列出的文件路径。"""
    m = re.search(r"(?ms)^## 目录\s*\n+```[a-z]*\n(.*?)\n```", text)
    if not m:
        raise AssertionError("README 里定位不到「## 目录」的代码块")
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(line.split()[0])
    if not out:
        raise AssertionError("「## 目录」的代码块里没列出任何文件")
    return sorted(out)


def readme_half_old_site_claim(text):
    """README 那句「不会产出半旧站点」必须在场（它对应生成器的写盘前校验）。"""
    flat = re.sub(r"\s+", "", text)
    if "不会产出一个「卡片有仓、分层表里没有」的半旧站点" not in flat:
        raise AssertionError("README 里找不到「不会产出一个『卡片有仓、分层表里没有』的半旧站点」这句")
    return "在"


# ---------------------------------------------------------------- 主张表

class Claim(object):
    def __init__(self, label, readme_side, source_side, mutator):
        self.label = label
        self.readme_side = readme_side
        self.source_side = source_side
        self.mutator = mutator


def _bump(text, old, new):
    if old not in text:
        raise AssertionError("变异没生效：README 里找不到 %r" % old)
    return text.replace(old, new, 1)


def _bump_in_dir_block(text, old, new):
    """在「## 目录」代码块**内**做替换。

    必须限定在块内：``tools/generate.py`` 在「重新生成数据」段里也出现过一次，
    全文替换会改到那一句上，目录清单原封不动 ⇒ 变异形同没做。
    """
    m = re.search(r"(?ms)(^## 目录\s*\n+```[a-z]*\n)(.*?)(\n```)", text)
    if not m:
        raise AssertionError("README 里定位不到「## 目录」的代码块")
    if old not in m.group(2):
        raise AssertionError("变异没生效：「## 目录」块里找不到 %r" % old)
    return text[:m.start(2)] + m.group(2).replace(old, new, 1) + text[m.end(2):]


def claims():
    return [
        Claim("登记仓数（标题标语）", readme_repo_count_headline, manifest_active_count,
              lambda t: _bump(t, "当前登记 **", "当前登记 **X")),
        Claim("登记仓数（生成段）", readme_repo_count_body, manifest_active_count,
              lambda t: re.sub(r"全仓事实表（当前 \d+ 条）", "全仓事实表（当前 X 条）", t, count=1)),
        Claim("凭据自查正则条数", readme_secret_pattern_count, secret_pattern_count,
              lambda t: _bump_in_dir_block(t, "（%d 项正则）" % int(secret_pattern_count()),
                                          "（X 项正则）")),
        Claim("交互回归断言条数", readme_interaction_count, interaction_step_count,
              lambda t: _bump_in_dir_block(t, "（%d 项断言）" % int(interaction_step_count()),
                                          "（X 项断言）")),
        Claim("分层数", readme_layer_count, layers_count,
              lambda t: re.sub(r"分层归属（\d+ 层）", "分层归属（X 层）", t, count=1)),
        Claim("目录清单（双向）", readme_dir_listing, generated_files,
              lambda t: _bump_in_dir_block(t, "tools/generate.py", "tools/generate_X.py")),
        Claim("半旧站点防御声明", readme_half_old_site_claim,
              lambda: "在" if gap_check_before_write() else "不在",
              lambda t: re.sub(r"不会产出一个「卡片有仓、\s*分层表里没有」的半旧站点",
                               "（这句被删了）", t, count=1)),
    ]


def verify(text):
    """一次全报式：把不一致全收集齐再返回。"""
    problems = []
    for c in claims():
        try:
            actual = c.readme_side(text)
            expected = c.source_side()
        except AssertionError as e:
            problems.append("%s —— %s" % (c.label, e))
            continue
        if str(actual) != str(expected):
            problems.append("%s —— README 写 %s，事实侧重算 %s" % (c.label, actual, expected))
    return problems


class ReadmeClaimsTest(unittest.TestCase):
    def test_readme_claims_match_facts(self):
        """用例 A：真实 README 的每条主张都要与事实侧重算值一致。"""
        problems = verify(readme_text())
        self.assertEqual([], problems, "README 主张与事实侧不一致：\n  - " + "\n  - ".join(problems))

    def test_mutated_readme_is_rejected(self):
        """用例 B（牙口）：每条主张合成一个改错的 README，必须被判红且报错指向那条主张。"""
        text = readme_text()
        self.assertEqual([], verify(text), "基线 README 自身已漂移，先把 README 修回一致")
        for c in claims():
            broken = c.mutator(text)
            self.assertNotEqual(text, broken, "变异没有生效：" + c.label)
            problems = verify(broken)
            self.assertTrue(problems, "主张被放过（README 写错但没红）：" + c.label)
            self.assertTrue(any(c.label in p for p in problems),
                            "报错没指向真正对不上的主张：%s / %s" % (c.label, problems))

    def test_real_readme_not_flagged(self):
        """用例 C（不许冤枉健康页）：真实 README 不得被判红。"""
        self.assertEqual([], verify(readme_text()), "真实 README 被误判为红")

    def test_generator_covers_every_active_repo(self):
        """生成器必须覆盖 lead manifest 里每一个非 retired 仓（漏一个就会退出）。"""
        active = active_manifest_repos()
        missing = sorted(active - layer_repo_names())
        self.assertEqual([], missing, "LAYERS 未覆盖的仓：%s" % "、".join(missing))
        missing_tags = sorted(active - tag_names())
        self.assertEqual([], missing_tags, "TAGS 未覆盖的仓：%s" % "、".join(missing_tags))

    def test_generator_has_no_stale_repo_names(self):
        """LAYERS / TAGS 里不许留 manifest 已不存在的旧仓名（如 z-llm / z-render）。"""
        stale = sorted((layer_repo_names() | tag_names()) - active_manifest_repos())
        self.assertEqual([], stale, "LAYERS/TAGS 里的过期仓名：%s" % "、".join(stale))

    def test_site_data_matches_manifest(self):
        """站点收录的仓数必须等于 manifest 非 retired 条数（生成产物不能是半旧的）。"""
        self.assertEqual(manifest_active_count(), site_projects_count(),
                         "assets/data.json 的 projects 条数与 lead manifest 不一致")

    def test_generator_validates_before_writing(self):
        """覆盖校验必须走在写盘之前，否则半旧数据已经落进 assets/。"""
        self.assertTrue(gap_check_before_write(),
                        "generate.py 的 LAYERS/TAGS 覆盖校验跑在写盘之后 —— "
                        "半旧数据会先落进 assets/，README 那句「不会产出半旧站点」就是假的")


if __name__ == "__main__":
    unittest.main(verbosity=2)
