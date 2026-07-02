# AAOS — AI Agent Operating System

云边协同的 Agent 控制平面：一个跑在免费 CPU 云主机上的 7×24 调度守护进程，替你指挥昂贵的云端大模型完成学术文献的检索、归档、总结与简报，而调度本身几乎零成本。

**控制平面（便宜、常驻）管理执行平面（昂贵、按需）** ——类比 Kubernetes 之于容器。

## 核心特性

- 🔁 **7×24 无人值守**：订阅关键词后自动轮询 arXiv → 去重 → 初筛 → 下载归档 → 深度总结 → 晨间简报，你的笔记本可以关机
- 💰 **成本控制**：三级模型路由（规则层 0 成本 / 轻量层 / 前沿层）+ 语义缓存 + 日预算硬熔断 + 每笔调用审计记账
- 🔌 **BYOK**：粘贴任意厂商 API Key 即可运行（自动格式修正、厂商识别、实时探活）；支持任意 OpenAI 兼容端点
- 🧯 **弹性容错**：检查点断点续跑（崩溃不重复付费）、指数退避+断路器+模型 fallback 链、僵尸任务看门狗
- 🔒 **安全**：出境 PII 脱敏网关（占位符替换回程还原）、提示注入隔离、append-only 审计日志、Key 加密存储
- ✅ **人类在环**：高危操作进审批队列，批准后从检查点无缝继续
- 📱 **随处可用**：响应式 Web 控制台（React Flow 流水线视图 + 进度条 + ETA），前端可托管 Vercel，手机可用

## 快速开始

### 方式一：一键部署到云 VM（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/Vector897/AAOS/main/install.sh | bash
```

浏览器打开 `http://<VM IP>:3000` → 用 `data/admin_password.txt` 里的密码登录 → 设置页粘贴 API Key → 订阅页添加研究关键词。完成。

### 方式二：本地开发

```bash
# 后端
cd server
python -m venv .venv && .venv/bin/pip install -e ".[dev]" litellm
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000

# 前端（另一个终端）
cd web
npm install && npm run dev                # http://localhost:3000
```

未配置 API Key 时系统运行在 **dry-run 模式**：全流程可跑通，LLM 返回模拟响应，零费用。

### 方式三：前端上 Vercel（手机公网访问最方便）

1. Fork 本仓库，Vercel 导入并把 Root Directory 设为 `web/`
2. Vercel 环境变量设 `BACKEND_URL=https://你的VM域名`（VM 上只跑 `server`）
3. push 即部署；数据与 Key 始终在你自己的 VM 上

## 架构

```
浏览器（任意设备） ── HTTPS ──> Next.js 控制台
                                    │ /api/* rewrites（同源）
                              FastAPI 控制平面（免费 CPU VM）
                              ├─ 调度器：队列/租约/看门狗/订阅轮询
                              ├─ 任务引擎：检查点续跑/ETA/Artifacts/审批中断
                              ├─ llm.py 统一出境调用点：
                              │    脱敏→缓存→预算→路由→弹性(退避/断路器/fallback)→审计
                              └─ SQLite（任务/论文/记忆/审计，单文件可迁移）
                                    │ 仅在必要时刻
                              云端大模型 API（Claude / GPT / Gemini / DeepSeek / 自定义端点）
```

详细设计见仓库外的《项目架构.md》《项目代码架构.md》（调研报告映射、六大功能域实现方案）。

## 测试

```bash
cd server
.venv/bin/python -m pytest          # 核心路径单测（路由/脱敏/断路器/检查点/预算）
.venv/bin/python tests/smoke_e2e.py # 全链路冒烟（启动→登录→任务→流水线→审计）
```

## 许可证

MIT
