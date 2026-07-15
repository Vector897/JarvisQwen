"use client";

import Link from "next/link";
import { useLang } from "@/lib/i18n";

/** Guidelines: onboarding for first-time users, organized per common onboarding conventions —
 *  overview → quick start → feature-page descriptions (strictly in sidebar order) → core concepts → FAQ.
 *  In-depth technical notes (cost architecture, safety mechanisms) live on the Help page (/help); this page covers getting started only.
 *  Bilingual inline (EN/ZH), toggled by the language switch. */

export default function Guidelines() {
  const { lang } = useLang();
  const L = (en: string, zh: string) => (lang === "zh" ? zh : en);
  return (
    <div className="space-y-6 leading-relaxed">
      {/* 1. Overview */}
      <section className="card space-y-3">
        <h2 className="text-lg font-bold">{L("1. Overview: what JarvisQwen is", "一、产品概述：JarvisQwen 是什么")}</h2>
        <p className="text-sm text-slate-600">
          {L(
            "JarvisQwen is a self-hosted, 24/7 AI research butler for work that needs continuous tracking rather than one-off answers. You run it on your own machine — or a cheap always-on VM — and subscribe once to a topic; it then searches, triages, archives and summarizes new work on schedule, and organizes everything into a searchable library and a morning briefing (which you can export as Markdown, PDF or HTML). Because you host it yourself, it keeps working even when your own laptop is closed. It collects nothing about you — no company server, no account, no telemetry: your documents, keys, memories and briefings stay on your machine and talk only to your own AI (Qwen) with a key you hold. No code, no babysitting, no surprise bills.",
            "JarvisQwen 是一个自托管、7×24 小时运行的 AI 研究管家，面向「需要持续跟踪」而非「一次性回答」的工作。你把它跑在自己的机器上（或一台便宜的常开云主机），订阅一个主题后，系统便按计划自动检索、初筛、归档、总结，并把结果整理成可检索的知识库与每日晨间简报（可导出为 Markdown / PDF / HTML）。因为是你自己托管，即使你的笔记本合上，它也照常运行。它不收集你的任何数据——没有厂商服务器、没有账号、没有埋点：你的文档、密钥、记忆与简报都留在你自己的机器上，只与你自己的 AI（Qwen）通信，用的是你自己持有的密钥。无需写代码、无需盯着、不会有意外账单。"
          )}
        </p>
        <p className="text-sm text-slate-600">
          {L(
            "The table below summarizes how JarvisQwen differs from conversational AI assistants (such as Doubao or DeepSeek):",
            "下表概括了 JarvisQwen 与对话式 AI 助手（如豆包、DeepSeek）的差异："
          )}
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-400">
                <th className="py-2 pr-3"></th>
                <th className="py-2 pr-3">{L("Conversational AI", "对话式 AI 助手")}</th>
                <th className="py-2">JarvisQwen</th>
              </tr>
            </thead>
            <tbody className="text-slate-600">
              <CmpRow k={L("How work is initiated", "工作方式")}
                a={L("Question-and-answer; stops when the conversation ends", "一问一答，会话结束即停止")}
                b={L("Runs continuously on schedule, without manual prompting", "按计划持续运行，无需反复下达指令")} />
              <CmpRow k={L("User presence", "使用期间")}
                a={L("The user must stay online and wait", "需要用户在线等待")}
                b={L("The user can go offline; execution continues in the cloud", "用户可离线，系统在云端继续执行")} />
              <CmpRow k={L("Where results are kept", "结果存放")}
                a={L("Scattered across chat history", "分散在聊天记录中")}
                b={L("Archived in the Library and digested into daily Briefings", "归档至「知识库」，并汇总为每日「简报」")} />
              <CmpRow k={L("Memory of the user", "用户记忆")}
                a={L("Limited memory across conversations", "跨会话记忆有限")}
                b={L("Long-term memory of your research focus and preferences", "长期记忆你的研究方向与偏好")} />
              <CmpRow k={L("Cost management", "费用管理")}
                a={L("Subscription or per-call billing, with little visibility", "按订阅或调用计费，明细不透明")}
                b={L("Hard daily budget cap plus a per-call audit trail", "每日预算上限 + 逐笔调用审计")} />
            </tbody>
          </table>
        </div>
      </section>

      {/* 2. Quick start */}
      <section className="card space-y-3">
        <h2 className="text-lg font-bold">{L("2. Quick start", "二、快速上手")}</h2>
        <ol className="list-decimal space-y-2 pl-6 text-sm text-slate-600">
          <li>
            <b>{L("Configure the system (Settings).", "完成基础配置（设置页）。")}</b>{" "}
            {L(
              "Paste an API key, set a daily budget cap, and describe your research focus. If no key is configured, the system runs in dry-run mode: the full pipeline works with simulated model responses, at zero cost.",
              "粘贴 API Key、设置每日预算上限、填写你的研究方向。未配置 Key 时系统以 dry-run 模拟模式运行：全流程可正常走通，模型返回模拟内容，不产生任何费用。"
            )}
          </li>
          <li>
            <b>{L("Submit a task (Tasks).", "提交一个任务（任务页）。")}</b>{" "}
            {L(
              "Describe what you want in natural language — for example, \"survey the latest research progress on topic X\" — and submit. The task detail page shows each execution step advancing in real time; you may close the page at any point.",
              "用自然语言描述需求，例如「调研 XXX 方向的最新研究进展」，然后提交。任务详情页会实时展示各执行步骤的进度，期间可以随时关闭页面。"
            )}
          </li>
          <li>
            <b>{L("View the results (task detail page).", "查看任务结果（任务详情页）。")}</b>{" "}
            {L(
              "When the task is marked Done, open its detail page and read the full output in the \"Artifacts\" section. The same results are also archived into the Library and included in the next day's Briefing.",
              "任务显示 Done 后，进入任务详情页，在「产出物（Artifacts）」区域阅读完整结果。同一结果也会归档进「知识库」，并汇总进次日「简报」。"
            )}
          </li>
        </ol>
        <p className="text-xs text-slate-400">
          {L(
            "Going further: add long-term topics in Subscriptions, and the system will track them automatically — briefings will arrive every morning without any further action.",
            "进一步使用：在「订阅」页添加长期关注的主题后，系统会自动持续跟踪，此后每天早晨的简报无需你再做任何操作。"
          )}
        </p>
      </section>

      {/* 3. Feature pages (in sidebar order) */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">
          {L("3. Feature pages, in sidebar order", "三、功能页面说明（按侧边栏自上而下的顺序）")}
        </h2>
        <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Feature icon="📖" name={L("Guidelines", "使用指南")}
            d={L(
              "This page. It introduces what the system does, how to get started, and what each page is for.",
              "即本页。介绍系统的定位、上手流程与各功能页面的作用。"
            )} />
          <Feature icon="📊" name={L("Dashboard", "仪表盘")}
            d={L(
              "The system overview: today's spending against the budget, the number of running tasks, and recent model-call statistics. A recommended starting point for each visit.",
              "系统总览：今日花费与预算进度、运行中任务数量、近期模型调用统计。建议每次使用从这里开始。"
            )} />
          <Feature icon="🔁" name={L("Tasks", "任务")}
            d={L(
              "The core working page. Submit tasks in natural language, monitor their execution progress, and open a task's detail page to read its results in the Artifacts section.",
              "核心工作页面。在此用自然语言提交任务、查看任务的执行进度；点击任务进入详情页，即可在「产出物」区域阅读结果。"
            )} />
          <Feature icon="📡" name={L("Subscriptions", "订阅")}
            d={L(
              "Manages the topics you track long-term. Once a subscription is added, the system searches for new content on schedule — no need to submit the same task repeatedly.",
              "管理长期跟踪的主题。添加订阅后，系统会按计划自动检索新内容，无需反复提交相同的任务。"
            )} />
          <Feature icon="📚" name={L("Library", "知识库")}
            d={L(
              "The archive of everything the system has collected and summarized, with search. Unlike chat history, archived content is never buried or lost.",
              "系统收集并总结过的全部资料的归档库，支持检索。与聊天记录不同，归档内容不会被刷走或丢失。"
            )} />
          <Feature icon="📰" name={L("Briefings", "简报")}
            d={L(
              "The daily digest the system generates automatically each morning, condensing everything newly collected in the past day.",
              "系统每天早晨自动生成的汇总报告，浓缩过去一天新收集的全部内容。"
            )} />
          <Feature icon="✅" name={L("Approvals", "审批")}
            d={L(
              "The confirmation queue for high-risk operations such as deletion or outbound sending. Such operations are held here and executed only after your explicit approval.",
              "高风险操作（如删除、对外发送）的确认队列。此类操作会在这里等待，经你明确批准后才会执行。"
            )} />
          <Feature icon="🧾" name={L("Audit", "审计")}
            d={L(
              "The itemized record of every model call: which model was used, how many tokens were consumed, and how much it cost.",
              "全部模型调用的明细记录：每一次调用使用了哪个模型、消耗了多少 token、产生了多少费用，逐笔可查。"
            )} />
          <Feature icon="📱" name={L("Connect", "手机遥控")}
            d={L(
              "Links a Telegram account, so you can submit tasks and receive briefings from your phone.",
              "绑定 Telegram 账号，之后可以在手机上提交任务、接收简报。"
            )} />
          <Feature icon="🚀" name={L("Deploy", "一键部署")}
            d={L(
              "A step-by-step guide to deploying your own private instance of JarvisQwen.",
              "部署一套完全属于你自己的 JarvisQwen 实例的分步教程。"
            )} />
          <Feature icon="⚙️" name={L("Settings", "设置")}
            d={L(
              "Global configuration: API keys, the daily budget cap, your research focus, and other preferences.",
              "全局配置：API Key、每日预算上限、研究方向及其他偏好。"
            )} />
          <Feature icon="❓" name={L("Help", "帮助")}
            d={L(
              "The technical reference: cost architecture, safety mechanisms, glossary, and troubleshooting, in greater depth than this guide.",
              "技术参考文档：成本架构、安全机制、名词解释与故障排查，内容比本指南更深入。"
            )} />
        </div>
      </section>

      {/* 4. Core concepts */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">{L("4. Core concepts", "四、核心概念")}</h2>
        <div className="card space-y-3 text-sm">
          <Concept name={L("Task flow diagram", "任务流程图")}
            d={L(
              "Each task is broken into sequential steps (for example: search → de-duplicate → archive → summarize → memorize). The diagram at the top of the task detail page shows the real-time status of each step; a green node means that step has completed. Note that the diagram shows the execution process — the actual results are in the Artifacts section below it.",
              "每个任务被拆分为顺序执行的若干步骤（例如：检索 → 去重 → 归档 → 总结 → 写入记忆）。任务详情页顶部的流程图实时展示各步骤的执行状态，绿色节点表示该步骤已完成。需要注意：流程图展示的是执行过程，任务的实际结果位于其下方的「产出物」区域。"
            )} />
          <Concept name={L("Artifacts", "产出物（Artifacts）")}
            d={L(
              "The reviewable output each step produces, such as the search list, the archive list, and the full written summary. This is where a task's final answer lives.",
              "每个步骤产生的可查阅结果，例如检索清单、归档列表和完整的总结文稿。任务的最终答案就在这里。"
            )} />
          <Concept name={L("Checkpoint", "检查点（Checkpoint）")}
            d={L(
              "The system saves its state after each completed step. If a task fails or is interrupted, it resumes from the most recent checkpoint — completed steps are never re-executed or re-billed.",
              "系统在每个步骤完成后保存一次状态。任务失败或中断后会从最近的检查点继续执行，已完成的步骤不会重复执行，也不会重复计费。"
            )} />
          <Concept name={L("Dry-run mode", "Dry-run 模式")}
            d={L(
              "The simulation mode used when no API key is configured: the full pipeline runs normally, model calls return simulated content, and no cost is incurred.",
              "未配置 API Key 时的模拟运行模式：全部流程正常走通，模型调用返回模拟内容，不产生任何费用。"
            )} />
        </div>
      </section>

      {/* 5. Frequently asked questions */}
      <section className="space-y-2">
        <h2 className="text-lg font-bold">{L("5. Frequently asked questions", "五、常见问题")}</h2>
        <div className="space-y-2">
          <Faq q={L("Where can I view the results of a completed task?", "提交的任务完成后，我应该在哪里查看任务的结果？")}
            a={L(
              "Open the Tasks page and click the task to enter its detail page; the results are in the \"Artifacts\" section below the flow diagram. The same results are also archived in the Library and included in the next Briefing.",
              "打开「任务」页，点击该任务进入详情页，结果位于流程图下方的「产出物（Artifacts）」区域。同一结果也会归档至「知识库」，并汇总进下一期「简报」。"
            )} />
          <Faq q={L("What does the flow diagram at the top of the task detail page represent?", "任务详情页顶部的流程图代表什么含义？")}
            a={L(
              "It shows the real-time status of each execution step of the task; green means completed. The diagram describes the process only — to read the results, scroll down to the Artifacts section.",
              "它实时展示该任务各执行步骤的状态，绿色表示已完成。流程图只描述执行过程；要阅读结果，请向下滚动到「产出物」区域。"
            )} />
          <Faq q={L("Why do my tasks keep returning simulated responses without incurring any cost?", "任务始终返回模拟响应且不产生任何费用，是什么原因？")}
            a={L(
              "No API key has been configured, so the system is running in dry-run mode. Paste a valid key on the Settings page to switch to real model calls.",
              "系统当前未配置 API Key，正以 dry-run 模拟模式运行。在「设置」页粘贴一个有效的 Key 即可切换为真实模型调用。"
            )} />
          <Faq q={L("What should I do when a task fails?", "任务执行失败后，我应该如何处理？")}
            a={L(
              "Open the task's detail page and click \"Rerun from checkpoint\". The task resumes from the last successful step; completed work is not repeated.",
              "打开该任务的详情页，点击「从检查点重跑」。任务会从最后一个成功的步骤继续执行，已完成的部分不会重做。"
            )} />
          <Faq q={L("What does a red connection indicator in the top bar mean?", "页面右上角的连接状态指示点变红，代表什么？")}
            a={L(
              "The real-time event stream has disconnected, usually due to a backend restart or a network interruption. The browser reconnects automatically; no action is required.",
              "表示实时事件流已断开，通常由后端重启或网络波动引起。浏览器会自动重连，无需任何操作。"
            )} />
          <Faq q={L("How do I control the system's daily spending?", "我应该如何控制系统的每日花费？")}
            a={L(
              "Set a daily budget cap on the Settings page: an alert is issued at 80% of the cap, and tasks are suspended at 100%, so spending can never exceed the cap. The Dashboard shows today's spending in real time, and the Audit page itemizes every call.",
              "在「设置」页设置每日预算上限：花费达到上限的 80% 时系统会告警，达到 100% 时任务会被挂起，因此花费不可能超出上限。「仪表盘」实时显示今日花费，「审计」页可查询每一笔调用明细。"
            )} />
        </div>
        <p className="text-xs text-slate-400">
          {L("For deeper technical details — cost architecture, safety mechanisms and troubleshooting — see the ", "更深入的技术细节（成本架构、安全机制与故障排查）请参阅侧边栏最后的")}
          <Link href="/help" className="underline hover:text-slate-600">{L("Help page", "「帮助」页")}</Link>
          {L(".", "。")}
        </p>
      </section>
    </div>
  );
}

function CmpRow({ k, a, b }: { k: string; a: string; b: string }) {
  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="py-2 pr-3 font-medium text-slate-700">{k}</td>
      <td className="py-2 pr-3 text-slate-500">{a}</td>
      <td className="py-2 font-medium text-emerald-700">{b}</td>
    </tr>
  );
}

function Feature({ icon, name, d }: { icon: string; name: string; d: string }) {
  return (
    <div className="card h-full">
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <span className="font-semibold">{name}</span>
      </div>
      <p className="mt-1.5 text-xs text-slate-500">{d}</p>
    </div>
  );
}

function Concept({ name, d }: { name: string; d: string }) {
  return (
    <div>
      <span className="font-semibold">{name}</span>
      <p className="text-slate-500">{d}</p>
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
