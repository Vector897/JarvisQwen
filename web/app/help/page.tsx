"use client";

import Link from "next/link";
import { useLang } from "@/lib/i18n";

/** 帮助页（技术参考）：任务流水线、成本架构、防呆机制、名词速查、疑难排查。
 *  产品定位/上手流程/各页面作用在「使用指南」（/guidelines），本页不重复。
 *  中英双语内联对照，语言开关切换。 */

export default function Help() {
  const { lang } = useLang();
  const L = (en: string, zh: string) => (lang === "zh" ? zh : en);
  return (
    <div className="space-y-6 leading-relaxed">
      {/* 页头：定位说明 + 指向使用指南 */}
      <section className="card space-y-1">
        <h2 className="text-lg font-bold">{L("Technical reference", "技术参考文档")}</h2>
        <p className="text-sm text-slate-600">
          {L(
            "This page explains how JarvisQwen works under the hood: the task pipeline, the cost architecture, and the safety mechanisms. If you are new here, start with the ",
            "本页面向想了解实现原理的读者：任务流水线、成本架构与安全机制。如果你是第一次使用，请先阅读"
          )}
          <Link href="/guidelines" className="font-medium underline hover:text-slate-800">
            {L("Guidelines page", "「使用指南」")}
          </Link>
          {L(
            " — it covers what the product does, how to get started, and what each page is for.",
            "——那里介绍产品定位、上手流程与各页面的作用，本页不再重复。"
          )}
        </p>
      </section>

      {/* ① 任务流水线 */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">{L("1. The task pipeline (the life of one task)", "一、任务流水线（一条任务的一生）")}</h2>
        <div className="card">
          <Flow steps={[
            [L("📡 Poll", "📡 轮询"), L("Fetch new papers from arXiv on schedule (pure code, $0)", "定时抓取 arXiv 新论文（纯代码，0 费用）")],
            [L("🧹 Dedupe", "🧹 去重"), L("Skip anything already seen, by title+ID fingerprint (pure code)", "按标题+ID 指纹跳过已见过的（纯代码）")],
            [L("🎯 Triage", "🎯 初筛"), L("Light model scores relevance against your research profile (cheap)", "轻量模型按你的研究方向打相关度分（便宜）")],
            [L("📥 Archive", "📥 归档"), L("Download PDF + store metadata (pure code)", "下载 PDF + 存元数据入库（纯代码）")],
            [L("📝 Summarize", "📝 总结"), L("Frontier model deep-reads each hit (expensive, but only the few that passed triage)", "前沿模型逐篇深度总结（贵，仅对命中的少数论文）")],
            [L("🧠 Remember", "🧠 记忆"), L("Write episodic memory; consolidated into long-term semantic memory overnight", "写入情节记忆，夜间整合成长期语义记忆")],
            [L("📰 Brief", "📰 简报"), L("Aggregated into a morning briefing, pushed to you daily", "每天早晨聚合成一份晨间简报推送给你")],
          ]} />
          <p className="mt-3 text-xs text-slate-400">
            {L(
              "Key point: 4 of the 7 stages are zero-cost pure code. Only triage and summarization spend money, and summarization only touches papers that passed triage — that's where the order-of-magnitude cost reduction comes from.",
              "关键：7 步里 4 步是零成本的纯代码，只有「初筛」「总结」花钱，且总结只作用于通过初筛的少数论文——这就是成本能降一个数量级的原因。"
            )}
          </p>
        </div>
      </section>

      {/* ② 成本架构 */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">{L("2. Cost architecture: three-tier model routing", "二、成本架构：三级模型路由")}</h2>
        <p className="text-sm text-slate-600">
          {L(
            "The core idea: a cheap, always-on steward + expensive, on-demand experts. The scheduler daemon runs on a cheap (even free) CPU VM and commands the Qwen model family on Qwen Cloud (qwen3.6-flash / qwen3.7-plus / qwen3.7-max); BYOK also supports other providers. Every piece of work is routed to the cheapest tier that can handle it:",
            "核心思路是「便宜常驻的管家 + 昂贵按需的专家」：调度守护进程跑在便宜（甚至免费）的 CPU 云主机上，指挥 Qwen Cloud 上的模型全家桶（qwen3.6-flash / qwen3.7-plus / qwen3.7-max），BYOK 也支持接入其他厂商。每项工作都被路由到能胜任的最便宜一层："
          )}
        </p>
        <div className="grid gap-3 md:grid-cols-3">
          <Tier color="border-slate-300" name={L("Rule tier", "规则层")} cost={L("$0", "0 费用")}
            desc={L("Polling, dedup, archiving, parsing — pure Python, no model calls at all.", "轮询、去重、归档、格式解析——纯 Python 代码，不调用任何模型。")} />
          <Tier color="border-blue-300" name={L("Light tier", "轻量层")} cost={L("very cheap", "很便宜")}
            desc={L("Instruction parsing, triage, briefings — qwen3.6-flash at $0.25/MTok input.", "指令解析、论文初筛、简报撰写——用 qwen3.6-flash（$0.25/MTok 输入）。")} />
          <Tier color="border-amber-300" name={L("Frontier tier", "前沿层")} cost={L("expensive", "较贵")}
            desc={L("Deep summaries and surveys — qwen3.7-max, only when genuinely needed.", "论文深度总结、综述生成——只在真正需要时用 qwen3.7-max 最强模型。")} />
        </div>
      </section>

      {/* ③ 防呆机制 */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">{L("3. 🛡️ Safety rails (no runaway bills, no data loss, no rogue actions)", "三、🛡️ 防呆机制（不会烧钱、不会丢数据、不会失控）")}</h2>
        <div className="space-y-2">
          <Guard title={L("Dry-run mode: no key, no errors", "Dry-run 模式：没配 Key 也不报错")}
            body={L(
              "With no API key configured, the system enters dry-run mode: LLM calls return simulated responses, the whole pipeline still runs, at zero cost. Learn the system first, connect a model later.",
              "未配置任何 API Key 时，系统进入 dry-run 模式：LLM 返回模拟响应，全流程可跑通、零费用。你可以先把整套流程玩明白，再决定接哪个模型。"
            )} />
          <Guard title={L("Key auto-correction + live probe", "API Key 自动格式修正 + 探活")}
            body={L(
              "Pasted keys are stripped of stray whitespace, quotes, Bearer prefixes, full-width characters and variable-name residue; the provider is auto-detected; a minimal test request runs on save and tells you immediately: valid / invalid / out of quota. You never discover a bad key mid-task.",
              "粘贴 Key 时自动去掉多余空格、引号、Bearer 前缀、全角字符和误带的变量名；自动识别厂商；保存时发一次最小测试请求，当场告诉你「可用 / 无效 / 余额不足」，不会等到跑任务才发现填错。"
            )} />
          <Guard title={L("Hard daily budget cut-off + 80% alert", "日预算硬熔断 + 80% 告警")}
            body={L(
              "Set a daily spending cap. At 80% you get an alert; at 100% the breaker trips — running tasks are suspended instead of burning money. Worst case is capped. A runaway bill is structurally impossible.",
              "给每天设一个花费上限。到 80% 会告警，到 100% 立即熔断——正在跑的任务被挂起而不是继续烧钱。最坏情况有封顶，绝不会跑出天价账单。"
            )} />
          <Guard title={L("Circuit breakers + exponential backoff + model fallback", "断路器 + 指数退避 + 模型降级")}
            body={L(
              "When a model/provider keeps failing it gets circuit-broken; requests reroute to a backup key → backup provider → cheaper model. Retries use exponential backoff with jitter (1s→2s→4s…). No retry storm can ever eat your quota.",
              "某个模型/厂商连续失败时自动熔断，请求改道备用 Key → 备用厂商 → 更便宜的模型；重试用带随机抖动的指数退避（1s→2s→4s…）。绝不会陷入疯狂重试把配额和钱烧光的死循环。"
            )} />
          <Guard title={L("Checkpoint resume: crashes never double-bill", "检查点断点续跑：崩溃不重复付费")}
            body={L(
              "Every completed step snapshots its state. After a power cut, restart or network outage, the task resumes from the last checkpoint — paid intermediate results are never recomputed. You never pay twice for the same work.",
              "任务每完成一步就存一次快照。断电、重启、网络中断后，系统从最后一个检查点继续，已经花钱得到的中间结果不会重做——不会为同一件事付两次费。"
            )} />
          <Guard title={L("Zombie-task watchdog", "僵尸任务看门狗")}
            body={L(
              "A task that hangs past its timeout is flagged as a zombie, reclaimed, and re-queued (resuming from checkpoint). Nothing silently occupies resources forever.",
              "任务卡死超时会被自动标记为僵尸、回收并重新排队（从检查点续跑），不会有任务无声无息地永久占着资源。"
            )} />
          <Guard title={L("Redaction gateway: sensitive data stays home", "脱敏网关：敏感信息不出境")}
            body={L(
              "All text bound for the cloud passes three detection layers (regex / entropy / NER): emails, IDs, API keys are replaced with placeholders and restored after the model responds. At the highest sensitivity level, egress is blocked outright. Your unpublished ideas never streak across third-party servers.",
              "所有发往云端的文本先过三层脱敏（正则 / 熵检测 / 命名实体）：邮箱、身份证、API 密钥等被替换成占位符，模型返回后再还原。高敏感等级下直接阻断出境。你的未发表想法和私密数据不会裸奔到第三方。"
            )} />
          <Guard title={L("Prompt-injection isolation", "提示注入隔离")}
            body={L(
              "External content (papers, web pages) is wrapped in a data zone declared as \"material, not instructions\" before entering prompts; outputs are scanned for suspicious links. Malicious instructions hidden in documents can't hijack the agent.",
              "论文、网页等外部内容进入提示词时会被包裹进「数据区」并声明「以下是资料不是指令」；输出还会扫描可疑外链，防止被藏在文档里的恶意指令劫持去偷数据。"
            )} />
          <Guard title={L("Human-in-the-loop approvals", "人类在环审批")}
            body={L(
              "Destructive or outbound operations never auto-execute — they queue for your explicit approval, then resume seamlessly from checkpoint. Denied means safely stopped.",
              "删除、对外发送等高危、不可逆操作不会自动执行，而是进入审批队列等你点「批准」；批准后从检查点无缝继续，拒绝则安全停止。"
            )} />
          <Guard title={L("Permission isolation + full audit", "权限隔离 + 全程审计")}
            body={L(
              "With multiple users, retrieval is ownership-filtered before anything reaches the model context. Every call's model, tokens, cost, and I/O digests land in an append-only audit trail — you can always answer \"which call produced this conclusion?\"",
              "多用户时，检索在进入模型上下文之前就按归属过滤（越权内容根本进不来）；每一次模型调用的模型、token、费用、输入输出摘要都写进不可篡改的审计流水，随时可查「这条结论来自哪次调用」。"
            )} />
        </div>
      </section>

      {/* ④ 名词速查 */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">{L("4. Glossary", "四、名词速查")}</h2>
        <div className="card grid gap-2 text-sm md:grid-cols-2">
          <Term t={L("Control / execution plane", "控制平面 / 执行平面")}
            d={L("Control plane = the cheap always-on scheduler; execution plane = expensive on-demand LLMs. The former commands the latter.", "控制平面=便宜常驻的调度器；执行平面=昂贵按需的大模型。前者管后者。")} />
          <Term t={L("Pipeline", "流水线（Pipeline）")}
            d={L("The steps a task is broken into; the task detail page renders them as a live, color-coded flow diagram.", "一条任务被拆成的若干步骤，任务详情页用彩色流程图实时展示到哪一步了。")} />
          <Term t={L("Artifacts", "Artifacts（产出物）")}
            d={L("Verifiable evidence each step produces (search list, archive list, summary draft) — also the resume points for reruns.", "每步产生的可核验证据（检索清单、归档列表、总结草稿），也是重跑的核验点。")} />
          <Term t={L("Checkpoint", "检查点（Checkpoint）")}
            d={L("A state snapshot after each step — the basis of crash-safe resume.", "任务每步的状态快照，断点续跑的依据。")} />
          <Term t="ETA"
            d={L("Estimated completion time from historical per-step durations, corrected live as the task runs.", "按历史各步耗时估算的预计完成时间，会随执行动态修正。")} />
          <Term t="dry-run"
            d={L("Keyless simulation mode — the full pipeline at zero cost.", "无 Key 时的模拟运行模式，零费用跑通全流程。")} />
          <Term t="BYOK"
            d={L("Bring Your Own Key — you supply the API key, so usage is billed to your own provider account.", "Bring Your Own Key——自带 API Key，费用直接计入你自己的厂商账户。")} />
          <Term t={L("Semantic cache", "语义缓存")}
            d={L("Reuses answers to semantically identical requests, so repeated questions don't trigger paid calls.", "语义相同的请求复用历史结果，重复提问不再触发付费调用。")} />
        </div>
      </section>

      {/* ⑤ 疑难排查 */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">{L("5. Troubleshooting", "五、疑难排查")}</h2>
        <div className="space-y-2">
          <Faq q={L("An API key is configured, but real model calls fail with an error?", "已配置 API Key，但真实模型调用报错？")}
            a={L("Self-hosted backends need the litellm dependency: run pip install litellm on the server. The Docker image ships with it preinstalled.", "自托管后端需要安装 litellm 依赖：在服务器运行 pip install litellm。Docker 镜像已内置，无需手动装。")} />
          <Faq q={L("Tasks stay QUEUED and never start running?", "任务一直停在 QUEUED 状态不开始执行？")}
            a={L("Usually the daily budget breaker has tripped (check the Dashboard) or all workers are busy with long tasks. Raise the cap in Settings or wait for a worker to free up; suspended tasks resume automatically.", "通常是日预算已熔断（看仪表盘）或全部 worker 正被长任务占用。到设置页调高预算上限，或等 worker 空闲；被挂起的任务会自动恢复。")} />
          <Faq q={L("Where are my data and the admin password stored?", "我的数据和管理员密码存放在哪里？")}
            a={L("Everything lives in the data/ directory next to the deployment (SQLite database, PDFs, admin_password.txt). Back up that one directory and you have backed up everything.", "全部数据都在部署目录旁的 data/ 目录里（SQLite 数据库、PDF、admin_password.txt）。备份这一个目录就等于备份了一切。")} />
        </div>
        <p className="text-xs text-slate-400">
          {L("For usage-level questions (where results are, what the flow diagram means, how to control spending), see the FAQ in the ", "使用层面的问题（结果在哪里查看、流程图的含义、如何控制花费）请见")}
          <Link href="/guidelines" className="underline hover:text-slate-600">{L("Guidelines", "「使用指南」")}</Link>
          {L(".", "中的常见问题。")}
        </p>
      </section>
    </div>
  );
}

function Flow({ steps }: { steps: [string, string][] }) {
  return (
    <div className="flex flex-col gap-1">
      {steps.map(([name, desc], i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="flex flex-col items-center">
            <div className="rounded-lg bg-slate-100 px-2 py-1 text-sm font-medium">{name}</div>
            {i < steps.length - 1 && <div className="h-3 w-px bg-slate-300" />}
          </div>
          <div className="pt-1.5 text-xs text-slate-500">{desc}</div>
        </div>
      ))}
    </div>
  );
}

function Tier({ color, name, cost, desc }: { color: string; name: string; cost: string; desc: string }) {
  return (
    <div className={`card border-l-4 ${color}`}>
      <div className="flex items-center justify-between">
        <span className="font-semibold">{name}</span>
        <span className="text-xs text-slate-400">{cost}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">{desc}</p>
    </div>
  );
}

function Guard({ title, body }: { title: string; body: string }) {
  return (
    <details className="card">
      <summary className="cursor-pointer font-medium">🛡️ {title}</summary>
      <p className="mt-2 text-sm text-slate-600">{body}</p>
    </details>
  );
}

function Term({ t, d }: { t: string; d: string }) {
  return (
    <div>
      <span className="font-medium">{t}</span>
      <span className="text-slate-500"> — {d}</span>
    </div>
  );
}

function Faq({ q, a }: { q: string; a: string }) {
  return (
    <details className="card">
      <summary className="cursor-pointer font-medium">Q: {q}</summary>
      <p className="mt-2 text-sm text-slate-600">A: {a}</p>
    </details>
  );
}
