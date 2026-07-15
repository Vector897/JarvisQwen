"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { api } from "@/lib/api";
import { useLang } from "@/lib/i18n";

/** Mobile remote-control page: two QR codes — (1) Telegram for issuing tasks, (2) GitHub repository (share/upgrade). */

const REPO = "https://github.com/Vector897/JarvisQwen";

// Contact tiles with inline (self-contained) brand marks.
const CONTACTS: { label: string; href: string; icon: React.ReactNode }[] = [
  {
    label: "Email",
    href: "mailto:EIITF@outlook.com",
    icon: (
      <svg viewBox="0 0 24 24" width="80" height="80" fill="none" stroke="#2563eb" strokeWidth="1.8" aria-hidden="true">
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="m3 7.5 9 6 9-6" />
      </svg>
    ),
  },
  {
    label: "GitHub",
    href: "https://github.com/Vector897",
    icon: (
      <svg viewBox="0 0 24 24" width="80" height="80" fill="currentColor" aria-hidden="true">
        <path d="M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.86 10.92c.58.11.79-.25.79-.56v-2c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.3-1.7-1.3-1.7-1.05-.72.08-.71.08-.71 1.17.08 1.78 1.2 1.78 1.2 1.04 1.78 2.73 1.27 3.4.97.1-.76.4-1.27.73-1.56-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .98-.31 3.2 1.18a11.1 11.1 0 0 1 5.83 0c2.22-1.49 3.2-1.18 3.2-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.7 5.4-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.2.68.8.56A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5Z" />
      </svg>
    ),
  },
  {
    label: "Devpost",
    href: "https://devpost.com/aigc-vm-uk",
    icon: (
      <svg viewBox="0 0 24 24" width="80" height="80" aria-hidden="true">
        <path fill="#003E54" d="M6.3 3h11.4L23 12l-5.3 9H6.3L1 12z" />
        <text x="12" y="15.6" textAnchor="middle" fontSize="9" fontWeight="700" fill="#fff" fontFamily="Arial, sans-serif">D</text>
      </svg>
    ),
  },
  {
    label: "YouTube",
    href: "https://www.youtube.com/@OrionVector",
    icon: (
      <svg viewBox="0 0 24 24" width="80" height="80" aria-hidden="true">
        <path fill="#FF0000" d="M23.5 6.5a3 3 0 0 0-2.1-2.12C19.5 3.8 12 3.8 12 3.8s-7.5 0-9.4.58A3 3 0 0 0 .5 6.5 31.3 31.3 0 0 0 0 12a31.3 31.3 0 0 0 .5 5.5 3 3 0 0 0 2.1 2.12c1.9.58 9.4.58 9.4.58s7.5 0 9.4-.58a3 3 0 0 0 2.1-2.12A31.3 31.3 0 0 0 24 12a31.3 31.3 0 0 0-.5-5.5Z" />
        <path fill="#fff" d="M9.6 15.5V8.5l6.2 3.5Z" />
      </svg>
    ),
  },
];

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
        {/* (1) Telegram remote control */}
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
          <p className="border-t border-slate-100 pt-3 text-xs text-slate-400 dark:border-slate-800">
            {L(
              "Channels today: Telegram (two-way) and email notifications. WhatsApp and Slack are on the roadmap.",
              "当前支持的渠道：Telegram（可双向收发）与邮件通知。WhatsApp、Slack 等更多渠道已在路线图上。"
            )}
          </p>
        </section>

        {/* (2) GitHub repository */}
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

      {/* (3) Contact / follow — reach a real human */}
      <section className="card space-y-3">
        <h2 className="text-lg font-semibold">💬 {L("Have questions? Get in touch", "有问题？直接找我")}</h2>
        <p className="text-sm text-slate-500">
          {L("Didn't find your answer? I'm a real person — reach me on any of these.",
             "没找到答案？真人回复，以下任意方式都能找到我。")}
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {CONTACTS.map((c) => (
            <a key={c.label} href={c.href}
              target={c.href.startsWith("mailto:") ? undefined : "_blank"}
              rel="noopener noreferrer"
              className="flex aspect-square flex-col items-center justify-center gap-2 rounded-xl border border-slate-200 p-3 text-center text-xs font-medium text-slate-600 transition hover:-translate-y-0.5 hover:border-slate-300 hover:bg-slate-50 hover:shadow-sm dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
              {c.icon}
              <span>{c.label}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
