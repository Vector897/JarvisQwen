"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

/** 公开落地页（无需登录）：隐私声明置顶 → 宣言 → 使命 → 作者与仓库。
 *  独立暗色画布（nav/topbar 在 /home 不渲染），风格与 Logo 一致。 */

const REPO = "https://github.com/Vector897/JarvisQwen";

const ZEN: [string, string][] = [
  ["Your attention is the scarcest resource on Earth. Spend it last.", "注意力是世上最稀缺的资源——把它留到最后再花。"],
  ["Machines should wait on people, not the other way around.", "该等待的是机器，不是人。"],
  ["If it must be watched, it isn't automated.", "还需要盯着的，就不叫自动化。"],
  ["Cheap models for cheap questions; expensive models only for expensive ones.", "便宜的问题用便宜的模型，昂贵的模型只留给昂贵的问题。"],
  ["Never pay twice for the same work.", "同一份工作，绝不付两次钱。"],
  ["A budget is a promise, not a suggestion.", "预算是承诺，不是建议。"],
  ["What leaves your machine should be your choice — and only yours.", "什么数据离开你的电脑，应当只由你决定。"],
  ["Trust is built from audit trails, not promises.", "信任来自可查的流水，而非口头的承诺。"],
  ["The best interface for AI is no interface: a briefing waiting at dawn.", "AI 最好的界面是没有界面——清晨醒来，简报已在。"],
  ["Simple enough for anyone. Honest enough for everyone.", "简单到人人可用，诚实到人人可查。"],
];

export default function Home() {
  const [code, setCode] = useState("");
  const [needCode, setNeedCode] = useState(false);
  const codeInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // api.ts 在访问码网关 401 时跳回 /home?code=required——高亮输入框、说明原因并聚焦
    const need = new URLSearchParams(window.location.search).get("code") === "required";
    setNeedCode(need);
    if (need) codeInput.current?.focus();
  }, []);

  function enterWithCode(e: React.FormEvent) {
    e.preventDefault();
    const k = code.trim();
    if (!k) return;
    // 走 middleware 的魔法链接逻辑：?k= 写入 aaos_access cookie 后跳到干净的 /dashboard
    window.location.href = `/dashboard?k=${encodeURIComponent(k)}`;
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="overflow-hidden rounded-3xl bg-[#05070d] text-slate-200 shadow-2xl ring-1 ring-slate-800">
        {/* Hero */}
        <div className="flex flex-col items-center px-6 pt-12 text-center">
          <h1 className="text-5xl font-extrabold tracking-tight drop-shadow-[0_0_25px_rgba(56,189,248,0.35)] sm:text-6xl">
            <span className="text-sky-400">Jarvis</span>
            <span className="text-white">Qwen</span>
          </h1>
          <p className="mt-3 text-sm tracking-widest text-sky-400/80">YOUR 24/7 AI BUTLER · POWERED BY QWEN</p>

          {/* CTA —— 移到 JarvisQwen 下一行 */}
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link href="/dashboard"
              className="rounded-xl bg-sky-500 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-400">
              Quick Try →
            </Link>
            <Link href="/deploy"
              className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-sky-500 hover:text-sky-400">
              🚀 Deploy your own
            </Link>
            <a href={REPO} target="_blank" rel="noreferrer"
              className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-sky-500 hover:text-sky-400">
              ⭐ GitHub
            </a>
          </div>

          {/* 访问码入口：公网 demo 的 /api 全部要求访问码；没走 ?k= 魔法链接的
              访客点 Quick Try 会被 401 弹回到这里（?code=required 高亮提示） */}
          <form onSubmit={enterWithCode}
            className={`mt-5 flex w-full max-w-md flex-col items-center gap-2 rounded-2xl border p-4 transition
              ${needCode ? "border-amber-500/70 bg-amber-950/30" : "border-slate-800 bg-slate-900/40"}`}>
            {needCode && (
              <p className="text-xs font-semibold text-amber-400">
                This demo requires an access code — paste the one you were given. ·
                该演示需要访问码，请粘贴你收到的访问码
              </p>
            )}
            <div className="flex w-full gap-2">
              <input ref={codeInput} value={code} onChange={(e) => setCode(e.target.value)}
                placeholder="Access code · 访问码 (jq-…)"
                className="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-sky-500" />
              <button type="submit"
                className="shrink-0 rounded-xl bg-slate-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-500">
                Enter →
              </button>
            </div>
            <p className="text-[11px] text-slate-600">
              Received a full invite link ending in <span className="font-mono">?k=…</span>?
              Open that link directly — it signs you in automatically, nothing to type here.
              · 如果你收到的是结尾带 <span className="font-mono">?k=…</span> 的完整链接，直接打开它即可自动进入，无需在此输入。
            </p>
          </form>
        </div>

        {/* 隐私声明——放在最前面 */}
        <div className="mx-6 mt-8 rounded-2xl border border-emerald-700/40 bg-emerald-950/40 p-5 text-sm leading-relaxed">
          <p className="font-semibold text-emerald-300">🔒 Before anything else, know this:</p>
          <p className="mt-2 text-emerald-100/90">
            <b>JarvisQwen collects nothing about you. Ever.</b> There is no company server, no account,
            no telemetry, no analytics. Everything — your documents, your API keys, your memories,
            your briefings — lives on <b>your own computer</b> and talks only to <b>your own AI</b>,
            with a key that <b>you</b> hold. Delete the folder and every trace is gone.
          </p>
          <p className="mt-2 text-xs text-emerald-200/60">
            本项目不收集任何用户数据：没有厂商服务器、没有账号体系、没有埋点。你的文档、密钥、记忆与简报全部保存在你自己的电脑上，只与你自己的 AI 通信。删除文件夹，一切痕迹随之消失。
          </p>
        </div>

        {/* 使命 */}
        <div className="px-8 py-10 text-center">
          <h2 className="text-xl font-bold text-white">Why this exists</h2>
          <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-400">
            The people who would benefit most from AI — researchers, analysts, doctors, lawyers,
            small-business owners — are mostly not programmers. Today, using AI <i>well</i> still
            means writing code, wiring APIs, and babysitting scripts. JarvisQwen is my answer:
            an AI butler that anyone can run — <b>subscribe to what you care about once, and wake up
            to what matters every morning</b>. No code. No babysitting. No surprise bills.
          </p>
        </div>

        {/* The Zen */}
        <div className="border-t border-slate-800/80 px-8 py-10">
          <h2 className="text-center text-xl font-bold text-white">The Zen of JarvisQwen</h2>
          <div className="mx-auto mt-6 max-w-xl space-y-4">
            {ZEN.map(([en, zh], i) => (
              <div key={i} className="text-center">
                <p className="text-[15px] leading-6 text-slate-200">{en}</p>
                <p className="text-xs text-slate-500">{zh}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 作者与仓库 */}
        <div className="border-t border-slate-800/80 px-8 py-8 text-center text-sm">
          <p className="text-slate-400">
            Built and actively maintained by{" "}
            <a href="https://github.com/Vector897" target="_blank" rel="noreferrer"
               className="font-semibold text-sky-400 hover:underline">@Vector897</a>.
            I use it every day for my own research, and I will keep shipping — new sources,
            new connectors, better memory. Star the repo to follow along, open an issue to shape it.
          </p>
          <a href={REPO} target="_blank" rel="noreferrer"
             className="mt-3 inline-block font-mono text-xs text-slate-500 hover:text-sky-400">
            {REPO}
          </a>
        </div>
      </div>
    </div>
  );
}
