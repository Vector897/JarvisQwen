"use client";

import { useState } from "react";
import { useLang } from "@/lib/i18n";

/** 一键部署页：一段给 AI-IDE 的提示词——复制给 Claude Code / Cursor 等,
 *  它就会替用户在本地装好(或升级)整个项目。面向零技术背景用户。 */

const PROMPT = `You are setting up JarvisQwen — an open-source, self-hosted AI research autopilot — on this computer. Repository: https://github.com/Vector897/JarvisQwen

Work through the steps below. Explain what you're doing in simple, non-technical language as you go. If anything fails, diagnose and fix it yourself; only ask me when a decision is truly mine to make.

1. Check prerequisites: git, Python 3.11+, Node.js 18+. Install anything missing (or give me the download link and wait for me).
2. If a "JarvisQwen" folder already exists here, run \`git pull\` inside it to UPDATE it to the latest version. Otherwise, clone the repository.
3. Backend: create a Python virtual environment inside ./server and install with: pip install -e ".[dev]" litellm
4. Frontend: run npm install inside ./web
5. Ask me for my Qwen Cloud API key (free to get at https://home.qwencloud.com -> API Keys; it starts with "sk-"). Save it to a file named .env at the project root, containing exactly one line: DASHSCOPE_API_KEY=<my key>. Never echo my full key back to me and never commit it anywhere. If I don't have a key yet, skip this step — the system runs in dry-run mode (zero cost, simulated AI) and I can add a key later in Settings.
6. Start both services: backend with uvicorn app.main:app --port 8000 (from ./server, using the venv), frontend with npm run dev (from ./web). Then open http://localhost:3000 in my browser.
7. Read the initial admin password from ./server/data/admin_password.txt (created on first start) and tell me. Then walk me through, step by step: signing in, filling in "My research focus" in Settings, and adding my first topic subscription.
8. Finally, run the test suite (python -m pytest in ./server) and confirm to me everything is green.`;

export default function Deploy() {
  const { lang } = useLang();
  const L = <T,>(en: T, zh: T): T => (lang === "zh" ? zh : en);
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(PROMPT).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">🚀 {L("Deploy without knowing how to code", "不会写代码,也能部署")}</h2>
        <p className="text-sm leading-6 text-slate-500">
          {L(
            "You don't install JarvisQwen. An AI does it for you. Copy the text below, paste it into any AI coding assistant that can operate your computer — Claude Code, Cursor, Windsurf, or similar — and it will download, configure, start, and even UPDATE the entire project for you, explaining every step in plain language. Anything that genuinely needs your hand (like getting a free API key), it will walk you through click by click.",
            "你不需要亲手安装 JarvisQwen——让 AI 替你装。复制下面这段文字,粘贴给任何能操作你电脑的 AI 编程助手(Claude Code、Cursor、Windsurf 等),它就会自动下载、配置、启动甚至升级整个项目,并用大白话解释每一步。真正需要你动手的环节(比如免费领一个 API Key),它会手把手带你点完。"
          )}
        </p>
      </section>

      <section className="card space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{L("The magic prompt", "魔法提示词")}</h3>
          <button onClick={copy} className="btn-primary text-sm">
            {copied ? L("✅ Copied!", "✅ 已复制!") : L("📋 Copy the prompt", "📋 一键复制")}
          </button>
        </div>
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-4 font-mono text-xs leading-5 text-slate-200">
{PROMPT}
        </pre>
        <p className="text-xs text-slate-400">
          {L(
            "The prompt is in English because AI assistants follow it most reliably that way — but you can talk to your assistant in any language while it works.",
            "提示词用英文写是因为 AI 助手执行英文指令最稳定——但执行过程中你完全可以用中文和它交流。"
          )}
        </p>
      </section>

      <section className="card space-y-2 text-sm">
        <h3 className="font-semibold">{L("What will happen, in plain words", "它到底会做什么(说人话版)")}</h3>
        <ol className="list-decimal space-y-1 pl-5 text-slate-600 dark:text-slate-300">
          <li>{L("Checks your computer has the basic tools; installs anything missing.", "检查你电脑上有没有基础工具,缺什么装什么。")}</li>
          <li>{L("Downloads JarvisQwen — or updates it if you already have it.", "下载 JarvisQwen;如果你已经装过,则升级到最新版。")}</li>
          <li>{L("Sets everything up and starts it. Your browser opens the console.", "配置并启动全部服务,浏览器自动打开控制台。")}</li>
          <li>{L("Helps you get a free Qwen API key and keeps it safely on YOUR machine only.", "带你免费领取 Qwen API Key,并且只保存在你自己的电脑上。")}</li>
          <li>{L("Walks you through your first subscription — tomorrow morning, your first briefing arrives.", "手把手带你添加第一个订阅——明天早晨,第一份简报就会送达。")}</li>
        </ol>
        <p className="pt-1 text-xs text-slate-400">
          {L(
            "No AI assistant? The README in the repository has the classic manual instructions too.",
            "没有 AI 助手?仓库 README 里也有传统的手动安装步骤。"
          )}
        </p>
      </section>
    </div>
  );
}
