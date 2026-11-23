#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""z-introduce 站点数据生成器。

扫描 lead manifest 登记的全部 z-* 仓库（仓数不在本文写死，以 `len(projects)` 现量为准），
把实测元数据（README 摘要、模块树、语言分布、代码体量、发布状态）合并成
assets/data.js 供前端渲染。仓库集合以非 retired 的 manifest 条目为准；
分层是本站按各仓 README 维护的展示分组，不是实时部署拓扑。

    python3 tools/generate.py            # 生成
    python3 tools/generate.py --root ..  # 指定仓库根（默认上一级）

登记字段沿用 lead manifest.json，依赖统计读取已有 maven-inventory 快照；
本地元数据现扫，历史登记与当前本地材料分开标注，不推断不存在的功能。
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

CODE_EXT = {
    ".java": "Java", ".kt": "Kotlin", ".py": "Python", ".go": "Go",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".vue": "Vue", ".svelte": "Svelte", ".rs": "Rust",
    ".c": "C", ".h": "C/C++ Header", ".cpp": "C++", ".sh": "Shell",
    ".sql": "SQL", ".yml": "YAML", ".yaml": "YAML",
}
SKIP_DIR = {"target", "node_modules", ".git", "dist", "build", ".idea", "logs",
            "__pycache__", ".gradle", "out", ".venv", "venv", "_code_temp"}

# 展示分组参照各仓 README；lead 的旧「全仓版本表」已归档，不作为当前事实。
# 登记名不随本机目录改名：z-render/README.md 与 package.json 均标识 z-frontend-render。
LOCAL_REPO_ALIASES = {"z-frontend-render": "z-render"}

LAYERS = [
    {
        "id": "lead", "name": "组织治理", "en": "Meta",
        "tagline": "lead 不生产新功能产品，lead 管所有产品仓",
        "desc": "组织治理仓：维护仓库登记表 manifest.json、跨仓规范、辅助脚本与新机器恢复入口。",
        "repos": ["z-opc-foundation-lead"],
    },
    {
        "id": "l1", "name": "L1 业务层", "en": "Business",
        "tagline": "一人公司的业务域，聚合在 z-opc 单体中台",
        "desc": "z-opc 提供统一主启动器；协同、资产、产品、交易、RPA 产品元数据、运维与商务等"
                "业务能力由各独立仓维护。接入与发布状态以各仓记录为准。",
        "repos": ["z-opc", "z-opcs", "z-asset", "z-product", "z-trade", "z-rpa", "z-ops",
                  "z-team", "z-biz"],
    },
    {
        "id": "l2", "name": "L2 Boot 封装层", "en": "Boot",
        "tagline": "版本权威 + Parent + Starter",
        "desc": "z-boot 以 z-boot-parent 作为消费入口，管理第三方依赖与兄弟仓接入面版本，"
                "并维护 Spring Boot starter 聚合层。",
        "repos": ["z-boot"],
    },
    {
        "id": "agent", "name": "L3 Agent 家族", "en": "Agent",
        "tagline": "从抽象基座到本地应用的一整条 agent 链路",
        "desc": "z-agent-kernel 把消息 / 工具 / 记忆 / provider / 会话契约一次收口；上层 "
                "z-llm-gateway、z-mcp、z-skill、z-bot、z-agent 各自只声明自己用到的那几个坐标。",
        "repos": ["z-agent-kernel", "z-agent", "z-llm-gateway", "z-llm-agent",
                  "z-llm-msghub", "z-mcp", "z-skill", "z-bot"],
    },
    {
        "id": "l3", "name": "L3 中间件层", "en": "Middleware",
        "tagline": "数据、通信与运行支撑能力",
        "desc": "缓存、消息队列、配置、调度、工作流、RPC、网关、图库、向量库、4A、密钥、"
                "消息下发、对象存储、代码索引、可观测性、数据源管控与 ETL。"
                "本组只表示登记仓的能力分类，不承诺所有模块互不依赖。",
        "repos": ["z-util", "z-cache", "z-mq", "z-config", "z-schedule", "z-camuda", "z-rpc",
                  "z-gw", "z-graph", "z-vector", "z-ctc", "z-mist", "z-msg",
                  "z-oss", "z-indexer", "z-wf", "z-observer", "z-dms", "z-etl"],
    },
    {
        "id": "cognition", "name": "认知与数据安全层", "en": "Cognition & Security",
        "tagline": "认知域建模 + 识别→脱敏→水印→审计四段流水线",
        "desc": "认知域（z-cognition / z-ontology）负责把知识组织成有类型、可推理的形状；"
                "数据安全线以 z-biz-security 为编排层，串起敏感识别（z-sense）、"
                "脱敏遮蔽（z-mask）、水印溯源（z-watermark）与合规留痕（z-audit）四段。"
                "这里是按主题合并的展示组；z-biz-security 的工程定位仍是 L1 业务编排仓。",
        "repos": ["z-cognition", "z-ontology", "z-biz-security",
                  "z-sense", "z-mask", "z-watermark", "z-audit"],
    },
    {
        "id": "incub", "name": "孵化层", "en": "Incubation",
        "tagline": "独立产品与开发工具",
        "desc": "低代码与报表、脚本、元数据、任务协作、扩展点、Web IDE、短网址、质量与测试资产。"
                "「孵化」沿用本站分组名，不表示未接入 z-boot 或尚未发布。",
        "repos": ["z-script", "z-lc", "z-webide", "z-meta", "z-task", "z-ext",
                  "z-surl", "z-qa"],
    },
    {
        "id": "frontend", "name": "前端与环境", "en": "Frontend & Env",
        "tagline": "不走 Maven Central 的那一组",
        "desc": "共享渲染引擎 z-frontend-render（本机目录 z-render）、前端组件库 z-frontend-common、"
                "Markdown 渲染与编辑包 z-markdown-component，以及环境编排仓 z-env 与纯静态展示站 z-introduce。",
        "repos": ["z-frontend-render", "z-frontend-common", "z-markdown-component", "z-env", "z-introduce"],
    },
]

