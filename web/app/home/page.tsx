"use client";

import Link from "next/link";

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
  return (
    <div className="mx-auto max-w-3xl">
      <div className="overflow-hidden rounded-3xl bg-[#05070d] text-slate-200 shadow-2xl ring-1 ring-slate-800">
        {/* Hero */}
        <div className="flex flex-col items-center px-6 pt-10 text-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-full.png" alt="JarvisQwen — AI Butler System" className="w-72 max-w-full" />
          <p className="mt-2 text-sm tracking-widest text-sky-400/80">YOUR 24/7 AI BUTLER · POWERED BY QWEN</p>
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

        {/* CTA */}
        <div className="flex flex-wrap justify-center gap-3 border-t border-slate-800/80 px-8 py-8">
          <Link href="/dashboard"
            className="rounded-xl bg-sky-500 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-400">
            Open the console →
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
      </div>
    </div>
  );
}
