# z-introduce

> z-opc-foundation 组织的仓库展示站（当前登记 **58 仓**，按 lead manifest 非 retired 条目计）。
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

它会读取 `../z-opc-foundation-lead/003_辅助能力/bootstrap/manifest.json`，
排除 `status=retired` 后拿到全仓事实表（当前 58 条），再逐仓实测 README / pom / 模块目录 / git 状态，
输出 `assets/data.js`（页面用）与 `assets/data.json`（便于二次加工）。
依赖统计读取已有的 `../z-opc-foundation-lead/003_辅助能力/maven-inventory/out/inventory.json`；
快照缺失或未覆盖有效仓时拒绝生成，不自动执行扫描器或访问网络。

分层表 `LAYERS` 与一句话定位 `TAGS` 是手维护的。新增仓漏分类/定位、残留退役或未登记项、
重复分层、manifest 重复仓名都会在**写盘之前报错退出**，不会产出一个「卡片有仓、
分层表里没有」的半旧站点。`NOTES` 也不允许挂在有效集合以外。
生成器只读本地源文件并执行 `git rev-list` / `git log`，只写本站的两份数据产物，不拉取、不推送。

## 目录

```
index.html            页面结构
assets/style.css      样式（深色技术风，各展示分层用色相区分）
assets/app.js         渲染 / 搜索 / 筛选 / 详情抽屉
assets/data.js        生成产物，勿手改
assets/data.json      同上，JSON 形态
tools/generate.py     数据生成器
tools/check_secrets.py  上线前凭据自查（8 项正则）
tools/test_interactions.py  浏览器交互回归（31 项断言）
tools/test_readme_claims.py  README 定量主张自守卫（unittest）
```

## 自查

```bash
python3 tools/check_secrets.py       # 凭据/内网地址/本地路径，有发现则 exit 1
python3 tools/test_interactions.py   # 31 项真实 DOM 断言；失败或空白截图均 exit 1
python3 tools/test_readme_claims.py   # README 定量主张自守卫（unittest，改 README 数字即红）
```

`test_interactions.py` 需要本机 Chrome 与 Node 22+，通过独立 CDP 会话点击筛选按钮、
派发搜索 input 事件、打开抽屉并验证键盘焦点。31 项结果与固定基线逐项比较，
断言失败、漏项、浏览器异常或空白截图均返回非零。截图保留真实页面，不使用日志覆盖层；
测试只访问临时 loopback 静态服务，不访问外部业务接口。

## 数据口径

遵循 lead 仓「数字必须现测」的原则，**不做任何推断**：

| 字段 | 来源 |
|---|---|
| 仓库清单、可见性、发布状态 | lead 仓 `manifest.json` 非 retired 条目；历史登记字段，不是本次远端复测；可见性 null 保持未知，不计入公开仓 |
| 分层归属（8 层） | 本站 `LAYERS` 按各仓 README 维护的展示分组；lead 旧版本表已归档 |
| 摘要 | 各仓 `README.md` 首段 |
| 版本、构件坐标 | 各仓 `pom.xml` 现读 |
| 模块列表 | 各仓子目录中的 `pom.xml` / `build.gradle` |
| 语言分布、代码体量 | 逐目录遍历（排除 `target` / `node_modules`） |
| 提交数、最后提交日 | `git rev-list --count` / `git log -1` |
| 注记 | 当前本地 README 可定位的边界与材料差异；未复核的旧审计告警已移除 |
| 依赖 TOP / 零 Maven 跨仓依赖 | 已有 maven-inventory 快照，日期见 `inventoryGenerated`；榜单只列有效仓，退役消费者不计，依赖退役制品仍计出边；非 Maven 仓不推断为零依赖 |

`z-report`、`z-agent-proxy`、`z-kb` 已在 manifest 标为 retired，生成时整仓排除，
既不进卡片，也不进分层表与依赖榜单。`z-camuda` 仍按 manifest 收录；z-boot README
称其已归档的材料差异放在注记里，不擅自更改权威集合。

本次磁盘与有效 manifest 均为 58 仓，但原始名称集合不相等：
manifest 独有 `z-frontend-render`，磁盘独有 `z-render`。后者的 README 和 package.json
标识前者，故只做本地目录映射，卡片名与远端链接仍遵循 manifest；不改台账、不改目录。
同名目录优先；回退到别名时核对 npm 包身份，失败则拒绝生成。
当前映射后全部有效仓均已 clone 且有 README 摘要；以后摘要缺失时如实标注，不编造。

