# overseas-radar-skill

采用基准：v1.1.1。建立时间：2026-10-19T08:51:32.860164+00:00。

状态：工程已初始化，需求与业务事实尚未填写。

先读 AGENTS.md 和项目说明.md，将已确认事实填入 project.json，再按任务清单推进。阶段检查入口位于 `.project-baseline/tools/检查项目.ps1`。完整性检查使用 `-ProjectPath . -Stage 基准完整性`。

`.project-baseline` 为不可变快照；项目自身的配置、文档和代码在快照外维护。初始化回执在 `.local/initialization-receipt.json`；首次 Git 提交由 `refs/baselines/initial` 固定。
