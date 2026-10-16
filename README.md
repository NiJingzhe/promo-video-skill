# promo-video

A Claude Code skill that makes a beat-synced product promo film end to end, with a human in the loop: pick music (Epidemic Sound "Create a cut") → design the storyboard → voice-over script for ElevenLabs → cut the take → build in Remotion (three.js metal renders, product-UI replicas, camera moves, every cut on the beat) → review the render in the browser.

Browser tools included: a waveform page for cutting the voice-over by clicking between the script's lines, and a review page (monitor + timeline strip, notes attached to exact frames).

```bash
npx skills add NiJingzhe/promo-video-skill
```

Needs `ffmpeg`, `node` 20+ and [`uv`](https://docs.astral.sh/uv/). Chinese guide below.

---

# promo-video · 做一支踩点的产品宣传片

> 一个 Claude Code skill：你和 Claude 一起，从选音乐开始，到出片。画面的每一次切换都踩在音乐的拍点上，旁白和画面严丝合缝。

## 你会得到什么

- 一支 30–60 秒、1080p60 的宣传片（H.264 mp4）
- 配套文件：分镜文档 `PLAN.md`、给 ElevenLabs 的带标记旁白脚本 `elevenlabs.md`、切好的旁白、整个 Remotion 工程（可以随时改、重渲）

## 你要做的只有这几件事（其余交给 Claude）

| 步骤 | 你 | Claude |
|---|---|---|
| **1. 选音乐** | 在 [Epidemic Sound](https://www.epidemicsound.com) 选一首曲子（无版权，可商用）。点曲目上的 **小剪刀图标 → “Create a cut”**，它会从原曲里剪出一个**流畅、自然收尾的指定时长版本**（比如 45 秒）。下载 wav/mp3 给 Claude。 | 分析曲子：真实 BPM、拍点、小节线、哪里是 drop / 停顿 / 渐强 |
| **2. 设计分镜** | 回答 Claude 的几个问题（产品是什么、要给谁看、想要什么感觉、必须出现什么）。看一眼分镜表，点头或改。 | 写 `PLAN.md`：每个镜头几点几秒、画面是什么、踩哪一拍 |
| **3. 旁白** | 去 [ElevenLabs](https://elevenlabs.io) 选一个合适的声音，把 Claude 给你的整段脚本（带 `<break>` 标记）**一次**生成完。把音频发给 Claude。 | 写旁白（如果需要）和 ElevenLabs 脚本 |
| **3b. 切分旁白** | Claude 会弹出一个浏览器页面：右边是**旁白脚本逐句列出**，中间是整段录音的波形（有声与停顿分开显示）。按空格播放，**每听到一句结束，就在停顿处点一下（或按 C）**切一刀；当前听到的是哪一句会高亮。可缩放、撤销重做。点 **Done**，页面自己关闭。 | 读取你的切分结果，切成一句一句，调到同样的响度，排到画面上 |
| **4. 看初稿** | 看 Claude 发来的关键帧截图和草稿，提意见（“这里慢一点”“这个太假”）。 | 用 Remotion + three.js 制作：写实金属渲染、产品界面复刻、镜头推拉摇移 |
| **5. 审片** | Claude 弹出审片页：上方是监视器，下方是时间线条（画面缩略图 + 成片音频波形 + 节拍/旁白标注）。边看边按 **M** 在当前画面上留一条备注（拖一段可标范围），最后选“通过”或“需要修改”。每条备注都自带当时那一帧。 | 看每条备注和对应画面，修好、重渲、再请你审，直到通过 |

- 需要的话，同一个编辑器也能在音乐波形上**标记 drop / 停顿 / 渐强**等关键点（会吸附到节拍网格）。

## 让 Claude 帮你操作网站（可选）

如果装了 `ego-browser`、Playwright 之类的浏览器自动化工具，Claude 会**先征求你同意**，再替你在 Epidemic Sound 找曲、点 “Create a cut” 下载，在 ElevenLabs 粘贴脚本、生成并下载旁白。需要知道的：

- **要有账号**：Epidemic Sound 需订阅（有试用）；ElevenLabs 有免费额度。账号你自己注册，Claude 不代注册。
- **可能产生费用**：ElevenLabs 按字符计费，一支片子约六七百到一千字符，重新生成会重复计费；Claude 会先告诉你预估花费，等你同意。
- **登录和付款永远由你来**：需要登录、验证码、付款时，浏览器交还给你，完成后再继续；Claude 不输入你的密码和银行卡。
- **选择权在你**：曲子和声音由你定，Claude 只负责筛出几个候选。

## 小贴士

- **音乐先行**。画面都是按音乐定的，换曲子等于重做。选定之后再往下走。
- **“Create a cut”比自己剪好**：它理解曲子的结构，剪出来的版本有完整的开头和结尾，不会在半拍里被切断。需要更短的版本时，让 Claude 用工具剪（它会对齐小节线并交叉淡化，并验证接缝）。
- **真实 > 好看**：画面里的模型、代码、界面都用你产品里真实的东西。给 Claude 一个仓库路径就行。
- **旁白不必每句都用**。想压缩时长，Claude 会挑关键几句，其余让音乐说话。

## 开始

对 Claude 说：**“用 promo-video 给 <产品名> 做个宣传片，大概 40 秒。”**

Claude 会先问你音乐，再往下走。目录结构、脚本和技术细节见 [SKILL.md](SKILL.md) 与 `references/`。