# 一句话定位，依据各仓 README；不保留过期的模块数、占位状态或发布断言。
TAGS = {
    "z-opc-foundation-lead": "组织治理大脑 + 新机器恢复钥匙",
    "z-opc": "一人公司全栈中台单体", "z-opcs": "任务撮合 / 服务市场",
    "z-asset": "模块资产元数据采集器", "z-product": "产品设计信息汇总（PM 工件）",
    "z-trade": "交易域 order / payment / usage", "z-rpa": "RPA 产品元数据（应用市场 / 需求中心）",
    "z-ops": "个人公司运维平台", "z-boot": "版本权威 / Parent / Starter",
    "z-agent-kernel": "Agent 框架基座", "z-agent": "云端 Agent SaaS 平台",
    "z-llm-gateway": "中心化 LLM 网关", "z-llm-agent": "CLI Agent 服务化（对话化本机 CLI）",
    "z-llm-msghub": "msgHub 中心消息路由（WebSocket 枢纽 + Agent SDK）", "z-mcp": "MCP 协议桥接与注册中心",
    "z-skill": "Skill 注册中心 + Marketplace", "z-bot": "本地 agent 应用（CLI + HTTP）",
    "z-util": "多模块工具库集（第一底座）",
    "z-cache": "Redis 协议兼容分布式缓存", "z-mq": "NameServer + Broker 消息队列",
    "z-config": "配置中心 + 服务注册中心", "z-schedule": "分布式任务调度",
    "z-camuda": "工作流引擎（Camunda 基座）", "z-rpc": "RPC 框架",
    "z-gw": "Netty 自研 API 网关", "z-graph": "图数据库（磁盘版本链存储）",
    "z-vector": "自研向量数据库",
    "z-ctc": "4A 中心 + SSO", "z-mist": "分布式密钥 / 秘密管理",
    "z-msg": "多通道消息下发抽象层", "z-oss": "可插拔对象存储抽象层",
    "z-indexer": "代码索引服务", "z-script": "多 DSL 脚本平台 + Mock Server",
    "z-lc": "低代码平台（通用 CRUD 引擎）", "z-webide": "Web IDE 后端（IDE 即服务）",
    "z-meta": "元数据管理平台", "z-task": "任务协作管理平台",
    "z-ext": "运行时可插拔扩展点框架",
    "z-frontend-render": "平台共享前端渲染引擎",
    "z-frontend-common": "组织共享前端组件库",
    "z-observer": "可观测性域独立仓",
    "z-env": "中间件编排环境仓",
    "z-wf": "自研 BPMN 流程引擎",
    "z-surl": "短网址服务（短码 / 解析 / 命中统计）",
    "z-qa": "质量与测试资产（用例集 / E2E / 套件编排）",
    "z-team": "数字员工协同域独立仓（后端多模块 + 前端组件包）",
    "z-introduce": "组织只读展示站（本站）",
    "z-biz": "商务外壳域（客户档案 / 合同 / 票据 / 对账）",
    "z-dms": "数据源管控底座（凭据只存 z-mist 引用）",
    "z-etl": "ETL 引擎域（reader → transform → writer）",
    "z-cognition": "业务认知域（术语 / 概念 / 证据链 / 消歧 / 影响面）",
    "z-ontology": "本体层 · TBox/ABox + RDFS 子集推理 + 一致性校验",
    "z-biz-security": "数据安全域编排层（场景→策略→四段流水线）",
    "z-sense": "敏感识别与分类分级引擎",
    "z-mask": "脱敏与遮蔽引擎",
    "z-watermark": "水印引擎（显式 / 隐写 / 盲水印溯源）",
    "z-audit": "审计与合规留痕（事件模型 + 哈希链 + 留存期）",
    "z-markdown-component": "共享 Markdown 渲染与编辑组件包",
}

