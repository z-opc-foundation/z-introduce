# 项目总览

## 1. 项目简介

z-introduce 是 z-opc-foundation 组织的**只读展示工程**：把组织旗下全部登记仓库的实测元数据（README 摘要、模块树、语言分布、代码体量、发布状态、分层归属）汇总成一个可搜索的静态站点。

本仓不是业务仓。纯静态、**无后端、无构建步骤**、无运行时依赖：数据以 `window.ZDESC` 内联在 `assets/data.js`，页面不发任何 fetch 请求，因此 clone 下来双击 `index.html` 即可打开（`file://` 协议下不受 CORS 限制）。

**技术栈：** 原生 HTML + CSS + JavaScript（无框架、无打包器）+ Python 3 标准库（数据生成与自查脚本，零 pip 依赖）

## 2. 模块架构

```
z-introduce/
├── index.html               # 页面结构：hero / 架构分层 / 依赖 / 仓库总览 / 技术栈 / 关于
├── assets/
│   ├── style.css            # 深色技术风样式，七层用色相区分
│   ├── app.js               # 站点交互：渲染 / 搜索 / 筛选 / 详情抽屉
│   ├── data.js              # 生成产物：window.ZDESC = {...}（勿手改）
│   └── data.json            # 生成产物：同一份数据的 JSON 形态
└── tools/
    ├── generate.py          # 数据生成器：扫 lead manifest + 逐仓实测
    ├── check_secrets.py     # 上线前凭据自查（8 项正则）
    └── test_interactions.py # headless Chrome 交互回归（24 项断言）
```

## 3. 核心功能

### 3.1 数据生成（`tools/generate.py`，479 行）

- 从 lead 仓 `003_辅助能力/bootstrap/manifest.json` 取登记仓库清单与元信息，**过滤 `status == "retired"`** 的仓。
- 逐仓实测：README 首段摘要（460 字截断）、`pom.xml` 的 artifactId / version、子模块列表、语言分布、代码体量、git 提交数与最后提交日、是否有 `docker-compose.yml` / `Dockerfile`。
- 从 lead 仓 `003_辅助能力/maven-inventory/out/inventory.json` 现算跨仓依赖边，得到**被依赖 TOP3**（fan-out 最大的三个 owner）与**零被依赖清单**。
- 输出 `assets/data.js`（`window.ZDESC = ` 前缀）与 `assets/data.json`（同一 payload 的 JSON 形态）。
- 站内所有读数（仓数、代码文件数、提交数、已发中央数、公开仓数）一律由实测集现算，源码里不写死数字。

### 3.2 分层与归类

- `LAYERS` 手维护 7 层：组织治理（lead）/ L1 业务层 / L2 Boot 封装层 / L3 Agent 家族 / L3 中间件层 / 孵化层 / 前端与环境。
- `TAGS` 手维护 45 个仓的一句话定位。
- 生成器在输出前核对覆盖缺口：任一登记仓未归层或缺 TAGS 即 `sys.exit(1)`，拒绝产出「卡片有仓、分层表里没有」的半旧站点。

### 3.3 站内交互（`assets/app.js`，342 行）

- Hero 统计条：登记仓库 / 代码文件 / 子模块 / Git 提交。
- 架构分层区块、跨仓依赖区块（被依赖 TOP3 + 零被依赖）、仓库卡片网格、语言分布图、关于区块。
- 筛选：按层的筛选芯片；搜索：空格分词后对卡片文本做包含匹配，input 事件带防抖重渲染。
- 详情抽屉：展示单仓模块列表、语言条形图、仓库特征与注记（⚠️ 已知问题），Esc 关闭。
- 事件用委托绑在容器上，`#q` 输入、`#resetBtn` / `#clearQ` 重置、`#dClose` 关闭抽屉。

### 3.4 上线前自查与回归

- `tools/check_secrets.py`：对 `assets/data.json` 做 8 项正则自查（明文口令、密钥赋值、私钥块、云厂商 AK、内网 IP:PORT、JDBC 连接串、长 base64 串、Bearer 令牌），并额外列出外链与本地绝对路径，有命中即 `exit 1`。
- `tools/test_interactions.py`：把 `index.html` 注入探针脚本后用 headless Chrome 真实点击筛选、派发 input、打开抽屉、按 Esc，断言结果画成覆盖整页的 `<pre>` 后截图回读，共 24 项断言。

## 4. 对外集成 / 上下游

**上游（数据源，均在 lead 仓内，缺任一即生成器退出）：**

- `../z-opc-foundation-lead/003_辅助能力/bootstrap/manifest.json` —— 仓库清单、可见性、发布状态、purpose、language、size_kb、remote。
- `../z-opc-foundation-lead/003_辅助能力/maven-inventory/out/inventory.json` —— 跨仓 Maven 依赖边（`dep_edges`）与 `is_maven` 标记。

**下游：本仓无对外 HTTP 边界。** 纯静态文件，不监听端口、不发起任何外部请求（`check_secrets.py` 检出的外链只是展示用的仓地址文本），页面本身无追踪、断网可用。

**消费方：** 任何部署方用静态服务器托管本仓产物；使用者直接打开 `index.html` 即可浏览。

## 5. 技术特点

1. **数据内联而非运行时 fetch**：`assets/data.js` 顶格写 `window.ZDESC = {...}`，使 `file://` 直接双击打开不被 CORS 拦；`.gitignore` 明确声明这两个生成产物**必须入版本库**，排除它们会让 clone 后的仓库变成空站。
2. **零外部依赖**：三个脚本只用 Python 3 标准库（`argparse` / `json` / `os` / `re` / `subprocess` / `xml.etree`），无 pip 依赖、无 Node 构建链。
3. **数字现算**：仓数、代码文件数、提交数、被依赖 TOP3 全部来自 manifest + 逐仓实测，源码不写死读数。
4. **缺配置即失败**：`LAYERS` / `TAGS` 未覆盖新登记仓时生成器直接退出，不产出半旧站点。
5. **双形态产物**：同一份 payload 同时写成 `data.js`（`window.ZDESC` 赋值）与 `data.json`，后者便于二次加工。
6. **敏感信息前置自查**：`check_secrets.py` 8 条正则守住 `data.json`，防止 manifest 里的本地绝对路径或内网地址随站点发布。

## 6. 目录结构

本仓无 Java 包树，源码按「页面 / 样式 / 交互 / 工具脚本」四类组织：

```
z-introduce/
├── index.html            # 页面骨架与各 section 容器
├── assets/
│   ├── style.css         # 全部样式（深色技术风，七层色相）
│   ├── app.js            # 渲染（hero/分层/依赖/卡片/栈/关于）、搜索、筛选、详情抽屉
│   ├── data.js           # 生成产物（window.ZDESC）
│   └── data.json         # 生成产物（JSON 形态）
└── tools/
    ├── generate.py       # 数据生成器：manifest + 逐仓实测 → data.js / data.json
    ├── check_secrets.py  # 凭据 / 内网地址 / 本地路径自查
    └── test_interactions.py  # headless Chrome 交互回归探针
```

`tools/generate.py` 内部按职责分段：`LAYERS` / `TAGS` / `NOTES` 为手维护口径表，其后是取数辅助函数（`run` / `local` / `read_pom` / `first_paragraph` / `readme_title` / `count_code` / `submodules` / `frontend_hits` / `docs_of` / `git_info`），最后由 `main()` 组装 payload 并做覆盖缺口校验。
