# Overseas Radar Skill · 海外商机研究

**从一个产品或消费需求，走到有依据的 B2B 机会判断与验证计划。**

[English](README.en.md) · [技能入口](skills/overseas-radar-b2b-research/SKILL.md) · [完整示例](skills/overseas-radar-b2b-research/references/worked-example.md) · [宿主适配](skills/overseas-radar-b2b-research/references/host-adaptation.md)

这是从 Overseas Radar 项目研究方法中提炼的轻量技能，首版 **0.1.0**。适合外贸从业者、产品研究人员和有工厂资源的创业者；支持两个入口：

- **从需求出发**：消费场景与痛点 → 需求假设 → 候选采购角色 → 采购条件 → 供给与验证。
- **从供给出发**：现有产品、工艺或询盘 → 候选市场与场景 → 买家与渠道 → 可行差异与下一步。

核心流程是“明确方向 → 收集线索 → 比较机会 → 核对条件 → 小测复盘”。有证据时给出推荐和优先级，缺证据时给条件式判断与补证动作。

## 三分钟开始

1. 下载本仓库，或从 [Releases](https://github.com/yaoadms-dot/overseas-radar-skill/releases) 下载独立技能包。
2. 将 `skills/overseas-radar-b2b-research/` 整个文件夹放进宿主支持的技能目录；不要只复制 SKILL.md。
3. 在支持显式技能调用的宿主中输入：

```text
请用 $overseas-radar-b2b-research：
我们有硅胶成型能力，想判断餐具沥水垫是否值得做美国 B2B 市场。
市场与渠道还没确定，MOQ、完整成本和认证条件尚未提供。
请先分析可行切口，再列出证据缺口和最小验证计划。
```

Codex 可安装到现有 `CODEX_HOME/skills/`；未设置 CODEX_HOME 时采用其默认工作库的 `skills/`。Windows 用户应沿用自己正在生效的工作库，不另建认证或数据库目录。

WorkBuddy 可将 SKILL.md 与 references 文件上传为专家参考，并采用 [手工配置引导](skills/overseas-radar-b2b-research/references/host-adaptation.md)。这里没有伪装成已注册的 WorkBuddy 原生专家包；不同宿主的发现与附件读取能力需要各自试用。

## 能得到什么

- 有理由的方向判断，以及改变判断的条件。
- 可追溯的具体样本，分开记录来源性质、内容性质和主张核验状态。
- C 端需求与候选 B 端角色的映射，明确采购意向的证据是否存在。
- 规格、价格、MOQ、物流、交期和准入的缺口。
- 包含负责人、时间、预算、观察指标和停止条件的最小行动计划。

日常问答保持简短，正式报告使用七段结构。公开标价不会自动变成批发报价，评论数不会自动变成销量；允许以注明来源的参数和假设测算成本与毛利。

## 文件

- [SKILL.md](skills/overseas-radar-b2b-research/SKILL.md)：流程与触发范围。
- [证据字段](skills/overseas-radar-b2b-research/references/evidence-schema.md) 与 [CSV 空表](skills/overseas-radar-b2b-research/references/evidence-register.csv)：25 个字段，未知允许留空。
- [报告骨架](skills/overseas-radar-b2b-research/references/report-template.md)：七段正式交付。
- [示例研究](skills/overseas-radar-b2b-research/references/worked-example.md) 与 [示例样本 CSV](skills/overseas-radar-b2b-research/references/example-evidence.csv)：公开来源、虚构客户条件、完整判断链。
- [评估场景](evals/scenarios.md)：供后续宿主行为试用，不冒充已完成的跨平台验证。

## 使用条件与当前验证

技能本体是 Markdown/CSV，无运行时依赖或必需 API 密钥。联网、模型和导出由宿主提供；无联网时只分析已有材料，不虚构检索。原软件的模型登录、Accio、Jev、数据存储和 Word/PDF 导出不在本技能包内。

[验证记录](docs/VALIDATION.md) 区分静态结构检查、打包检查、示例原页读取和真实宿主行为试用。完整示例展示方法，不证明该产品已经有采购需求或客户成交。源码与方法文本使用 [MIT](LICENSE)；第三方网页、品牌、商标和商品数据的权利仍属于各自权利人，见 [来源说明](docs/PROVENANCE.md)。

## 维护与打包

Python 3.10+，不安装额外依赖：

```sh
python scripts/validate.py
python scripts/validate.py --package
```

独立技能包生成到被 Git 忽略的 `.local/releases/`，只包含技能与许可，不包含工程基准、缓存或私人资料。工程维护采用仓库内 `.project-baseline/` 快照，具体范围见 [项目说明](项目说明.md)。欢迎按 [贡献指南](CONTRIBUTING.md) 提供失败案例和改进。
