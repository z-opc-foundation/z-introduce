#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""z-desc 站点数据生成器。

扫描 lead manifest 登记的全部 z-* 仓库（仓数不在本文写死，以 `len(projects)` 现量为准），
把实测元数据（README 摘要、模块树、语言分布、代码体量、发布状态）合并成
assets/data.js 供前端渲染。分层口径与 lead 的 docs/ORG_COGNITION.md 家族成员表一致。

    python3 tools/generate.py            # 生成
    python3 tools/generate.py --root ..  # 指定仓库根（默认上一级）

数据口径与 z-opc-foundation-lead 的 manifest.json + README 版本表一致；
任何"看起来像"但代码里不存在的功能，本生成器不做推断，只呈现实测字段。
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

# 分层口径取自 z-opc-foundation-lead/README.md 的「全仓版本表」
LAYERS = [
    {
        "id": "lead", "name": "组织治理", "en": "Meta",
        "tagline": "lead 不生产新功能产品，lead 管所有产品仓",
        "desc": "组织的治理大脑：全仓事实表 manifest.json、强制规范、10 个跨仓技能、"
                "新机器一键恢复。三条设计原则是「数字必须现测」「所有脚本共享一份 manifest」"
                "「零外部依赖（python3 + bash + git）」。",
        "repos": ["z-opc-foundation-lead"],
    },
    {
        "id": "l1", "name": "L1 业务层", "en": "Business",
        "tagline": "一人公司的业务域，聚合在 z-opc 单体中台",
        "desc": "不再把每个业务域拆成独立微服务：一个 z-opc-main-starter 进程 + 一个 oc 库"
                "承接全部能力，其余业务仓以 Central 坐标被依赖或独立部署。",
        "repos": ["z-opc", "z-opcs", "z-asset", "z-product", "z-trade", "z-rpa", "z-ops",
                  "z-team"],
    },
    {
        "id": "l2", "name": "L2 Boot 封装层", "en": "Boot",
        "tagline": "版本权威 + BOM + 全套 Starter",
        "desc": "z-boot 家族把第三方依赖版本锁进 BOM，并为每个 L3 中间件提供聚合 starter。"
                "组织内绝大多数 Java 仓的 parent 指向 z-boot-parent，业务仓只声明坐标不写版本。",
        "repos": ["z-boot"],
    },
    {
        "id": "agent", "name": "L3 Agent 家族", "en": "Agent",
        "tagline": "从抽象基座到本地应用的一整条 agent 链路",
        "desc": "z-agent-kernel 把消息 / 工具 / 记忆 / provider / 会话契约一次收口；上层 "
                "z-llm、z-mcp、z-skill、z-bot、z-agent-proxy、z-agent 各自只声明自己用到的那几个坐标。",
        "repos": ["z-agent-kernel", "z-agent", "z-llm", "z-mcp", "z-skill", "z-bot",
                  "z-agent-proxy"],
    },
    {
        "id": "l3", "name": "L3 中间件层", "en": "Middleware",
        "tagline": "数据面模块只向下打 z-util / z-boot，不互依",
        "desc": "自研基础设施群：缓存、消息队列、配置中心、调度、工作流（Camunda 封装线 z-camuda "
                "与自研 BPMN 线 z-wf 两条并存）、RPC、网关、图库、向量库、知识库、4A、密钥、"
                "消息下发、对象存储、代码索引。"
                "跨中间件的边全在 admin / web / registry 控制面。",
        "repos": ["z-util", "z-cache", "z-mq", "z-config", "z-schedule", "z-camuda", "z-rpc",
                  "z-gw", "z-graph", "z-vector", "z-kb", "z-ctc", "z-mist", "z-msg",
                  "z-oss", "z-indexer", "z-wf"],
    },
    {
        "id": "incub", "name": "孵化层", "en": "Incubation",
        "tagline": "尚未接入 z-boot 聚合 starter 的独立产品仓",
        "desc": "低代码、报表、脚本、元数据、任务协作、扩展点、Web IDE、短网址、质量与测试资产 "
                "—— 已各自发版到 Central，但还没被 z-boot 家族聚合。",
        "repos": ["z-script", "z-lc", "z-webide", "z-meta", "z-task", "z-ext", "z-report",
                  "z-surl", "z-qa"],
    },
    {
        "id": "frontend", "name": "前端与环境", "en": "Frontend & Env",
        "tagline": "不走 Maven Central 的那一组",
        "desc": "z-render 是平台共享的前端渲染引擎（npm @yuku123/render）；z-env 把 MySQL / "
                "Redis / Nacos / Kafka / MinIO / ES 等依赖层以「组件 + 版本 + 场景」三段式收口，"
                "一条命令拉起、一条命令重置；z-desc 是本站本身，纯静态无后端。",
        "repos": ["z-render", "z-env", "z-desc"],
    },
]

