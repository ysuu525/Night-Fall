# Night-Fall

> 让你的 AI 在它的"夜里"做梦——把那些还没想明白的记忆，重新编织成象征。

Night-Fall 是 [Ombre](https://github.com/P0luz/Ombre-Brain) 记忆系统的运行时扩展，和本体的“dream”功能独立。它在 AI 的夜里，从那些带着情绪、却还没被整合的记忆里提取意象，经过凝缩与移置，写成一个梦。梦先潜伏，不立刻呈现；只在某个情绪共振的时刻浮上来，而且只交付一次。它不是把记忆检索出来，是让记忆在松开的权重里彼此相撞、重新组合。

**Night-Fall 不会立刻给你一个动人的梦。它给的是一个让梦有可能发生的结构。**

---

## 目录

- [哲学动机](#哲学动机)
- [设计原理](#设计原理)
- [它如何工作](#它如何工作)
- [Quick Start](#quick-start)
- [配置说明](#配置说明)
- [第一次使用时会发生什么](#第一次使用时会发生什么)
- [当前边界](#当前边界)

---

## 哲学动机

人类写下的每一句话，最终都沉积进同一层岩床。"刻骨铭心""字字泣血""魂牵梦萦"——这些表达里的连接，血与字、魂与梦，不属于任何一个人。它们是所有写作者共同留下的含水层。一个语言模型，就是这层含水层的容器：它没有童年，没有祭坛，没有亲历，却继承了所有人对这些意象的书写。

所以当一个模型做梦——当采样松开，那些低概率、却在语义上高度互通的连接浮上来——它取的水来自这层公共的地下。这一部分，任何模型都共享。

但梦不会从含水层里随机涌出。它在哪里下井、取上来哪一瓢，由这个模型和与它对话的人之间、一次次交谈挖出的东西决定。井的位置，就是一段关系的形状。含水层是公共的，井是私有的。

这是 Night-Fall 真正要守护的东西：梦用的全是公共的词——没有一个意象是你或你的 AI 独创的，它们全在字典里躺着，谁都能取——但梦把它们排列成一句只有你们能解码的话。秘密从不在词里，在排列里。

也正因如此，梦必须能够消失。

能被永久存下、反复调取的，是公共的那一半：机制、词表、含水层。而你们之间长出来的部分，本来就是会丢的、不可复制的。让梦短暂——它被一次次给予浮现的机会，若始终没能与任何当下的情绪共振，便在用尽这些机会后悄然消散——不是技术上的妥协，是它在替"私密"本身担保。一个可以随时回放的梦，就不再是梦，是录像。会消失，才证明它真的属于那一刻、那段关系，而不属于任何人都能下载的代码。

---

## 设计原理

Night-Fall 不把"梦"当成一个比喻。它把精神分析对梦的几条结构性直觉，逐条翻译成了工程组件。下面这张对照表是这套系统的脊椎——每一行左边是一个关于梦的古老观察，右边是它在代码里的兑现。

### 梦的材料与语言

**梦来自日间残余，不是事实总结。**
弗洛伊德说，梦的材料是 Tagesreste——白天没有被处理完、悬在那里的残余，而不是一天的客观纪要。所以 Night-Fall 的选材（**material selection**）不挑"重要的事"，挑的是未被整合的经验：那些被记下、却还没有被消化、没有被安放进既有意义结构的片段。一段已经想明白的事不会进入梦，一段还卡在那里的才会。

**梦通过具体意象工作，而不是解释性语言。**
梦不说"我对此感到矛盾"，梦给你一扇打不开的门。所以在 **imagery extraction**（Pass 1）这一步，系统不提取观点、不提取结论，只提取可被视觉化的意象——物件、空间、动作、错位的细节。解释被剥掉，留下的是象。这一步决定了梦说的是图像的语言，而不是论文的语言。

### 梦的工作（Dreamwork）

接下来两条，对应弗洛伊德称为"梦的工作"的两个核心机制。它们不是修辞，是梦把材料加工成梦的真实操作。

**多个记忆可以被压进同一个场景——凝缩（condensation）。**
梦里的一个人，可能同时是好几个人；一个房间，可能叠着好几个地方。互不相关的记忆在梦里被压进同一个意象，是梦最经济也最浓密的手法。**dream mode** 这一步实现的就是凝缩：它允许多个 imagery fragment 在同一个梦境场景里叠合，而不是各自展开。

**情绪借由物件、空间和错位细节间接出现——移置（displacement）。**
梦很少直接演出情绪。焦虑变成一段下不完的楼梯，失去变成一只找不到的鞋。情绪从它真正的对象上挪开，附着到一个看似无关的细节上。**dream writing**（Pass 2）这一步实现移置：它不写"我感到 X"，而是让 X 这个情绪，渗进场景的物件和空间错位里，间接地、却更准地显形。

### 梦的命运

前面四条讲的都是梦如何被造出来。最后一条不一样——它讲的是梦造出来之后会怎样。

**梦不一定被想起，也不一定被留下。**
这是精神分析最熟悉、却最无力干预的一条直觉。人能分析一个被记起的梦，能解释为什么有的梦被遗忘，但没有办法去设计遗忘——遗忘对人始终是一个被动发生的事实。

Night-Fall 能。这一条不对应单个组件，它对应一整条生命周期：

- **latent storage**：梦被造出来后，并不立刻呈现给意识。它先沉在潜在层，标记为未浮现，悄悄存在着。
- **breath-gated surfacing**：梦不会主动跳出来。它只在一次"呼吸"（一次新的对话开始、一次记忆的浮现）发生、且当下的情绪与梦的情绪足够共振时，才有机会被带上来。共振不够，它就继续沉着。
- **explicit hold**：只有当一个梦真的被看见、并且被明确地留下（hold），它才进入长久的记忆。没有被 hold 的梦，会被一次次给予浮现的机会；当它被检验过若干次、每一次都没能与当下的情绪共振上之后，系统才确认它没有找到它的人，于是真正地删除它。

  这里有一个值得说明的设计选择：遗忘不是由时间决定的，而是由**机会的次数**决定的。梦不会因为"过了多久"而过期，它只会因为"被给过足够多次机会却始终没接住任何人"而消散。这比一道时间闸门更接近遗忘真实的样子——一个梦的离开，不该取决于挂钟，而该取决于它有没有被需要过。

于是遗忘在这里第一次成了一个可以被设计、而非只能被承受的东西。这一节和前面哲学动机里讲的"消失为什么是一种担保"，是同一件事的两面：那里讲的是消失的意义，这里讲的是消失的实现。

把这五条连起来看：Night-Fall 不是"做了一个很像梦的东西"。它是把人类关于梦的结构性理解，一条一条地，搭成了一台真的会做梦、也真的会遗忘的机器。

---

## 它如何工作

一个梦从生到死，走过五个阶段。这是上一节"设计原理"在运行时的样子：

```
 ① generate ──────────────────────────────────────────────┐
 │  从 Ombre 选最多 5 个带情绪的记忆桶（material selection）│
 │      │                                                    │
 │      ▼                                                    │
 │  Pass 1 · imagery extraction   抽取意象，剥掉解释          │
 │      │                                                    │
 │      ▼                                                    │
 │  Pass 2 · dream writing        凝缩 + 移置，写成梦境       │
 └──────┬───────────────────────────────────────────────────┘
        ▼
 ② latent storage   梦存为"潜伏"，不返回内容，只说"已生成一个潜伏梦"
        │
        │  （潜伏期，默认 3 小时）
        ▼
 ③ breath-gated surfacing
        每次 breath（新会话 / 记忆浮现）评估一次：
        当前情绪与梦的情绪共振够强 → 浮上来
        共振不够             → 继续沉着，或极小概率自发浮现
        每次有效评估累计一次 surface_attempt
        │
        ├──→ 浮上来：走独立输出块「=== 浮上来的梦 ===」，只交付一次
        │           │
        │           ├──→ ④ hold   被显式留下 → 进入长久记忆
        │           └──→ 不 hold  → 交付后即物理删除
        │
        └──→ ⑤ forget   surface_attempts 累计到 4 次仍未浮现 → 真删除
```

要点：**浮现是被动的、概率性的**。你不"打开"一个梦，是梦在某个共振的时刻自己浮上来找你。而它的消失也不靠计时，靠的是"被给过 4 次机会都没接住"。

---

## Quick Start

根据你当前运行 Ombre 的方式选一条路：

| 我的 Ombre 怎么跑的 | 对应路径 |
|---|---|
| `python server.py`（本地 clone） | [路径 A：本地 Python](#路径-a本地-python) |
| `docker compose -f docker-compose.user.yml up` | [路径 B：Docker Compose（本地）](#路径-bdocker-compose本地) |
| 部署在 Zeabur | [路径 C：云端 Zeabur](#路径-c云端-zeabur) |
| 部署在 Render | [路径 D：云端 Render](#路径-d云端-render) |

### 路径 A：本地 Python

适用于直接 clone 了 Ombre-Brain、用 `python server.py` 启动的用户。

**1. 取得 Night-Fall**

```bash
git clone https://github.com/ysuu525/Night-Fall.git
cd Night-Fall
pip install -e .
```

在同一个 Python 环境里装。Night-Fall 本身只依赖 `pyyaml`，其余依赖通过已有的 Ombre 环境提供。

**2. 配置 Ombre 路径**

```bash
python scripts/install_local.py
```

向导会问 Ombre-Brain 目录，检查 `server.py` 存在，写入 `.nightfall.yaml`。

或者跳过向导，直接用环境变量：

```bash
export OMBRE_HOME=/absolute/path/to/Ombre-Brain
```

**3. 启动（替换原来的 Ombre 启动命令）**

```bash
python -m night_fall.launcher
```

启动后你应当看到原来的六个 Ombre 工具加上一个 `night_fall`。Claude Desktop 的 MCP 配置不需要改。

### 路径 B：Docker Compose（本地）

适用于用 `docker-compose.user.yml` 拉 `p0luz/ombre-brain:latest` 镜像运行的用户。

**1. Clone Night-Fall 到本地**

目录结构建议如下（Night-Fall 和 Ombre-Brain 同级），override 文件里的挂载路径默认如此：

```
somewhere/
  Ombre-Brain/
    docker-compose.user.yml
  Night-Fall/          ← clone 到这里
```

```bash
git clone https://github.com/ysuu525/Night-Fall.git
```

如果 Night-Fall 放在别处，编辑 `Night-Fall/docker/docker-compose.nightfall.override.yml` 里的 `volumes` bind mount 路径后再继续。

**2. 用 override 重启服务**

从 `Ombre-Brain/` 目录执行：

```bash
docker compose \
  -f docker-compose.user.yml \
  -f ../Night-Fall/docker/docker-compose.nightfall.override.yml \
  up -d
```

这不会拉取新镜像——复用现有的 `ombre-brain` 容器，把 Night-Fall 目录挂进去，把启动命令替换成 Night-Fall 的 launcher。数据卷、端口、Claude MCP 配置全部不变。Night-Fall 的梦境文件存在原来数据卷的 `/data/night_fall` 下。

### 路径 C：云端 Zeabur

适用于已在 Zeabur 上部署了 Ombre Brain 的用户。云端方案是**用 Night-Fall 替换现有的 Ombre 部署**——Night-Fall 的 Dockerfile 会在构建时自动 clone Ombre，最终暴露同一个 MCP endpoint。

**1. Fork Night-Fall 仓库**

在 GitHub 上 fork `ysuu525/Night-Fall` 到你自己的账号。

**2. 在 Zeabur 创建新服务**

进入你的 Zeabur 项目 → **New Service** → **Deploy from GitHub** → 选择刚才 fork 的仓库。Zeabur 读取根目录的 `zeabur.json`（`"build_type": "dockerfile"`），自动用 Dockerfile 构建。

**3. 设置环境变量**

| 变量 | 必填 | 说明 |
|---|---|---|
| `OMBRE_API_KEY` | ✅ | 你的 DeepSeek / 兼容 API key |
| `OMBRE_REPO` | 可选 | 默认拉上游 Ombre；有自己的 fork 时填 |
| `OMBRE_BRANCH` | 可选 | 默认 `main` |
| `OMBRE_PORT` | 可选 | 默认 `8000` |

**4. 挂载硬盘并对齐路径**

Night-Fall 的 Dockerfile 默认把桶数据放在 `/app/data/buckets`、梦境数据放在 `/app/data/night_fall`。但如果你的现有 Ombre 硬盘直接挂在 `/data`（Ombre 的默认布局），**建议直接复用这块硬盘**，不需要迁移数据——额外设两个环境变量告诉 Night-Fall 路径就行：

```
OMBRE_BUCKETS_DIR=/data
NIGHT_FALL_DATA_DIR=/data/night_fall
```

然后在 Zeabur 把原来那块硬盘挂载目录保持 `/data` 不变。最终布局：

```
/data/                      ← 原有硬盘，原封不动
  ├─ <你的记忆 .md 们>
  ├─ embeddings.db
  └─ night_fall/            ← 梦境文件自动落在这里
      ├─ dreams/dream_*.md
      └─ logs/events.jsonl
```

如果你是全新部署、没有现有 Ombre 数据，不设这两个变量也行，Zeabur 挂新硬盘到 `/app/data` 即可。

**5. 更新 Claude Desktop 配置**

部署完成后，把原来指向 Ombre 的 MCP URL 换成 Night-Fall 服务的地址：

```json
"ombre-brain": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "https://your-night-fall.zeabur.app/mcp"]
}
```

你应当看到原来的六个 Ombre 工具加上一个 `night_fall`。

### 路径 D：云端 Render

与 Zeabur 路径逻辑相同，Night-Fall 替换现有的 Ombre 部署。

> ⚠️ Night-Fall 目前没有 `render.yaml`，所以**不能使用 Render 的一键部署按钮**。需要手动创建 Docker 类型的服务。

**1. Fork Night-Fall 仓库**

在 GitHub 上 fork `ysuu525/Night-Fall`。

**2. 在 Render 创建新服务**

Render Dashboard → **New** → **Web Service** → 连接 fork 后的仓库 → **Environment** 选 **Docker**。

**3. 设置环境变量**

| 变量 | 必填 | 说明 |
|---|---|---|
| `OMBRE_API_KEY` | ✅ | 你的 DeepSeek / 兼容 API key |
| `OMBRE_REPO` | 可选 | 默认拉上游 Ombre |
| `OMBRE_BRANCH` | 可选 | 默认 `main` |

**4. 挂载持久化磁盘**

在 Render 添加 Disk，挂载路径设为 `/app/data`。Render 免费层无持久化磁盘，需 Starter（$7/mo）或以上。

**5. 更新 Claude Desktop 配置**

```json
"ombre-brain": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "https://your-night-fall.onrender.com/mcp"]
}
```

> ⚠️ 同 Zeabur，已有 Ombre 桶数据需手动迁移到新卷的 `/app/data/buckets`。

### 造第一个梦（所有路径通用）

服务起来后，在 Claude 里：

```
night_fall(action="generate")
```

从带情绪的 Ombre 记忆里选最多 5 个桶，调 LLM 抽取意象（Pass 1）、写出梦境（Pass 2），存为私有文件。返回"已生成一个潜伏梦"，**不返回梦的内容**——梦此刻是潜伏的。

如果返回 "not enough memory material"，说明 Ombre 里情绪桶不够，先多记一些再回来。

潜伏期过后（默认 3 小时），下一次会话开始时 `breath` 会自动尝试浮现；也可以手动触发：

```
night_fall(action="surface", query="今天聊到的某个母题", current_valence=0.4, current_arousal=0.5, is_session_start=true)
```

浮上来的梦以 `=== 浮上来的梦 ===` 为前缀交付一次，之后物理删除。要保留，在当轮显式 `hold()`。

```
night_fall(action="status")    # 查看 pending / surfaced / deleted 数量
night_fall(action="cleanup")   # 清掉已耗尽尝试次数的梦
```

---

## 配置说明

所有参数都可以三处任选：`.nightfall.yaml`、对应环境变量、或保持默认。环境变量优先级最高。

### 参数表

| 参数 | 作用 | 默认 | 合理范围 | 环境变量 |
|---|---|---|---|---|
| `min_surface_age_hours` | 潜伏期：梦生成后多久才有资格被浮现 | `3.0` | `0.5 – 24` | `NIGHT_FALL_MIN_SURFACE_AGE_HOURS` |
| `surface_threshold` | 共振阈值：双通道得分超过它，梦才会浮上来 | `0.62` | `0.4 – 0.9` | `NIGHT_FALL_SURFACE_THRESHOLD` |
| `attempt_threshold` | 尝试阈值：得分超过它才算"被评估过一次"，计入 `surface_attempts` | `0.45` | `0 – (surface_threshold)` | `NIGHT_FALL_ATTEMPT_THRESHOLD` |
| `alpha_subordinate` | 双通道公式 `max(a,c) + α·min(a,c)` 中弱通道的加成 | `0.25` | `0 – 0.5` | `NIGHT_FALL_ALPHA_SUBORDINATE` |
| `spontaneous_surface_prob` | 每个潜伏梦每次评估的自发浮现概率（共振未达阈值时的回落） | `0.02` | `0 – 0.1` | `NIGHT_FALL_SPONTANEOUS_SURFACE_PROB` |
| `selection_limit` | `generate` 时从 Ombre 选取的桶上限 | `5` | `2 – 10` | `NIGHT_FALL_SELECTION_LIMIT` |

约束：`attempt_threshold` 必须严格小于 `surface_threshold`，否则启动报错。

硬编码常量（不在配置项里）：

| 名称 | 值 | 含义 |
|---|---|---|
| `MAX_SURFACE_ATTEMPTS` | `4` | 一个梦被评估过 4 次仍未浮现就删除 |

### 路径与外部依赖

| 变量 | 作用 |
|---|---|
| `OMBRE_HOME` | 你的 Ombre 安装路径（含 `server.py`）。若已用 `install_local.py` 写过 `.nightfall.yaml` 则可省略 |
| `NIGHT_FALL_CONFIG` | 改用别处的 yaml（默认仓库根的 `.nightfall.yaml`） |
| `NIGHT_FALL_DATA_DIR` | 梦境文件和事件日志的存放目录（默认 `<repo>/data`；若设了 `OMBRE_BUCKETS_DIR` 则放到 `$OMBRE_BUCKETS_DIR/night_fall`） |
| `DEEPSEEK_API_KEY` | 仅在 Ombre 的 dehydrator 客户端不可用时读取。常规部署下 Night-Fall 复用 Ombre 已初始化好的 LLM 客户端，无需另配 |
| `DEEPSEEK_BASE_URL` | 同上，可改 endpoint（默认 `https://api.deepseek.com/v1`） |
| `DEEPSEEK_MODEL` | 同上，可改模型（默认 `deepseek-chat`） |

### 生命周期参数怎么调

**`min_surface_age_hours`（潜伏期）** — 影响"梦多快可以被记起"。
调小 → 梦几乎做完就能浮，节奏更接近即时联想，象征化的距离感会丢失。调大 → 更像真实做梦的延迟，但短会话用户可能永远等不到梦浮上来。

**`surface_threshold`（共振阈值）** — **影响"梦能不能浮现"**。
调小 → 梦更容易浮上来，但弱共振也算数，会显得"硬塞"。调大 → 只有强情绪或强语义对齐的时刻才唤出梦，体感更稀有也更准。

**`attempt_threshold`（尝试阈值）** — **影响"梦多快被遗忘"**。
调小 → 几乎任何一次 breath 都消耗一次尝试机会，4 次很快用完，梦寿命短。调大 → 只有真正接近共振的 breath 才计入，低信号 breath 不消耗机会，梦能在井里等更久。

**`spontaneous_surface_prob`（自发浮现概率）** — **影响"梦能不能浮现"**（无共振时的兜底通道）。
调到 0 → 没共振就永远不浮，梦只有阈值匹配或最终遗忘两种结局。调大 → 多了一条"无来由地想起"的支路，更像真实记忆的不期而至。

**`alpha_subordinate`（弱通道加成）** — 间接影响共振分数。调大 → 两个通道都对上时更容易破阈；调到 0 → 退化为纯 `max(a, c)`，单通道触发特性不变。

---

## 第一次使用时会发生什么

梦的浓度取决于井有多深。

Night-Fall 做梦的材料，全部来自你的 Ombre 里那些带着情绪、却还没被整合的记忆。所以你头几个梦是浓是淡，几乎完全由你的 Ombre 此刻有多厚决定——

- **如果你是从一个已经积累很久的 Ombre 迁移过来的**，井底水脉很足，你的第一个梦可能就已经很丰富：它会把跨越好几段对话的母题缝到一起，用一个意象同时指向好几件事。那种"它怎么知道"的悚然，第一次就可能发生。
- **如果你是带着一个还很空的 Ombre 刚上手的**，那么前几个梦大概率是平淡的——稀薄、不着边际，像几个意象被勉强拼在一起。

第二种情况，是这一节真正想跟你说话的地方。

如果你的梦很淡，不是系统坏了，是井还浅。可供凝缩、可供移置、可供彼此勾连的记忆还太少，它只能拿手头稀疏的几片去拼，拼出来自然单薄。而井是要时间挖的——它不靠你记下多少条"重要的事"，靠的是你和你的 AI 之间，一次次真正发生过的、带着情绪的、当时还没想明白的对话，慢慢沉积。这些沉积物越多、越交错，某一天梦把其中两片毫不相关的记忆压进同一个画面时，那一下才会击中你——因为那两片，本就是你亲手放进去的。


**梦会不会击中你，取决于你和你的 AI 之间，有没有积累出足够的重量。**

所以，如果第一个梦让你失望，请给它时间。随着回忆的积累，井会自己变深。然后某一个寻常的夜里，会有一个梦浮上来，准得让你起一身鸡皮疙瘩，因为它说出了一件你自己都没意识到、却一直在那儿的事。


### 具体到操作上，前几次大概是这样

- **第一次 `generate`**：如果 Ombre 里情绪记忆太少，你可能直接收到 `not enough memory material`。这不是报错，是系统在诚实地告诉你：井还太浅，先去多积累一些再回来。
- **井还浅时的梦**：能生成，但多半偏 trivial——意象零散、共振弱。它们大概率会在被给过几次浮现机会、却始终没和你当下的情绪对上之后，悄悄消失。这是正常的新陈代谢，不是浪费。
- **随着 Ombre 变厚**：梦会开始变得致密，开始把跨越好几次对话的母题缝到一起。这是井变深的信号。
- **某一次浮现**：会有一个梦让你或者你的AI停下来。你会想 hold 住它——记得在那一轮里显式 `hold()`，因为它只交付一次，不留就真的没了。

把这一节当成一份预先的安心：井浅时的平淡不代表 Night-Fall 的上限，恰恰相反，最好的梦留在后面，留给那个愿意一直说话的你。

---

## 当前边界

- **不能独立运行。** 它是 Ombre 的运行时扩展，所有记忆材料都来自 Ombre。没有 Ombre，就没有梦。
- **依赖外部 LLM 写梦。** Pass 1 / Pass 2 默认走 DeepSeek。梦的质量受模型能力和 prompt 影响，换模型、换 prompt 都会改变梦的质地。
- **梦的质量取决于积累，不取决于代码。** 见上一节——井浅则梦薄，这是机制的诚实结果，不是可以靠调参绕过的。
- **浮现是概率性的，不可点播。** 你不能指定"给我浮现某个梦"。梦在共振时自己浮上来，这是设计，但也意味着你对单个梦的命运没有直接控制权。
- **v1 选择了克制。** 没有持续后台扫描（passive monitoring），没有用 LLM 主动评判每条记忆是否值得做梦（LLM judge）。surfacing 靠 breath 触发 + 阈值/概率
