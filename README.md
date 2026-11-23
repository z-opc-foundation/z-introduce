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
