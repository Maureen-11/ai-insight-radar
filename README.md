# AI Insight Radar

面试展示型「AI 行业情报与模型评测平台」静态 Demo。

它把岗位要求拆成四个可展示模块：

- 情报雷达：公开来源、竞品动态、重要性评分、证据链。
- 模型评测：固定场景题的质量、引用准确率、延迟、成本对比。
- 访谈纪要：转写文本到观点、证据、待验证问题、行动项。
- 策略周报：把情报、评测与访谈整理成可讨论的战略判断。

## 运行

这是无构建依赖的静态网页，直接在本目录启动本地服务器即可：

```powershell
python -m http.server 4173
```

然后打开 <http://localhost:4173>。

也可以直接双击 `index.html` 查看，但本地服务器更接近正式部署环境。

## 目录

```text
index.html                 页面结构与展示数据入口
styles.css                 视觉系统、响应式布局与组件样式
app.js                     页面路由、过滤、评测切换、导出和交互
data/eval-scenarios.json   可替换为 EvalScope 真实运行的最小评测配置
```

## 数据与证据边界

- 页面中的信源链接指向公开厂商、社区或开源项目页面。
- 页面里的模型分数是“演示记录”，不是模型官方成绩，也不应作为采购结论。
- `data/eval-scenarios.json` 提供了三个可重复场景，接入真实模型时应保存原始回答、评分依据、延迟和成本。
- 访谈页使用“模拟输入”来展示结构，不伪造真实专家引语；正式作品应替换为已获授权的转写文本。

## 后续接入路线

1. 用 RSS、厂商公告页或 GitHub API 替换 `signals` 静态数组，并保存来源 URL、发布时间和抓取时间。
2. 用 EvalScope 运行 `data/eval-scenarios.json` 中的场景，补充真实模型适配器和结果 JSON。
3. 将 `Source`、`Entity`、`Event`、`ModelEvalRun`、`InterviewNote`、`Insight` 落到 SQLite 或 Postgres。
4. 用定时任务生成周报，并为每条结论保留可回溯的证据链。

## 许可证与第三方说明

本 Demo 的页面代码为本项目新增代码，未复制 `newsroom` 等未授权仓库的源代码。若后续引入 EvalScope 或 OpenCompass，应保留其 Apache-2.0 许可证与版权声明；没有明确许可证的仓库只能先作本地研究，不能直接公开再分发。