# 仅保留可从当前本地材料定位的边界说明；未复核的旧审计结论不当作当前告警。
NOTES = {
    "z-boot": "据本仓 README「火车制重构」：原 fleet / dependencies 独立 BOM 已退役，"
              "消费入口为 z-boot-parent；旧 Central 制品保留不代表当前拓扑。",
    "z-team": "据本仓 README「仓的由来」：2026-10-20 从 z-opc 迁出，"
              "当前为自带父 POM、reactor 与前端组件包的独立仓，不是空占位。",
    "z-camuda": "材料存在差异：z-boot/README.md 的 2026-11-17 注记称本仓已归档，"
                "但 manifest 尚未标 retired；本站按 manifest 保留，不据此断言仍在维护。",
    "z-biz-security": "据本仓 README：L1 业务编排仓，只做编排与拦截判定，"
                      "不自行实现识别、脱敏、水印、审计算法。",
    "z-introduce": "本站本身：纯静态，无后端；本地实测数据与登记快照分开标注。",
}

# 被依赖 TOP3 与「独立仓」两组读数一律在 main() 里现算自 lead 的 maven-inventory 产物，
# 不在这里写死 —— 写死的那一轮就是它和 lead 对不上、要人工追的那一轮。


def run(cmd, cwd):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=20)
        return p.stdout.strip()
    except Exception:
        return ""


def local(tag):
    return tag.split("}")[-1]


def read_pom(path):
    out = {}
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return out
    for child in root:
        t = local(child.tag)
        if t in ("name", "description", "artifactId", "version") and t not in out and child.text:
            out[t] = child.text.strip()
    return out


def first_paragraph(md, limit=460):
    buf = []
    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            if buf:
                break
            continue
        if line.startswith(("#", ">", "|", "```", "---", "===", "<!--", "[!", "<img", "<p",
                           "<div", "<a ", "<br", "![", "*  ")):
            if buf:
                break
            continue
        if line.startswith("!") or re.match(r"^\[.*\]\(.*\)\s*$", line):
            continue
        if set(line) <= set("-|* "):
            continue
        buf.append(line)
    text = " ".join(buf)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*|__|\*", "", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def readme_title(md):
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
        if s:
            break
    return ""


def count_code(d):
    counts, nbytes = {}, 0
    for base, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in SKIP_DIR and not x.startswith((".", "dist.stale-"))]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in CODE_EXT:
                counts[CODE_EXT[ext]] = counts.get(CODE_EXT[ext], 0) + 1
                try:
                    nbytes += os.path.getsize(os.path.join(base, f))
                except OSError:
                    pass
    return counts, nbytes


def submodules(d):
    mods = []
    for e in sorted(os.listdir(d)):
        p = os.path.join(d, e)
        if not os.path.isdir(p) or e in SKIP_DIR or e.startswith(("_", ".")):
            continue
        if os.path.exists(os.path.join(p, "pom.xml")) or \
           os.path.exists(os.path.join(p, "build.gradle")) or e.startswith("z-"):
            mods.append(e)
    return mods


def frontend_hits(d):
    hits = []
    for base, dirs, _ in os.walk(d):
        dirs[:] = [x for x in dirs if x not in SKIP_DIR and not x.startswith((".", "dist.stale-"))]
        for e in dirs:
            if e in ("webapp", "static", "resources", "frontend", "admin-frontend",
                     "web", "ui", "public", "assets"):
                rel = os.path.relpath(os.path.join(base, e), d)
                if rel not in hits:
                    hits.append(rel)
        if len(hits) > 6:
            break
    return hits[:6]


