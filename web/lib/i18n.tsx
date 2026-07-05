"use client";

import { createContext, useContext, useEffect, useState } from "react";

/**
 * 轻量 i18n：覆盖全部界面文案（导航、按钮、标题、空状态、表单标签、Toast 提示）。
 * 范围边界：后端返回的动态内容本身——任务标题、审计摘要、简报正文、AI 回答——
 * 是模型生成的中文语义内容，不在此翻译范围（那是数据，不是界面文案）。
 * 帮助页（/help）是长文档说明，保留中文原文，切换英文时顶部会有提示条。
 */

const DICT = {
  zh: {
    "nav.dashboard": "仪表盘", "nav.tasks": "任务", "nav.subscriptions": "订阅",
    "nav.library": "知识库", "nav.briefings": "简报", "nav.approvals": "审批",
    "nav.audit": "审计", "nav.settings": "设置", "nav.help": "帮助",
    "topbar.logout": "登出", "topbar.online": "实时连接正常", "topbar.offline": "连接断开，重连中…",
    "topbar.admin": "管理员",
    "common.save": "保存", "common.cancel": "取消", "common.delete": "删除", "common.loading": "加载中…",

    "dashboard.spendToday": "今日花费", "dashboard.budgetHint": "达 80% 会告警，达 100% 自动熔断挂起任务——不会超支。",
    "dashboard.runningTasks": "运行中任务", "dashboard.calls24h": "24h LLM 调用",
    "dashboard.cacheHits24h": "24h 缓存命中", "dashboard.papersTotal": "论文总数",
    "dashboard.statusBreakdown": "任务状态分布",
    "dashboard.noTasks": "暂无任务——去「任务」页下达第一个任务，或在「订阅」页添加自动轮询。",
    "dashboard.costTrend": "近 7 天花费趋势", "dashboard.costByModel": "按模型花费占比",
    "dashboard.budgetCutoff": "预算已用尽（已熔断）", "dashboard.budgetWarn": "预算告警",

    "tasks.promptPlaceholder": "或直接用自然语言下任务，如：\"帮我调研 XXX 的最新进展\"",
    "tasks.submit": "提交任务", "tasks.submitting": "提交中…",
    "tasks.templateCancel": "取消", "tasks.templateSubmit": "创建任务",
    "tasks.empty": "还没有任务", "tasks.emptyHint": "用上面的模板或自然语言下达第一个任务。",
    "tasks.created": "已创建任务", "tasks.done": "任务完成", "tasks.failed": "任务失败，可从检查点重跑",
    "tasks.suspended": "任务已挂起（预算或等待）",

    "taskDetail.totalProgress": "总进度", "taskDetail.finishedAt": "完成于",
    "taskDetail.rerun": "从检查点重跑", "taskDetail.cancel": "取消任务",
    "taskDetail.artifacts": "产出物（Artifacts）", "taskDetail.noArtifacts": "暂无产出物。",
    "taskDetail.requeued": "已从检查点重新排队", "taskDetail.cancelled": "任务已取消",

    "subs.hint": "添加后系统 7×24 自动轮询 arXiv、去重、初筛、归档并总结新论文——你的电脑可以关机。",
    "subs.queryPlaceholder": "arXiv 关键词，如：LLM agent security / portfolio optimization",
    "subs.add": "添加订阅", "subs.every1h": "每 1 小时", "subs.every6h": "每 6 小时",
    "subs.every12h": "每 12 小时", "subs.everyDay": "每天",
    "subs.empty": "还没有订阅", "subs.emptyHint": "添加一个研究关键词，系统就会自动帮你盯着新论文。",
    "subs.pause": "暂停", "subs.enable": "启用", "subs.delete": "删除", "subs.paused": "已暂停",
    "subs.added": "已添加订阅",

    "library.qaTitle": "🔎 问知识库", "library.qaHint": "对已归档的全部论文提问，系统会检索相关证据并标注引用来源。",
    "library.qaPlaceholder": "如：我库里关于灾难性遗忘的论文都提出了什么解决方案？",
    "library.qaAsk": "提问", "library.qaAsking": "检索中…",
    "library.qaEscalated": "（轻量层置信度不足，已自动升级到前沿模型重答）",
    "library.searchPlaceholder": "搜索已归档论文（标题/摘要）", "library.search": "搜索",
    "library.exportBibtex": "导出 BibTeX",
    "library.empty": "知识库为空", "library.emptyHint": "创建文献跟踪任务或添加订阅后会自动填充。",
    "library.viewOriginal": "查看原文 →", "library.zoteroSync": "同步到 Zotero",

    "briefings.empty": "暂无简报",
    "briefings.emptyHint": "系统每天早晨自动生成；也可以在任务页输入\"生成简报\"立即触发。",
    "briefings.exportMd": "导出 MD", "briefings.exportPdf": "导出 PDF",

    "approvals.hint": "高危操作会在这里等待你批准后从检查点无缝继续。",
    "approvals.empty": "没有待审批项", "approvals.emptyHint": "当任务触发高危操作（如对外发送、删除）时会出现在这里。",
    "approvals.riskLevel": "风险等级",
    "approvals.approve": "批准", "approvals.reject": "拒绝",
    "approvals.newOne": "有新的待审批操作", "approvals.approved": "已批准，任务将从检查点继续", "approvals.rejected": "已拒绝",

    "audit.hint": "每一次 LLM 出境调用的模型、token、费用与输入输出摘要（append-only）。",
    "audit.input": "输入：", "audit.output": "输出：", "audit.empty": "暂无调用记录。",
    "audit.cacheHit": "缓存命中", "audit.dryRun": "dry-run",

    "settings.keysTitle": "API Key", "settings.keysHint": "粘贴即可——自动去除空格/引号/Bearer 前缀、全角转半角、识别厂商，保存时实时探活校验。",
    "settings.keysPlaceholder": "粘贴你的 API Key（怎么粘都行，系统会自动修正格式）",
    "settings.keysAdvanced": "高级：自定义 OpenAI 兼容端点（各类中转站/自部署 vLLM）",
    "settings.keysSave": "保存并校验", "settings.keysVerifying": "校验中…", "settings.keysProbe": "探活",
    "settings.keysEmpty": "尚未配置任何 Key——系统当前运行在 dry-run 模式（LLM 返回模拟响应，不产生费用）。",
    "settings.selectProvider": "选择厂商…",

    "settings.generalTitle": "运行参数", "settings.researchProfile": "我的研究方向（用于论文初筛与总结）",
    "settings.dailyBudget": "每日预算上限（美元）", "settings.redactLevel": "脱敏等级",
    "settings.redactLow": "低（只拦截明确凭证）", "settings.redactMed": "中（凭证+PII 占位符替换）",
    "settings.redactHigh": "高（高危命中直接阻断出境）",
    "settings.modelLight": "轻量层模型（解析/初筛/简报）", "settings.modelFrontier": "前沿层模型（总结/综述）",
    "settings.relevanceThreshold": "初筛相关度阈值（0-1）", "settings.briefingHour": "简报生成时间（小时，0-23）",
    "settings.cacheEnabled": "启用语义缓存（相同/相近请求直接复用历史结果，省钱）",
    "settings.cascadeEnabled": "启用模型级联（跨库问答等场景先用轻量层回答，置信度不足才升级前沿层）",
    "settings.cascadeThreshold": "级联置信度阈值（0-1，越低越少升级）",
    "settings.save": "保存设置", "settings.saved": "已保存，立即生效",

    "settings.notifyTitle": "推送通知", "settings.notifyHint": "简报生成、预算熔断时推送到 Telegram 或邮箱，离开网页也能收到。",
    "settings.telegramEnable": "启用 Telegram 推送", "settings.telegramToken": "Bot Token（找 @BotFather 申请）",
    "settings.telegramChatId": "Chat ID", "settings.emailEnable": "启用邮件推送（SMTP）",
    "settings.smtpHost": "SMTP 服务器，如 smtp.gmail.com", "settings.smtpPort": "端口（587）",
    "settings.smtpUser": "用户名", "settings.smtpPassword": "密码/App Password",
    "settings.smtpFrom": "发件地址", "settings.smtpTo": "收件地址",
    "settings.notifyOnCutoff": "预算熔断时也推送（强烈建议开启，避免任务静默挂起没人知道）",
    "settings.testNotify": "发送测试推送", "settings.notifySaved": "推送设置已保存",
    "settings.configuredKeepBlank": "已配置，留空保持不变",

    "settings.zoteroTitle": "Zotero 同步",
    "settings.zoteroHint": "单向推送：在知识库页把归档论文一键推入你的 Zotero 文献库。API Key 在 Zotero 设置 → Security 里生成。",
    "settings.zoteroKey": "Zotero API Key", "settings.zoteroLibraryId": "Library ID",
    "settings.zoteroType": "Library 类型", "settings.zoteroUser": "个人库（user）", "settings.zoteroGroup": "团队库（group）",
    "settings.zoteroSaved": "Zotero 配置已保存",

    "settings.usersTitle": "用户管理（管理员）", "settings.usersNamePlaceholder": "用户名",
    "settings.roleMember": "member（可下任务）", "settings.roleViewer": "viewer（只读）", "settings.roleAdmin": "admin（全权限）",
    "settings.usersCreate": "创建账号", "settings.usersDelete": "删除",
    "settings.roleUpdated": "角色已更新", "settings.userDeleted": "已删除用户",

    "settings.accountTitle": "账号", "settings.oldPassword": "原密码", "settings.newPassword": "新密码（至少 8 位）",
    "settings.changePassword": "修改密码", "settings.passwordChanged": "密码已修改",

    "login.title": "登录 JarvisQwen", "login.hint": "首次部署的初始密码在服务器 data/admin_password.txt",
    "login.username": "用户名", "login.password": "密码", "login.submit": "登录",

    "help.langNotice": "帮助页目前仅提供中文说明文档，界面切换不影响本页内容。",
  },
  en: {
    "nav.dashboard": "Dashboard", "nav.tasks": "Tasks", "nav.subscriptions": "Subscriptions",
    "nav.library": "Library", "nav.briefings": "Briefings", "nav.approvals": "Approvals",
    "nav.audit": "Audit", "nav.settings": "Settings", "nav.help": "Help",
    "topbar.logout": "Log out", "topbar.online": "Live", "topbar.offline": "Reconnecting…",
    "topbar.admin": "Admin",
    "common.save": "Save", "common.cancel": "Cancel", "common.delete": "Delete", "common.loading": "Loading…",

    "dashboard.spendToday": "Today's spend", "dashboard.budgetHint": "Alerts at 80%, auto-cutoff at 100% suspends tasks — never over budget.",
    "dashboard.runningTasks": "Running tasks", "dashboard.calls24h": "LLM calls (24h)",
    "dashboard.cacheHits24h": "Cache hits (24h)", "dashboard.papersTotal": "Papers in library",
    "dashboard.statusBreakdown": "Task status breakdown",
    "dashboard.noTasks": "No tasks yet — create one on the Tasks page, or add a subscription for auto-polling.",
    "dashboard.costTrend": "7-day spend trend", "dashboard.costByModel": "Spend by model",
    "dashboard.budgetCutoff": "Budget exhausted (cut off)", "dashboard.budgetWarn": "Budget warning",

    "tasks.promptPlaceholder": 'Or use natural language, e.g. "Research the latest progress on XXX"',
    "tasks.submit": "Submit task", "tasks.submitting": "Submitting…",
    "tasks.templateCancel": "Cancel", "tasks.templateSubmit": "Create task",
    "tasks.empty": "No tasks yet", "tasks.emptyHint": "Use a template above, or describe a task in natural language.",
    "tasks.created": "Task created", "tasks.done": "Task done", "tasks.failed": "Task failed — can rerun from checkpoint",
    "tasks.suspended": "Task suspended (budget or waiting)",

    "taskDetail.totalProgress": "Overall progress", "taskDetail.finishedAt": "Finished at",
    "taskDetail.rerun": "Rerun from checkpoint", "taskDetail.cancel": "Cancel task",
    "taskDetail.artifacts": "Artifacts", "taskDetail.noArtifacts": "No artifacts yet.",
    "taskDetail.requeued": "Requeued from checkpoint", "taskDetail.cancelled": "Task cancelled",

    "subs.hint": "The system polls arXiv 24/7, dedupes, filters, archives, and summarizes new papers — your computer can be off.",
    "subs.queryPlaceholder": "arXiv keyword, e.g. LLM agent security / portfolio optimization",
    "subs.add": "Add subscription", "subs.every1h": "Every hour", "subs.every6h": "Every 6 hours",
    "subs.every12h": "Every 12 hours", "subs.everyDay": "Daily",
    "subs.empty": "No subscriptions yet", "subs.emptyHint": "Add a research keyword and the system will watch for new papers automatically.",
    "subs.pause": "Pause", "subs.enable": "Enable", "subs.delete": "Delete", "subs.paused": "Paused",
    "subs.added": "Subscription added",

    "library.qaTitle": "🔎 Ask the library", "library.qaHint": "Ask a question over all archived papers — the system retrieves evidence and cites sources.",
    "library.qaPlaceholder": "e.g. What solutions do the papers in my library propose for catastrophic forgetting?",
    "library.qaAsk": "Ask", "library.qaAsking": "Searching…",
    "library.qaEscalated": "(Light tier was uncertain — automatically escalated to the frontier model)",
    "library.searchPlaceholder": "Search archived papers (title/abstract)", "library.search": "Search",
    "library.exportBibtex": "Export BibTeX",
    "library.empty": "Library is empty", "library.emptyHint": "Create a literature-watch task or add a subscription to populate it.",
    "library.viewOriginal": "View original →", "library.zoteroSync": "Sync to Zotero",

    "briefings.empty": "No briefings yet",
    "briefings.emptyHint": 'Generated automatically every morning; or type "generate briefing" on the Tasks page to trigger one now.',
    "briefings.exportMd": "Export MD", "briefings.exportPdf": "Export PDF",

    "approvals.hint": "High-risk actions wait here for your approval, then resume seamlessly from the checkpoint.",
    "approvals.empty": "Nothing pending", "approvals.emptyHint": "Shows up here when a task triggers a high-risk action (e.g. outbound send, delete).",
    "approvals.riskLevel": "Risk",
    "approvals.approve": "Approve", "approvals.reject": "Reject",
    "approvals.newOne": "New item awaiting approval", "approvals.approved": "Approved — task will resume from checkpoint", "approvals.rejected": "Rejected",

    "audit.hint": "Model, tokens, cost, and input/output digest for every outbound LLM call (append-only).",
    "audit.input": "Input:", "audit.output": "Output:", "audit.empty": "No calls recorded yet.",
    "audit.cacheHit": "Cache hit", "audit.dryRun": "dry-run",

    "settings.keysTitle": "API Keys", "settings.keysHint": "Just paste it — whitespace/quotes/Bearer prefix are stripped automatically, provider is detected, and it's tested live on save.",
    "settings.keysPlaceholder": "Paste your API key (any format — auto-corrected)",
    "settings.keysAdvanced": "Advanced: custom OpenAI-compatible endpoint (gateways / self-hosted vLLM)",
    "settings.keysSave": "Save & verify", "settings.keysVerifying": "Verifying…", "settings.keysProbe": "Test",
    "settings.keysEmpty": "No keys configured — running in dry-run mode (LLM returns simulated responses, no cost).",
    "settings.selectProvider": "Select provider…",

    "settings.generalTitle": "Runtime settings", "settings.researchProfile": "My research focus (used for paper filtering & summarizing)",
    "settings.dailyBudget": "Daily budget cap (USD)", "settings.redactLevel": "Redaction level",
    "settings.redactLow": "Low (block obvious credentials only)", "settings.redactMed": "Medium (credentials + PII placeholders)",
    "settings.redactHigh": "High (block outbound on any high-risk match)",
    "settings.modelLight": "Light-tier model (parsing/filtering/briefings)", "settings.modelFrontier": "Frontier-tier model (summaries/surveys)",
    "settings.relevanceThreshold": "Relevance threshold (0-1)", "settings.briefingHour": "Briefing generation hour (0-23)",
    "settings.cacheEnabled": "Enable semantic cache (reuse similar past results — saves money)",
    "settings.cascadeEnabled": "Enable model cascade (light tier answers first; escalate only when uncertain)",
    "settings.cascadeThreshold": "Cascade confidence threshold (0-1, lower = fewer escalations)",
    "settings.save": "Save settings", "settings.saved": "Saved, effective immediately",

    "settings.notifyTitle": "Push notifications", "settings.notifyHint": "Get pushed to Telegram or email when a briefing is ready or the budget cuts off.",
    "settings.telegramEnable": "Enable Telegram push", "settings.telegramToken": "Bot token (from @BotFather)",
    "settings.telegramChatId": "Chat ID", "settings.emailEnable": "Enable email push (SMTP)",
    "settings.smtpHost": "SMTP server, e.g. smtp.gmail.com", "settings.smtpPort": "Port (587)",
    "settings.smtpUser": "Username", "settings.smtpPassword": "Password / App password",
    "settings.smtpFrom": "From address", "settings.smtpTo": "To address",
    "settings.notifyOnCutoff": "Also push on budget cutoff (strongly recommended — otherwise a suspended task goes unnoticed)",
    "settings.testNotify": "Send test push", "settings.notifySaved": "Notification settings saved",
    "settings.configuredKeepBlank": "Configured — leave blank to keep it",

    "settings.zoteroTitle": "Zotero sync",
    "settings.zoteroHint": "One-way push: send archived papers to your Zotero library from the Library page. Generate the API key under Zotero Settings → Security.",
    "settings.zoteroKey": "Zotero API key", "settings.zoteroLibraryId": "Library ID",
    "settings.zoteroType": "Library type", "settings.zoteroUser": "Personal library (user)", "settings.zoteroGroup": "Group library (group)",
    "settings.zoteroSaved": "Zotero settings saved",

    "settings.usersTitle": "User management (admin)", "settings.usersNamePlaceholder": "Username",
    "settings.roleMember": "member (can run tasks)", "settings.roleViewer": "viewer (read-only)", "settings.roleAdmin": "admin (full access)",
    "settings.usersCreate": "Create account", "settings.usersDelete": "Delete",
    "settings.roleUpdated": "Role updated", "settings.userDeleted": "User deleted",

    "settings.accountTitle": "Account", "settings.oldPassword": "Current password", "settings.newPassword": "New password (8+ chars)",
    "settings.changePassword": "Change password", "settings.passwordChanged": "Password changed",

    "login.title": "Sign in to JarvisQwen", "login.hint": "The initial password is in data/admin_password.txt on the server",
    "login.username": "Username", "login.password": "Password", "login.submit": "Sign in",

    "help.langNotice": "The Help page is currently Chinese-only documentation; the language toggle doesn't affect this content.",
  },
} as const;

type Lang = keyof typeof DICT;
type Key = keyof typeof DICT["zh"];

const LangCtx = createContext<{ lang: Lang; t: (k: Key) => string; toggle: () => void }>({
  lang: "en",
  t: (k) => DICT.en[k] ?? k,
  toggle: () => {},
});
export const useLang = () => useContext(LangCtx);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  useEffect(() => {
    const saved = localStorage.getItem("aaos-lang") as Lang | null;
    if (saved && DICT[saved]) setLang(saved);
  }, []);

  function toggle() {
    const next: Lang = lang === "zh" ? "en" : "zh";
    setLang(next);
    localStorage.setItem("aaos-lang", next);
  }

  const t = (k: Key) => DICT[lang][k] ?? DICT.en[k] ?? k;

  return <LangCtx.Provider value={{ lang, t, toggle }}>{children}</LangCtx.Provider>;
}