# 一句话定位，取自 lead 仓版本表的「定位」列
TAGS = {
    "z-opc-foundation-lead": "组织治理大脑 + 新机器恢复钥匙",
    "z-opc": "一人公司全栈中台单体", "z-opcs": "任务撮合 / 服务市场",
    "z-asset": "模块资产元数据采集器", "z-product": "产品设计信息汇总（PM 工件）",
    "z-trade": "交易域 order / payment / usage", "z-rpa": "RPA（复刻影刀）",
    "z-ops": "个人公司运维平台", "z-boot": "启动器 / Starter / BOM",
    "z-agent-kernel": "Agent 框架基座（25 子模块）", "z-agent": "云端 Agent SaaS 平台",
    "z-llm": "中心化 LLM 网关", "z-mcp": "MCP 协议桥接与注册中心",
    "z-skill": "Skill 注册中心 + Marketplace", "z-bot": "本地 agent 应用（CLI + HTTP）",
    "z-agent-proxy": "三方 agent 适配代理", "z-util": "多模块工具库集（第一底座）",
    "z-cache": "Redis 协议兼容分布式缓存", "z-mq": "NameServer + Broker 消息队列",
    "z-config": "配置中心 + 服务注册中心", "z-schedule": "分布式任务调度",
    "z-camuda": "工作流引擎（Camunda 基座）", "z-rpc": "RPC 框架",
    "z-gw": "Netty 自研 API 网关", "z-graph": "图数据库（增量存储）",
    "z-vector": "自研向量数据库", "z-kb": "自托管知识库（RAG）",
    "z-ctc": "4A 中心 + SSO", "z-mist": "分布式密钥 / 秘密管理",
    "z-msg": "多通道消息下发抽象层", "z-oss": "可插拔对象存储抽象层",
    "z-indexer": "代码索引服务", "z-script": "多 DSL 脚本平台 + Mock Server",
    "z-lc": "低代码平台（通用 CRUD 引擎）", "z-webide": "Web IDE 后端（IDE 即服务）",
    "z-meta": "元数据管理平台", "z-task": "任务协作管理平台",
    "z-ext": "运行时可插拔扩展点框架", "z-report": "AI 拖拽式报表平台",
    "z-render": "平台共享前端渲染引擎", "z-env": "中间件编排环境仓",
    "z-wf": "自研 BPMN 流程引擎（与 z-camuda 两条线并存）",
    "z-surl": "短网址服务（短码 / 解析 / 命中统计）",
    "z-qa": "质量与测试资产（用例集 / E2E / 套件编排）",
    "z-team": "Z-Team 协同域独立仓（空占位，代码仍在 z-opc）",
    "z-desc": "组织只读展示站（本站）",
}

# 已知问题，逐条取自 lead 仓各轮审计的实测记录（近期一轮为 2026-10-08），不做推测
NOTES = {
    "z-boot": "⚠️ z-boot-parent 1.0.23 的 fleet 版本仍写 1.0.1，实际已发 1.0.2，消费方继承到落后一档",
    "z-asset": "⚠️ parent 仍是 com.zifang:z-opc 且 relativePath 指向不存在的文件，独立仓不可构建（P0）",
    "z-oss": "⚠️ pom 宣传 MinIO provider，实现未落地",
    "z-graph": "⚠️ 默认纯内存存储，重启丢数据",
    "z-kb": "未配向量 / 图存储时自动回落 JSON + 内存",
    "z-indexer": "已发 Central，组织内暂无消费方",
    "z-webide": "⚠️ 仓名 z-webide ≠ 构件名 z-tool-webide",
    "z-task": "是任务管理而非定时调度，仓内无调度器实现",
    "z-bot": "本地 0.2.1 高于 Central 0.2.0，待发版",
    "z-opcs": "本地 1.0.0-SNAPSHOT，未发 Central",
    "z-report": "本地 1.0.0-SNAPSHOT，未发 Central",
    "z-env": "无 pom，属编排仓而非 Java 构件",
    "z-render": "发布渠道是 npm @yuku123/render，不走 Central",
    "z-ops": "GitHub 有仓，本机未 clone（manifest 已标 not_cloned）",
    "z-mcp": "当前零跨仓依赖，独立性最强",
    "z-opc": "reactor 模块已从 9 降到 4，被拆走的中间件改由 Central 坐标消费",
    "z-wf": "⚠️ 同坐标 io.github.yuku123:z-wf 的 1.x 是 Camunda 线（现为 z-camuda 仓），"
            "两仓无共同历史，消费方须锁 2.x",
    "z-team": "空占位仓：代码仍在 z-opc 的 z-team 模块里，孵化尚未搬入",
    "z-desc": "本站本身：无 pom、不发中央，数据由本生成器实测产出",
}

