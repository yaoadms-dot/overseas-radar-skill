# 验证记录 · 0.1.0

日期：2026-10-19。

## 已执行

- 本机 skill-creator 的 quick_validate.py：通过，退出码 0。
- `python scripts/validate.py --package`：通过，退出码 0。检查技能 frontmatter、资源存在、相对链接、占位符、25 列 CSV、样本编号关联、发布候选文件及常见密钥格式。
- 发布包 9 个条目：8 个技能资源与 LICENSE；校验 CRC、条目清单和每个条目的字节一致性。压缩包不包含工程基准或本地运行数据；独立解包后，全部内部链接可解析，临时解包目录已自动清理。
- 示例来源：实际打开 OXO 和 Brabantia 商品页；Joseph Joseph 原地址跳转到集合页，记录冲突并排除摘要中的具体价格与规格。链接与日期保留在示例中。

发布包 SHA-256：`f90146d6a91708bd66f77bbe7340540dcc7daada7ba3370c4b2baf6211f12d37`。打包器统一 UTF-8/LF 并固定条目顺序、时间和文件属性；后续内容变化需要重建并更新校验值。

## 尚未声明通过

- Codex 新会话自动发现与真实任务行为评估。
- WorkBuddy 原生注册、知识文件检索与实际导出。
- 买家访谈、供应报价、产品性能、法规适用性、采购计划、客户采用或成交。

evals/scenarios.md 提供后续试用场景，不是这些场景已经执行的证据。静态通过不证明模型每次正确，也不能保证所有宿主的兼容性。

## 公开发布核对

- 仓库：https://github.com/yaoadms-dot/overseas-radar-skill ，API 未登录请求确认 `private=false`。
- 版本：https://github.com/yaoadms-dot/overseas-radar-skill/releases/tag/v0.1.0 。
- 发布来源提交：`484b340dbd3b17923e342cc092ea4a1db9781a50`。
- [GitHub 自动检查](https://github.com/yaoadms-dot/overseas-radar-skill/actions/runs/39227821778)：completed / success，对应上述来源提交。
- ZIP 安装包与 SHA256SUMS.txt 都通过匿名下载；长度及 SHA-256 与本地一致。ZIP 为 14714 字节，包含 9 个条目。
- 发布提交中的远程 SKILL.md 与本地文本一致。没有改变原软件仓库的文件或可见性。

工程基准完整性、明确目标与命令验证通过；资源审计为零候选大文件重复。两次最终打包校验值一致。最终验收执行记录保存在本地工程回执中，不上传凭据或本机运行记录。
