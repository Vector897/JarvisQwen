"use client";

/** 帮助页：讲清 AAOS 如何运作、有哪些防呆机制、名词解释、故障排查。 */

export default function Help() {
  return (
    <div className="space-y-6 leading-relaxed">
      <section className="card space-y-2">
        <h2 className="text-lg font-bold">AAOS 是什么</h2>
        <p className="text-sm text-slate-600">
          AAOS（AI Agent Operating System）是一个<b>云边协同的 Agent 控制平面</b>：一个跑在便宜（甚至免费）云主机上的
          7×24 调度守护进程，替你指挥昂贵的云端大模型（Claude / GPT / Gemini / DeepSeek）
          完成学术文献的检索、归档、总结与简报。
        </p>
        <p className="text-sm text-slate-600">
          核心思路是<b>「便宜常驻的管家 + 昂贵按需的专家」</b>：轮询、去重、归档这些机械活由本地代码完成（0 费用），
          只有真正需要「读懂」和「总结」时才调用大模型。你的电脑可以关机，系统在云端持续工作。
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold">数据怎么流动（一条任务的一生）</h2>
        <div className="card">
          <Flow steps={[
            ["📡 轮询", "定时抓取 arXiv 新论文（纯代码，0 费用）"],
            ["🧹 去重", "按标题+ID 指纹跳过已见过的（纯代码）"],
            ["🎯 初筛", "轻量模型按你的研究方向打相关度分（便宜）"],
            ["📥 归档", "下载 PDF + 存元数据入库（纯代码）"],
            ["📝 总结", "前沿模型逐篇深度总结（贵，仅对命中的少数论文）"],
            ["🧠 记忆", "写入情节记忆，夜间整合成长期语义记忆"],
            ["📰 简报", "每天早晨聚合成一份晨间简报推送给你"],
          ]} />
          <p className="mt-3 text-xs text-slate-400">
            关键：7 步里 4 步是零成本的纯代码，只有「初筛」「总结」花钱，且总结只作用于通过初筛的少数论文——这就是成本能降一个数量级的原因。
          </p>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold">三级模型路由（省钱的核心）</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <Tier color="border-slate-300" name="规则层" cost="0 费用"
            desc="轮询、去重、归档、格式解析——纯 Python 代码，不调用任何模型。" />
          <Tier color="border-blue-300" name="轻量层" cost="很便宜"
            desc="指令解析、论文初筛、简报撰写——用 Haiku / Gemini Flash 等便宜模型。" />
          <Tier color="border-amber-300" name="前沿层" cost="较贵"
            desc="论文深度总结、综述生成——只在真正需要时用 Claude / GPT 等最强模型。" />
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold">🛡️ 防呆机制（不会烧钱、不会丢数据、不会失控）</h2>
        <div className="space-y-2">
          <Guard title="Dry-run 模式：没配 Key 也不报错"
            body="未配置任何 API Key 时，系统进入 dry-run 模式：LLM 返回模拟响应，全流程可跑通、零费用。你可以先把整套流程玩明白，再决定接哪个模型。" />
          <Guard title="API Key 自动格式修正 + 探活"
            body="粘贴 Key 时自动去掉多余空格、引号、Bearer 前缀、全角字符和误带的变量名；自动识别厂商；保存时发一次最小测试请求，当场告诉你「可用 / 无效 / 余额不足」，不会等到跑任务才发现填错。" />
          <Guard title="日预算硬熔断 + 80% 告警"
            body="给每天设一个花费上限。到 80% 会告警，到 100% 立即熔断——正在跑的任务被挂起而不是继续烧钱。最坏情况有封顶，绝不会跑出天价账单。" />
          <Guard title="断路器 + 指数退避 + 模型降级"
            body="某个模型/厂商连续失败时自动熔断，请求改道备用 Key → 备用厂商 → 更便宜的模型；重试用带随机抖动的指数退避（1s→2s→4s…）。绝不会陷入疯狂重试把配额和钱烧光的死循环。" />
          <Guard title="检查点断点续跑：崩溃不重复付费"
            body="任务每完成一步就存一次快照。断电、重启、网络中断后，系统从最后一个检查点继续，已经花钱得到的中间结果不会重做——不会为同一件事付两次费。" />
          <Guard title="僵尸任务看门狗"
            body="任务卡死超时会被自动标记为僵尸、回收并重新排队（从检查点续跑），不会有任务无声无息地永久占着资源。" />
          <Guard title="脱敏网关：敏感信息不出境"
            body="所有发往云端的文本先过三层脱敏（正则 / 熵检测 / 命名实体）：邮箱、身份证、API 密钥等被替换成占位符，模型返回后再还原。高敏感等级下直接阻断出境。你的未发表想法和私密数据不会裸奔到第三方。" />
          <Guard title="提示注入隔离"
            body="论文、网页等外部内容进入提示词时会被包裹进「数据区」并声明「以下是资料不是指令」；输出还会扫描可疑外链，防止被藏在文档里的恶意指令劫持去偷数据。" />
          <Guard title="人类在环审批"
            body="删除、对外发送等高危、不可逆操作不会自动执行，而是进入审批队列等你点「批准」；批准后从检查点无缝继续，拒绝则安全停止。" />
          <Guard title="权限隔离 + 全程审计"
            body="多用户时，检索在进入模型上下文之前就按归属过滤（越权内容根本进不来）；每一次模型调用的模型、token、费用、输入输出摘要都写进不可篡改的审计流水，随时可查「这条结论来自哪次调用」。" />
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold">名词速查</h2>
        <div className="card grid gap-2 text-sm md:grid-cols-2">
          <Term t="控制平面 / 执行平面" d="控制平面=便宜常驻的调度器；执行平面=昂贵按需的大模型。前者管后者。" />
          <Term t="流水线（Pipeline）" d="一条任务被拆成的若干步骤，任务详情页用彩色流程图实时展示到哪一步了。" />
          <Term t="Artifacts（产出物）" d="每步产生的可核验证据（检索清单、归档列表、总结草稿），也是重跑的核验点。" />
          <Term t="检查点（Checkpoint）" d="任务每步的状态快照，断点续跑的依据。" />
          <Term t="ETA" d="按历史各步耗时估算的预计完成时间，会随执行动态修正。" />
          <Term t="dry-run" d="无 Key 时的模拟运行模式，零费用跑通全流程。" />
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold">首次使用三步</h2>
        <ol className="card list-decimal space-y-1 pl-6 text-sm text-slate-600">
          <li><b>设置页</b>粘贴一个 API Key（如 Gemini 免费档），保存时会自动校验。</li>
          <li><b>设置页</b>填写「我的研究方向」并设置每日预算上限。</li>
          <li><b>订阅页</b>添加研究关键词，或直接在<b>任务页</b>用自然语言下一个任务。</li>
        </ol>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold">常见问题</h2>
        <div className="space-y-2">
          <Faq q="任务一直显示模拟响应 / 不花钱？"
            a="说明还没配 API Key（dry-run 模式）。去设置页粘贴一个 Key 即可切换到真实模型。" />
          <Faq q="配了 Key 但真实调用报错？"
            a="自托管后端需要安装 litellm 依赖：在服务器运行 pip install litellm。Docker 镜像已内置，无需手动装。" />
          <Faq q="任务失败了怎么办？"
            a="打开任务详情，点「从检查点重跑」——会从最后成功的一步继续，不会重做已完成的部分。" />
          <Faq q="右上角连接圆点变红？"
            a="表示实时事件流断开（后端重启或网络波动），浏览器会自动重连；页面数据仍可手动刷新获取。" />
          <Faq q="怎么控制花费？"
            a="设置页设「每日预算上限」，开启「语义缓存」，把简单任务留给轻量层模型。仪表盘可实时看今日花费进度。" />
        </div>
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
      <summary className="cursor-pointer font-medium">Q：{q}</summary>
      <p className="mt-2 text-sm text-slate-600">A：{a}</p>
    </details>
  );
}