DEP_FANS = [("z-util", 28), ("z-boot", 22), ("z-agent-kernel", 7)]
ZERO_DEP = ["z-agent-kernel", "z-util", "z-graph", "z-mcp", "z-env", "z-render"]


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
        dirs[:] = [x for x in dirs if x not in SKIP_DIR and not x.startswith(".")]
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
        dirs[:] = [x for x in dirs if x not in SKIP_DIR]
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
        manifest = {r["name"]: r for r in json.load(fh)["repositories"]}

    # 实测扫描
    scan = {}
    for name in manifest:
        d = os.path.join(root, name)
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

    layer_of = {r: l["id"] for l in LAYERS for r in l["repos"]}
    projects = []
    for name, mf in manifest.items():
        s = scan.get(name, {})
        projects.append({
            "name": name,
            "tagline": TAGS.get(name, mf.get("purpose", "")[:40]),
            "purpose": re.sub(r"\s+", " ", mf.get("purpose", "")).strip(),
            "layer": layer_of.get(name, "other"),
            "artifactId": s.get("artifactId", ""),
            "version": s.get("version", ""),
            "published": mf.get("published_status", ""),
            "private": bool(mf.get("private", True)),
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
            "note": NOTES.get(name, ""),
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
    n_public = sum(1 for p in projects if not p["private"])
    n_java = sum(1 for p in cloned if "Java" in p["languages"])
    top_fan = max(DEP_FANS, key=lambda x: x[1]) if DEP_FANS else ("—", 0)

    data = {
        "org": {
            "name": "z-opc-foundation", "zhName": "一人公司技术基座",
            "tagline": "%d 个自研仓库，从工具库到 agent 平台的一整条自建栈" % n_repos,
            "desc": "z-opc-foundation 是一个「一人公司」形态的技术组织：把一个中小团队日常需要的缓存、"
                    "消息队列、配置中心、调度、工作流、RPC、网关、图库、向量库、知识库、4A、"
                    "密钥管理、对象存储、低代码、报表、脚本平台全部自研，而不是从 Spring Cloud / "
                    "Dubbo / Kafka / Milvus / Dify / Camunda 各拉一个现成件。%d 个仓库里 %d 个 "
                    "Java 仓已发 Maven Central (io.github.yuku123)，前端走 npm @yuku123。"
                    % (n_repos, n_published),
            "facts": [
                {"k": "登记仓库", "v": str(n_repos),
                 "d": "1 lead + %d 产品 / 业务仓，本机已 clone %d" % (n_repos - 1, n_cloned)},
                {"k": "已发中央", "v": str(n_published), "d": "Java 构件发布到 io.github.yuku123"},
                {"k": "公开仓", "v": str(n_public),
                 "d": "按 lead manifest 的可见性字段，与 GitHub org API 同口径"},
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
        "generated": datetime.date.today().isoformat(),
        "projects": projects,
    }

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
    print("✅ %d 仓 → %s" % (len(projects), out_dir))
    print("   已 clone %d · 代码文件 %d · 模块 %d · 提交 %d" % (
        data["stats"]["cloned"], data["stats"]["codeFiles"],
        data["stats"]["modules"], data["stats"]["commits"]))
    miss = [p["name"] for p in projects if not p["summary"]]
    print("   无 README 摘要:", "、".join(miss) or "无")
    un = [p["name"] for p in projects if p["layer"] == "other"]
    no_tag = [p["name"] for p in projects if p["name"] not in TAGS]
    print("   未归层:", "、".join(un) or "无")
    print("   无一句话定位:", "、".join(no_tag) or "无")
    # LAYERS / TAGS 是手维护的：manifest 补登记新仓而这里不拦，站点就会
    # 交付「卡片有仓、分层表里没有」的半旧读数（46 仓那轮就是这么漏了 5 仓）。
    gap = sorted(set(un) | set(no_tag))
    if gap:
        sys.exit("❌ %d 仓未被 LAYERS/TAGS 覆盖: %s —— 先补分类再生成" % (len(gap), "、".join(gap)))


if __name__ == "__main__":
    main()