def docs_of(d):
    out = [c for c in ("_doc", "docs", "doc", "_docs")
           if os.path.isdir(os.path.join(d, c))]
    for e in sorted(os.listdir(d)):
        if e.startswith("_doc") and os.path.isdir(os.path.join(d, e)) and e not in out:
            out.append(e)
    return out


def git_info(d):
    if not os.path.isdir(os.path.join(d, ".git")):
        return {"cloned": False, "commits": 0, "lastCommit": ""}
    commits = run(["git", "rev-list", "--count", "HEAD"], d)
    return {
        "cloned": True,
        "commits": int(commits) if commits.isdigit() else 0,
        "lastCommit": run(["git", "log", "-1", "--format=%cs"], d),
    }


def active_repositories(rows):
    """先检查重复，再过滤 retired，避免 dict 覆盖掩盖台账错误。"""
    manifest = {}
    seen = set()
    for row in rows:
        name = row["name"]
        if name in seen:
            raise ValueError("manifest 重复仓名: " + name)
        seen.add(name)
        if row.get("status") != "retired":
            manifest[name] = row
    return manifest


def validate_catalog(manifest, layers, tags, notes):
    """手维护清单须与有效 manifest 双向相等，失败时禁止写产物。"""
    active = set(manifest)
    seen, ids, problems = {}, set(), []
    for layer in layers:
        if layer["id"] in ids:
            problems.append("重复分层 ID: " + layer["id"])
        ids.add(layer["id"])
        for name in layer["repos"]:
            seen[name] = seen.get(name, 0) + 1
    gap = sorted((active - set(seen)) | (active - set(tags)))
    stale = sorted((set(seen) | set(tags) | set(notes)) - active)
    dup = sorted(n for n, count in seen.items() if count > 1)
    if gap:
        problems.append("未被 LAYERS/TAGS 覆盖: " + "、".join(gap))
    if stale:
        problems.append("LAYERS/TAGS/NOTES 含过期仓名: " + "、".join(stale))
    if dup:
        problems.append("仓库重复分层: " + "、".join(dup))
    if problems:
        raise ValueError("分类与 manifest 不一致，先改 tools/generate.py 再生成：\n  - "
                         + "\n  - ".join(problems))
    return {name: layer["id"] for layer in layers for name in layer["repos"]}


def repo_directory(root, name):
    """优先同名目录；仅对已核实的别名回退，并检查 npm 包身份。"""
    canonical = os.path.join(root, name)
    if os.path.isdir(canonical) or name not in LOCAL_REPO_ALIASES:
        return canonical
    alias = os.path.join(root, LOCAL_REPO_ALIASES[name])
    if not os.path.isdir(alias):
        return canonical
    with open(os.path.join(alias, "package.json"), encoding="utf-8") as fh:
        package = json.load(fh)
    if package.get("name") != "@yuku123/" + name:
        raise ValueError("目录别名的 package.json 身份不符: " + os.path.basename(alias))
    return alias


