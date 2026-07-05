"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { api } from "@/lib/api";
import { useLang } from "@/lib/i18n";

/** 手机遥控页：两个二维码——① Telegram 遥控下任务 ② GitHub 仓库(分享/升级)。 */

const REPO = "https://github.com/Vector897/JarvisQwen";

export default function Connect() {
  const [bot, setBot] = useState<any>(null);
  const { lang } = useLang();
  const L = <T,>(en: T, zh: T): T => (lang === "zh" ? zh : en);

  useEffect(() => { api("/api/telegram/bot").then(setBot).catch(() => setBot({ configured: false })); }, []);

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500">
        {L("Your autopilot shouldn't need a laptop. Scan, and take it with you.",
           "自动驾驶不该被绑在电脑前。扫一下,把它装进口袋。")}
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ① Telegram 遥控 */}
        <section className="card space-y-4">
          <h2 className="text-lg font-semibold">📲 {L("Command by Telegram", "Telegram 遥控下任务")}</h2>
          <p className="text-sm text-slate-500">
            {L(
              "Scan with your phone camera, tap START, then just text the bot what you want — in plain language. JarvisQwen queues the task, runs the full pipeline, and replies when it's on it.",
              "手机相机扫码 → 点 START → 直接用大白话给 bot 发消息。JarvisQwen 会把消息变成任务排队执行,并回复确认。"
            )}
          </p>
          {bot?.configured && bot?.username ? (
            <div className="flex flex-col items-center gap-3 py-2">
              <div className="rounded-2xl bg-white p-4 shadow-inner ring-1 ring-slate-200">
                <QRCodeSVG value={`https://t.me/${bot.username}`} size={180} level="M" />
              </div>
              <a href={`https://t.me/${bot.username}`} target="_blank" rel="noreferrer"
                 className="font-mono text-sm text-blue-600 hover:underline">@{bot.username}</a>
              <div className="w-full rounded-lg bg-slate-50 p-3 text-xs text-slate-500 dark:bg-slate-800">
                {L("Try texting:", "试着发一句:")}
                <div className="mt-1 space-y-0.5 font-mono text-slate-600 dark:text-slate-300">
                  <div>Track new papers on LLM agent security</div>
                  <div>Generate today&apos;s briefing</div>
                </div>
              </div>
              <p className="text-xs text-slate-400">
                🔒 {L(
                  "Only messages from YOUR configured chat are accepted — anyone else scanning this QR cannot command your system.",
                  "只接受你在设置页配置的那个 chat 发来的指令——其他人扫到这个码也无法指挥你的系统。"
                )}
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
              <p className="font-medium">{L("Not set up yet — 3 steps, ~2 minutes:", "还没配置——三步,约 2 分钟:")}</p>
              <ol className="mt-2 list-decimal space-y-1 pl-5">
                <li>{L(<>In Telegram, message <b>@BotFather</b>, send <code>/newbot</code>, follow the prompts, copy the token.</>, <>Telegram 里找 <b>@BotFather</b>,发送 <code>/newbot</code> 按提示创建,复制 token。</>)}</li>
                <li>{L(<>Message <b>@userinfobot</b> to get your numeric chat ID.</>, <>给 <b>@userinfobot</b> 发条消息,拿到你的数字 chat ID。</>)}</li>
                <li>{L(<>Paste both in <Link href="/settings" className="underline">Settings → Notifications</Link> and enable Telegram.</>, <>把两者填进<Link href="/settings" className="underline">设置页 → 通知</Link>并启用 Telegram。</>)}</li>
              </ol>
              <p className="mt-2 text-xs opacity-70">{L("This page will show the QR code automatically once configured.", "配置完成后本页会自动显示二维码。")}</p>
            </div>
          )}
        </section>

        {/* ② GitHub 仓库 */}
        <section className="card space-y-4">
          <h2 className="text-lg font-semibold">⭐ {L("The project, in one scan", "项目仓库二维码")}</h2>
          <p className="text-sm text-slate-500">
            {L("This QR points to the JarvisQwen GitHub repository. Two things it's for:",
               "这个码指向 JarvisQwen 的 GitHub 仓库,两个用途:")}
          </p>
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            <li>🎁 <b>{L("Share it", "推荐给别人")}</b> — {L(
              "someone likes what they see over your shoulder? They scan, they own one too. Free, open-source, MIT.",
              "有人看到你的屏幕感兴趣?扫一下,TA 也能拥有一套。免费、开源、MIT 协议。")}</li>
            <li>⬆️ <b>{L("Upgrade yours", "升级你的部署")}</b> — {L(
              "new versions ship regularly. Open the repo, follow the Deploy page prompt, and your local copy updates itself.",
              "新版本持续发布。打开仓库,配合「一键部署」页的提示词,即可让 AI 帮你把本地版本升到最新。")}</li>
          </ul>
          <div className="flex flex-col items-center gap-3 py-2">
            <div className="rounded-2xl bg-white p-4 shadow-inner ring-1 ring-slate-200">
              <QRCodeSVG value={REPO} size={180} level="M" />
            </div>
            <a href={REPO} target="_blank" rel="noreferrer"
               className="font-mono text-xs text-blue-600 hover:underline">{REPO}</a>
            <Link href="/deploy" className="btn-ghost text-xs">🚀 {L("Go to one-click deploy →", "去一键部署页 →")}</Link>
          </div>
        </section>
      </div>
    </div>
  );
}
