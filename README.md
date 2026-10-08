# z-desc

> z-opc-foundation 组织的仓库展示站（当前登记 **46 仓**，2026-10-08 按 lead manifest 实测）。
> 纯静态，无后端、无构建步骤。

本仓不是业务仓，是**只读展示工程**：把组织旗下全部登记仓库的实测元数据
（README 摘要、模块树、语言分布、代码体量、发布状态、分层归属）汇总成一个
可搜索的静态站点。

## 快速开始

```bash
# 任选其一
python3 -m http.server 8000     # 然后打开 http://127.0.0.1:8000
open index.html                 # 直接双击也行（数据内联，无 fetch 限制）
```

## 重新生成数据

页面内容不是手写的，而是从同级目录的真实仓库扫出来的：

```bash
python3 tools/generate.py
```

它会读取 `../z-opc-foundation-lead/003_辅助能力/bootstrap/manifest.json`
拿到全仓事实表（当前 46 条），再逐仓实测 README / pom / 模块目录 / git 状态，
输出 `assets/data.js`（页面用）与 `assets/data.json`（便于二次加工）。

新增仓库后重跑一次即可，卡片会自动收录；但分层表 `LAYERS` 与一句话定位 `TAGS`
是手维护的，新仓没补进去时生成器**直接报错退出**，不会产出一个「卡片有仓、
分层表里没有」的半旧站点。

## 目录

```
index.html            页面结构
assets/style.css      样式（深色技术风，七层用色相区分）
assets/app.js         渲染 / 搜索 / 筛选 / 详情抽屉
assets/data.js        生成产物，勿手改
assets/data.json      同上，JSON 形态
tools/generate.py     数据生成器
tools/check_secrets.py  上线前凭据自查（8 项正则）
tools/test_interactions.py  浏览器交互回归（24 项断言）
```

## 自查

```bash
python3 tools/check_secrets.py       # 凭据/内网地址/本地路径，有发现则 exit 1
python3 tools/test_interactions.py   # 交互回归，结果写到截图里
```

`test_interactions.py` 用 headless Chrome 真实点击筛选按钮、往搜索框派发
input 事件、打开抽屉、按 Esc，结果渲染成整页文字后截图。
（注意：本机 Chrome 的 `--dump-dom` 会挂住，`--screenshot` 正常，故走截图回读。）
它补的是 Node 单测覆盖不到的部分 —— 事件委托、防抖重渲染、抽屉状态机
是否真的在浏览器里接线成功。

## 数据口径

遵循 lead 仓「数字必须现测」的原则，**不做任何推断**：

| 字段 | 来源 |
|---|---|
| 仓库清单、可见性、发布状态 | lead 仓 `manifest.json` |
| 分层归属（7 层） | lead 仓 README「全仓版本表」 |
| 摘要 | 各仓 `README.md` 首段 |
| 版本、构件坐标 | 各仓 `pom.xml` 现读 |
| 模块列表 | 各仓子目录中的 `pom.xml` / `build.gradle` |
| 语言分布、代码体量 | 逐目录遍历（排除 `target` / `node_modules`） |
| 提交数、最后提交日 | `git rev-list --count` / `git log -1` |
| 注记（⚠️ 已知问题） | lead 仓 2026-10-03 审计结论 |

`z-asset` 与 `z-ops` 没有 README 摘要（前者仓内无 README，后者本机未 clone），
站点会如实标注而非编造。

## 已知边界

- 快照反映 **2026-10-03** 的磁盘状态，不是实时数据。
- 可见性标记区分 public / private，但**页面不泄露任何 private 仓的源码**，
  只呈现 README 摘要这类本就在组织内公开的描述。
- 页面本身无追踪、无外部请求，断网可用。

## 许可

展示工程，MIT。源码版权归属各原仓。