认知与数据安全是主题展示组，其中 `z-biz-security` 的工程定位仍是 L1 编排仓；
「孵化层」沿用站内名称，不代表没有 starter、未发布或未实现。

## 已知边界

- 本地扫描日期见 `assets/data.json.generated`（页面页脚同步显示）；manifest 与依赖快照有各自的更新周期，不是实时数据。
- 可见性标记区分 public / private，但**页面不泄露任何 private 仓的源码**，
  只呈现 README 摘要这类本就在组织内公开的描述。
- 页面本身无追踪、无外部请求，断网可用。

## 文档目录

本项目文档统一收口在 `_doc/` 下（八类固定编号表，桶按需存在）:

- [`_doc/001_arch/`](_doc/001_arch/) — 架构、接口、DB schema、协议、路线图

## 许可

展示工程，MIT。源码版权归属各原仓。

---

<!-- z-opc-foundation-sibling-registry:v1 -->
## 🔗 兄弟仓全景（z-opc-foundation 组织）

本仓隶属于 [z-opc-foundation](https://github.com/orgs/z-opc-foundation/repositories) 组织——一人公司基座的全部自研件（现存 61 仓，含私有仓；口径 2026-11-24 GitHub org API 实读）。

| 仓 | 一句话说明 |
|---|---|
| [z-agent](https://github.com/z-opc-foundation/z-agent) | 云端 Agent 平台的库与 starter——ReAct/Plan 实现 + 注册中心 + REST 网关 + 只读控制面 |
| [z-agent-kernel](https://github.com/z-opc-foundation/z-agent-kernel) | Agent 框架基座——消息/工具/记忆/provider/会话 SPI + 轻量默认实现（纯 POJO 无 Spring） |
| [z-asset](https://github.com/z-opc-foundation/z-asset) | 企业资产台账——实物设备全生命周期 + 域名/证书/许可到期提醒 |
| [z-audit](https://github.com/z-opc-foundation/z-audit) | 审计与合规留痕——事件模型 + 哈希链 + 事件出口 SPI + 留存期策略 |
| [z-biz](https://github.com/z-opc-foundation/z-biz) | 商务外壳域——客户/合同/票据/对账四聚合 |
| [z-biz-erp](https://github.com/z-opc-foundation/z-biz-erp) | 进销存 ERP——商品/客商/采购/销售/库存流水/应收应付核销（z-biz 业务线） |
| [z-biz-security](https://github.com/z-opc-foundation/z-biz-security) | 业务数据安全防护入口——场景化策略注册 + 安全线四段流水线对外编排 |
| [z-boot](https://github.com/z-opc-foundation/z-boot) | Spring Boot Starter 聚合仓 + 版本权威（火车制）——唯一消费入口 z-boot-parent |
| [z-bot](https://github.com/z-opc-foundation/z-bot) | 本地 agent 应用——终端 CLI + HTTP/SSE web 控制台 + 多通道 gateway（飞书/钉钉/webhook） |
| [z-cache](https://github.com/z-opc-foundation/z-cache) | RESP2 协议兼容的分布式内存缓存——Java 8 + Netty，Redis 客户端零修改直连 |
| [z-camuda](https://github.com/z-opc-foundation/z-camuda) | 【已退役·归档】基于 Camunda 的工作流封装层（原 z-wf 改名，与现行 z-wf 无共同历史） |
| [z-cognition](https://github.com/z-opc-foundation/z-cognition) | 业务认知域/认知舱——术语/概念/证据链 + memory/kb/ontology 渐进式模块 |
| [z-config](https://github.com/z-opc-foundation/z-config) | 分布式配置中心 + 服务注册中心（类 Nacos）——Netty 长连接推送 + React 控制台 |
| [z-ctc](https://github.com/z-opc-foundation/z-ctc) | 4A 中心——认证/授权/账户/审计，多租户 JWT + SSO 跨子域 |
| [z-dms](https://github.com/z-opc-foundation/z-dms) | 数据源管控底座——统一登记、统一建池、统一探活、变更统一推送 |
| [z-env](https://github.com/z-opc-foundation/z-env) | 本地中间件与基础设施环境——31 个 docker-compose 场景 + make 一键运维 |
| [z-etl](https://github.com/z-opc-foundation/z-etl) | ETL 引擎——DataX 式线性作业 + Flink 式 DAG 流管道（键控状态/水位/窗口） |
| [z-ext](https://github.com/z-opc-foundation/z-ext) | Java 扩展点框架——@ExtPoint/@ExtImpl 运行期选实现，五档侵入方式 |
| [z-frontend-common](https://github.com/z-opc-foundation/z-frontend-common) | 全仓共享前端基座——AppLayout/LoginPage 等前端规范的唯一承载 |
| [z-frontend-markdown](https://github.com/z-opc-foundation/z-frontend-markdown) | Markdown 通用共享组件包（npm）——MarkdownLiveEditor/NoteMarkdown/MermaidBlock 单一真源 |
| [z-frontend-render](https://github.com/z-opc-foundation/z-frontend-render) | 平台共享前端渲染引擎——后端 schema 是唯一事实源，报表与低代码共用 |
| [z-graph](https://github.com/z-opc-foundation/z-graph) | 独立图数据库——MVCC 版本链存储 + OpenCypher 子集 + Bolt 风格协议 + React 控制台 |
| [z-gw](https://github.com/z-opc-foundation/z-gw) | 自研高性能 API 网关——Netty 手写运行时，Route/Predicate/Filter 模型可嵌 Spring Boot |
| [z-indexer](https://github.com/z-opc-foundation/z-indexer) | 代码索引服务——仓库注册表 + 定时重建索引 + 符号/调用链查询 |
| [z-introduce](https://github.com/z-opc-foundation/z-introduce) | 组织仓库展示站——全仓实测元数据汇总成可搜索静态站点 **（本仓）** |
| [z-lc](https://github.com/z-opc-foundation/z-lc) | 低代码平台——DB 驱动通用 CRUD 引擎 + 报表/模型设计框架 |
| [z-llm-agent](https://github.com/z-opc-foundation/z-llm-agent) | CLI Agent 服务化——把本机 CLI agent（CC/Hermes/Qoder 等）暴露成 OpenAI 兼容对话 API |
| [z-llm-gateway](https://github.com/z-opc-foundation/z-llm-gateway) | LLM 网关——OpenAI/Anthropic 双协议面 + 多 vendor 凭据池、限流与 token 记账 |
| [z-llm-msghub](https://github.com/z-opc-foundation/z-llm-msghub) | msgHub 中心消息路由——WebSocket 中心枢纽 + Agent 侧客户端 SDK |
| [z-mask](https://github.com/z-opc-foundation/z-mask) | 脱敏与遮蔽引擎——按敏感命中位置遮蔽，策略即数据 |
| [z-mcp](https://github.com/z-opc-foundation/z-mcp) | MCP 服务端 + 上游聚合网关——Java 8 手写协议层，Spring Boot 自动装配 |
| [z-meta](https://github.com/z-opc-foundation/z-meta) | 元数据管理平台——租户/应用/接口清单登记 + @BizModel 业务模型采集 |
| [z-mill](https://github.com/z-opc-foundation/z-mill) | 资料磨坊——全格式文档转 Markdown/JSON/纯文本/HTML（对标 MinerU） |
| [z-mist](https://github.com/z-opc-foundation/z-mist) | KMS 分布式密钥/秘密管理平台——集中加密存储 + Netty 协议 + starter 嵌入 |
| [z-mq](https://github.com/z-opc-foundation/z-mq) | 自研分布式消息队列——NameServer+Broker+Store，形状对标 RocketMQ、自有 Netty 协议 |
| [z-msg](https://github.com/z-opc-foundation/z-msg) | 多通道消息 + WebSocket 实时下发基础设施——短信/邮件/站内信/Webhook/IM 平台 |
| [z-observer](https://github.com/z-opc-foundation/z-observer) | 可观测性域——指标/日志/链路 + 告警引擎 |
| [z-opc](https://github.com/z-opc-foundation/z-opc) | 一人公司统一后端+统一前端——单 JVM all-in-one 承载协作/Agent/RPA/交易/资产等业务域与自研中间件 |
| [z-opc-foundation-lead](https://github.com/z-opc-foundation/z-opc-foundation-lead) | 组织治理大脑——事实表、强制规范、跨仓工具集、新机器恢复钥匙（本清单权威持有处） |
| [z-opcs](https://github.com/z-opc-foundation/z-opcs) | 任务撮合/服务市场——用户付费发布诉求，持有者接单完成，金额自动瓜分 |
| [z-ops](https://github.com/z-opc-foundation/z-ops) | 个人公司运维平台——部署单元/镜像构建/WebShell/K8s 巡检 + Ops Agent 执行器 |
| [z-oss](https://github.com/z-opc-foundation/z-oss) | 对象存储服务——自持 local 后端 + aliyun/s3 对接层，starter 注入 OssTemplate |
| [z-product](https://github.com/z-opc-foundation/z-product) | 产品设计信息汇总仓（开发域 PM 工件） |
| [z-qa](https://github.com/z-opc-foundation/z-qa) | 步骤式 API 链路测试平台——用例/计划/执行/报告/质量看板（对标 TestRail·MeterSphere） |
| [z-rpa](https://github.com/z-opc-foundation/z-rpa) | RPA 产品皮——应用市场/需求中心（执行归 z-script，触发归 z-schedule） |
| [z-rpc](https://github.com/z-opc-foundation/z-rpc) | Java 8 + Netty RPC 框架——微内核 + SPI 插件化，形状参照 Dubbo/gRPC |
| [z-schedule](https://github.com/z-opc-foundation/z-schedule) | 分布式任务调度中枢（对标 XXL-Job）——选主 + 时间环排期，starter 嵌入宿主 |
| [z-script](https://github.com/z-opc-foundation/z-script) | 多 DSL 脚本平台 + Mock 平台——沙箱执行/版本灰度/可注册 MCP Tool，starter 内嵌 |
| [z-security](https://github.com/z-opc-foundation/z-security) | 数据安全域编排层——场景→策略→识别→脱敏→水印→审计 四段流水线编排 |
| [z-sense](https://github.com/z-opc-foundation/z-sense) | 敏感识别与分类分级引擎——数据安全线底座（规则目录 + 可插拔识别器 + 分类分级） |
| [z-skill](https://github.com/z-opc-foundation/z-skill) | Skill 平台聚合器——归一化各家 Skill 形状，再按各家 API 形状发回 |
| [z-surl](https://github.com/z-opc-foundation/z-surl) | 短网址服务——短码生成/解析/命中统计，starter 一行集成 |
| [z-task](https://github.com/z-opc-foundation/z-task) | 任务协作平台——项目空间/看板/任务卡片（看板范式，对标 Trello·Teambition） |
| [z-team](https://github.com/z-opc-foundation/z-team) | 数字员工协同域——全栈独立仓，自 z-opc 毕业 |
| [z-trade](https://github.com/z-opc-foundation/z-trade) | 交易域独立仓——自 z-opc reactor 迁出 |
| [z-util](https://github.com/z-opc-foundation/z-util) | 底层 Java 工具库——89 个模块 POM，Java 8/17 口径，按需引用按需升级 |
| [z-vector](https://github.com/z-opc-foundation/z-vector) | 自研 Java 向量数据库——嵌入式+可独立部署，ANN+Payload 过滤，兼容 Qdrant REST |
| [z-voice-demo](https://github.com/z-opc-foundation/z-voice-demo) | 语音链路 demo——流式识别→kernel LLM→流式 TTS→可打断 的契约验证实现 |
| [z-watermark](https://github.com/z-opc-foundation/z-watermark) | 水印引擎——显式文字/图片隐写/盲水印，三种技术成对「打+验」 |
| [z-webide](https://github.com/z-opc-foundation/z-webide) | 企业级 WebIDE 后端——Git 仓/共享目录秒变 code-server 实例，全生命周期管理 |
| [z-wf](https://github.com/z-opc-foundation/z-wf) | 自研流程引擎——不依赖 Camunda/Flowable，定义层与运行时全自研 |

**已退役仓**（迁至 [z-trash](https://github.com/z-trash) 组织，archived 只读）：

| 仓 | 说明 |
|---|---|
| [z-agent-proxy](https://github.com/z-trash/z-agent-proxy) | 三方 coding agent 适配代理（Aider/Cursor → kernel Agent SPI），2026-10-26 退役 |
| [z-kb](https://github.com/z-trash/z-kb) | 自研知识库系统（对标 LightRAG/RAGFlow），2026-11 并入 z-cognition 认知舱后退役 |
| [z-ontology](https://github.com/z-trash/z-ontology) | 本体层（TBox/ABox/RDFS 推理），并入 z-cognition 后退役 |

另有 [z-report](https://github.com/z-opc-foundation/z-report)（报表域，2026-10-11 撤销并入 z-lc（远端已删除））。

总清单权威持有处在 [z-opc-foundation-lead](https://github.com/z-opc-foundation/z-opc-foundation-lead) `008_组织规范/005_兄弟仓清单.md`。
