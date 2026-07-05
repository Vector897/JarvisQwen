# JarvisQwen — 知识工作的自动驾驶控制平面,跑在 Qwen Cloud 上

> 赛道:Autopilot Agent · Global AI Hackathon (Qwen Cloud) · [English →](README.md)

大部分知识工作是同一个循环:**盯信息源 → 筛出重要的 → 深度处理 → 输出简报 → 从反馈中学习**。科研人盯论文、分析师盯竞品、法务盯法规、安全团队盯 CVE——所有人每天手动跑这个循环。JarvisQwen 把它变成 7×24 自主运行的自动驾驶,通过成本感知的三级路由指挥 Qwen 模型全家桶(`$0 规则层` → `qwen3.6-flash` → `qwen3.7-max`),让每个 token 都花在"能干这活的最便宜模型"上。本版本内置这个模式下最深的垂直场景:**科研文献跟踪**(arXiv 每天 500+ 篇,朴素自动化最烧钱的场景)。同一引擎换连接器+提示词即可跑专利监控、竞品情报、法规跟踪、安全通告分诊(模板化)。

**控制平面(便宜、常驻)管理执行平面(昂贵、按需)**——类比 Kubernetes 之于容器。

## 核心特性

- 🔁 **7×24 无人值守**:订阅关键词后自动轮询 arXiv → 去重 → 初筛(flash)→ 下载归档 → 深度总结(max)→ 晨间简报,你的笔记本可以关机
- 💰 **成本控制**:三级模型路由(规则层 $0 / flash 初筛 / max 精读)+ 语义缓存 + 置信度级联 + 日预算硬熔断 + 按 Qwen 官方价目表逐笔精确记账,单主题日成本约 **$0.30**(朴素全前沿方案的 1/30)
- 🔌 **BYOK**:粘贴 Qwen Cloud API Key 即可运行(自动格式修正、厂商识别、实时探活、Fernet 加密存储);兼容其他厂商与任意 OpenAI 兼容端点
- 🧯 **弹性容错**:检查点断点续跑(崩溃不重复付费)、指数退避 + 断路器 + 模型 fallback 链(max→plus→flash)、僵尸任务看门狗
- 🔒 **安全**:出境 PII 三层脱敏网关(正则/熵/NER,占位符替换回程还原)、提示注入隔离、append-only 审计日志
- ✅ **人类在环**:高危操作进审批队列,批准后从检查点无缝继续
- 🧠 **记忆系统**:情节记忆 → 夜间低峰整合为语义记忆;你标记"重要/忽略"的反馈回流优化后续初筛
- 📱 **随处可用**:响应式 PWA 控制台(React Flow 流水线视图 + 预算仪表盘 + 审批 + 审计),中英双语,深色模式

## 快速开始

### 本地(零 Key 可跑)

```bash
cd server
python -m venv .venv && .venv/bin/pip install -e ".[dev]" litellm
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000

cd web
npm install && npm run dev                # http://localhost:3000
```

未配 Key 时运行在 **dry-run 模式**:全流程可跑通、LLM 返回模拟响应、零费用。设置页粘贴 Qwen Cloud Key 即切换真实调用。

### 阿里云 ECS 部署

```bash
curl -fsSL https://raw.githubusercontent.com/Vector897/JarvisQwen/main/install.sh | bash
```

浏览器打开 `http://<ECS IP>:3000` → 用 `data/admin_password.txt` 里的密码登录 → 设置页粘贴 DASHSCOPE_API_KEY → 订阅页添加研究关键词。所有状态在 `./data` 目录,迁移 = 拷贝 + compose up。

## 架构

所有 LLM 请求经过唯一出境通道 [`server/app/core/router/llm.py`](server/app/core/router/llm.py):**脱敏 → 语义缓存 → 预算检查 → 三级路由 → 弹性调用(退避/断路器/fallback)→ 审计记账**,任何 prompt 都无法绕过安全与计费。架构图与 Qwen Cloud 集成点详见 [英文 README](README.md#architecture)。

## 测试

```bash
cd server
.venv/bin/python -m pytest          # 路由/脱敏/断路器/检查点/预算 单测
.venv/bin/python tests/smoke_e2e.py # 全链路冒烟
```

## 许可证

[MIT](LICENSE)