def dependency_summary(manifest, inventory):
    """按有效仓集合统计快照；别名归一，退役仓不再作为当前消费方或榜单项。"""
    active = set(manifest)
    aliases = {alias: name for name, alias in LOCAL_REPO_ALIASES.items() if name in active}
    fan, out_to = {}, {}
    for row in inventory.values():
        for edge in row.get("dep_edges") or []:
            consumer = aliases.get(edge["consumer"], edge["consumer"])
            owner = aliases.get(edge["owner"], edge["owner"])
            if consumer not in active or consumer == owner:
                continue
            # 活跃仓依赖退役制品仍是出边，不能伪称零跨仓依赖。
            out_to.setdefault(consumer, set()).add(owner)
            if owner in active:
                fan.setdefault(owner, set()).add(consumer)
    top = sorted(((name, len(consumers)) for name, consumers in fan.items()),
                 key=lambda item: (-item[1], item[0]))[:3]
    zero = sorted(name for name in active
                  if inventory[name]["is_maven"] and not out_to.get(name))
    return top, zero


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "assets"))
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out_dir = os.path.abspath(args.out)

    manifest_path = os.path.join(
        root, "z-opc-foundation-lead/003_辅助能力/bootstrap/manifest.json")
    if not os.path.exists(manifest_path):
        sys.exit("找不到 manifest.json：%s" % manifest_path)
    with open(manifest_path, encoding="utf-8") as fh:
        try:
            manifest = active_repositories(json.load(fh)["repositories"])
            layer_of = validate_catalog(manifest, LAYERS, TAGS, NOTES)
        except ValueError as exc:
            sys.exit(str(exc))

    # 跨仓依赖图现算：消费面 = 去重后的 (owner, artifactId, version) 边里 owner→consumer 的仓数
    inv_path = os.path.join(
        root, "z-opc-foundation-lead/003_辅助能力/maven-inventory/out/inventory.json")
    if not os.path.exists(inv_path):
        sys.exit("缺 maven-inventory 产物：%s\n"
                 "⇒ 先跑 lead 的 003_辅助能力/maven-inventory（被依赖 TOP3 / 独立仓两组都从它现算，"
                 "宁可不出站也不能抄旧数）" % inv_path)
    with open(inv_path, encoding="utf-8") as fh:
        inventory = json.load(fh)
    inv = {r["name"]: r for r in inventory["repos"]}
    missing_inventory = sorted(set(manifest) - set(inv))
    if missing_inventory:
        sys.exit("maven-inventory 未覆盖有效仓，请先刷新快照: " + "、".join(missing_inventory))
    DEP_FANS, ZERO_DEP = dependency_summary(manifest, inv)

    # 实测扫描
    scan = {}
    for name in manifest:
        try:
            d = repo_directory(root, name)
        except (OSError, ValueError) as exc:
            sys.exit(str(exc))
        if not os.path.isdir(d):
            continue
        pom = os.path.join(d, "pom.xml")
        pd = read_pom(pom) if os.path.exists(pom) else {}
        md, rfile = "", ""
        for cand in ("README.md", "readme.md", "README.MD", "README_zh.md"):
            p = os.path.join(d, cand)
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="ignore") as fh:
                    md = fh.read()
                rfile = cand
                break
        langs, nbytes = count_code(d)
        ver = pd.get("version", "")
        scan[name] = {
            "localDir": os.path.basename(d),
            "artifactId": pd.get("artifactId", ""),
            "version": "" if ver.startswith("${") else ver,
            "summary": first_paragraph(md) if md else "",
            "readmeFile": rfile,
            "readmeTitle": readme_title(md) if md else "",
            "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
            "codeKB": round(nbytes / 1024),
            "modules": submodules(d),
            "docs": docs_of(d),
            "frontend": frontend_hits(d),
            "docker": os.path.exists(os.path.join(d, "docker-compose.yml")) or
                      os.path.exists(os.path.join(d, "Dockerfile")),
            **git_info(d),
        }

    projects = []
    for name, mf in manifest.items():
        s = scan.get(name, {})
        note = NOTES.get(name, "")
        if s.get("localDir", name) != name:
            note = (note + " 登记名为 %s，本地采集目录为 %s；README 与 package.json 已核对。"
                    % (name, s["localDir"])).strip()
        projects.append({
            "name": name,
            "localDir": s.get("localDir", ""),
            "tagline": TAGS[name],
            "purpose": re.sub(r"\s+", " ", mf.get("purpose", "")).strip(),
            "layer": layer_of[name],
            "artifactId": s.get("artifactId", ""),
            "version": s.get("version", ""),
            "published": mf.get("published_status", ""),
            "maven": bool(inv.get(name, {}).get("is_maven", False)),
            "private": mf.get("private"),
            "language": mf.get("language", ""),
            "sizeKB": mf.get("size_kb", 0),
            "remote": (mf.get("remote", "") or "").replace(
                "git@github.com:", "https://github.com/").removesuffix(".git"),
            "summary": s.get("summary", ""),
            "readmeFile": s.get("readmeFile", ""),
            "readmeTitle": s.get("readmeTitle", ""),
            "languages": s.get("languages", {}),
            "codeFiles": sum(s.get("languages", {}).values()),
            "codeKB": s.get("codeKB", 0),
            "modules": s.get("modules", [])[:26],
            "docs": s.get("docs", []),
            "frontend": s.get("frontend", []),
            "cloned": s.get("cloned", False),
            "commits": s.get("commits", 0),
            "lastCommit": s.get("lastCommit", ""),
            "docker": s.get("docker", False),
            "note": note,
        })
    projects.sort(key=lambda p: p["name"])

    cloned = [p for p in projects if p["cloned"]]
    langs = {}
    for p in cloned:
        for k, v in p["languages"].items():
            langs[k] = langs.get(k, 0) + v

    # 站内所有「仓数 / 已发中央 / 公开仓」读数一律由上面的实测集现算，
    # 不在源码里写死数字——写死的那次就是它和 lead 对不上的那次。
    n_repos = len(projects)
    n_cloned = len(cloned)
    n_published = sum(1 for p in projects if p["published"] == "central")
    # 「已发中央」有两类通道：Maven Central 与 npm @yuku123，混在一个数里就会把 z-render 说成 Java 构件
    n_pub_npm = sum(1 for p in projects if p["published"] == "central" and not p["maven"])
    n_pub_maven = n_published - n_pub_npm
    n_public = sum(1 for p in projects if p["private"] is False)
    n_unknown_visibility = sum(1 for p in projects if p["private"] is None)
    n_java = sum(1 for p in cloned if "Java" in p["languages"])
    top_fan = max(DEP_FANS, key=lambda x: x[1]) if DEP_FANS else ("—", 0)

    data = {
        "org": {
            "name": "z-opc-foundation", "zhName": "一人公司技术基座",
            "tagline": "%d 个自研仓库，从工具库到 agent 平台的一整条自建栈" % n_repos,
            "desc": "z-opc-foundation 面向一人公司与小型团队，维护业务应用、Agent、基础设施与共享组件。"
                    "本站按 manifest 收录 %d 个非退役仓库，结合本地 README、模块与代码文件扫描展示。"
                    "发布状态沿用登记快照：%d 个 Maven 仓标记已发 Central，%d 个非 Maven 仓标记 npm；"
                    "本次生成不访问远端核验发布状态。" % (n_repos, n_pub_maven, n_pub_npm),
            "facts": [
                {"k": "登记仓库", "v": str(n_repos),
                 "d": "1 lead + %d 产品 / 业务仓，本机已 clone %d" % (n_repos - 1, n_cloned)},
                {"k": "已发中央", "v": str(n_pub_maven),
                 "d": "manifest 登记为已发布的 Maven 仓；另有 %d 个登记为 npm 发布"
                     % n_pub_npm},
                {"k": "公开仓", "v": str(n_public),
                 "d": "按 manifest 的 private=false 计数；可见性未知 %d 仓，未重测 GitHub" % n_unknown_visibility},
                {"k": "被依赖 TOP1", "v": "%d 仓" % top_fan[1],
                 "d": "%s 是事实上的第一底座" % top_fan[0]},
            ],
        },
        "stats": {
            "repos": n_repos, "cloned": n_cloned,
            "codeFiles": sum(p["codeFiles"] for p in cloned),
            "modules": sum(len(p["modules"]) for p in projects),
            "commits": sum(p["commits"] for p in cloned),
            "javaRepos": n_java,
            "published": n_published,
            "publicRepos": n_public,
            "withUi": sum(1 for p in projects if p["frontend"]),
        },
        "languages": [{"name": k, "count": v} for k, v in
                      sorted(langs.items(), key=lambda kv: -kv[1])[:6]],
        "layers": LAYERS,
        "depFans": [{"name": n, "count": c} for n, c in DEP_FANS],
        "zeroDep": ZERO_DEP,
        "inventoryGenerated": inventory.get("generated_at", "未记录"),
        "generated": datetime.date.today().isoformat(),
        "projects": projects,
    }

    # 再钉最终卡片集合：无缺失、无额外项、无重复；所有检查都在写盘前。
    names = [p["name"] for p in projects]
    if set(names) != set(manifest) or len(names) != len(manifest):
        sys.exit("生成卡片集合与有效 manifest 不一致，拒绝写盘")

    os.makedirs(out_dir, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for fname, header in (("data.js", "window.ZDESC = "), ("data.json", "")):
        p = os.path.join(out_dir, fname)
        with open(p, "w", encoding="utf-8") as fh:
            if header:
                fh.write("/* 由 tools/generate.py 从 %d 个仓库实测生成，勿手改 */\n"
                         % n_repos + header)
            fh.write(payload)
            if header:
                fh.write(";\n")
    print("%d 仓 → %s" % (len(projects), out_dir))
    print("   已 clone %d · 代码文件 %d · 模块 %d · 提交 %d" % (
        data["stats"]["cloned"], data["stats"]["codeFiles"],
        data["stats"]["modules"], data["stats"]["commits"]))
    miss = [p["name"] for p in projects if not p["summary"]]
    print("   无 README 摘要:", "、".join(miss) or "无")
    print("   集合 / 分层 / 定位校验通过")
    print("   目录别名:", "、".join(p["name"] + " → " + p["localDir"] for p in projects
                                  if p["localDir"] and p["localDir"] != p["name"]) or "无")


if __name__ == "__main__":
    main()
