# Documentation Index

## v3.0.0-beta.2 enterprise-trial baseline

Start here when evaluating the current v3 work. This is a bounded enterprise
trial and simulation baseline, not an industrial or safety-certified AGV
controller.

- [Architecture and runtime boundaries](architecture/V3_ENTERPRISE_ARCHITECTURE.md): API, scheduler, simulation adapter, events, and persistence.
- [Docker trial deployment](deployment/DOCKER_TRIAL.md): Docker Compose, MySQL, and the optional Keycloak acceptance profile.
- [Database migrations, backup, and recovery](deployment/DATABASE_MIGRATIONS.md): check, backup, upgrade, verify, and restore procedures.
- [Enterprise-trial security baseline](security/TRIAL_SECURITY_BASELINE.md): demo-account, HTTPS, cookie, CORS, identity, and device boundaries.
- [Windows local demo and package](release/PACKAGING_WINDOWS.md): SQLite-oriented single-machine demonstration and packaging flow.
- [Enterprise avoidance demo](demo/ENTERPRISE_AVOIDANCE_DEMO_RUNBOOK.md): a reproducible simulation scenario.

## Current version and historical release material

The repository-root [`VERSION`](../VERSION) file is the canonical current
version and is now `v3.0.0-beta.2`. The beta.2 notes describe the current
baseline; published beta.1 material is retained as historical preview
documentation:

- [beta.2 release notes](release/RELEASE_DRAFT_v3.0.0-beta.2.md)
- [beta.1 release notes](release/RELEASE_DRAFT_v3.0.0-beta.1.md)
- [beta.1 release procedure](release/RELEASE_UPLOAD_v3.0.0-beta.1.md)
- [release strategy](release/RELEASE_STRATEGY.md)
- [historical plans](archive/plans/README.md)

这个目录用于把根目录中过多的阶段材料分区收纳。项目已通过毕业设计答辩，后续开发优先看 `plans/POST_DEFENSE_PRODUCTIZATION_PLAN_2026-04-22.md`，需要回看答辩口径时再看 `defense/`。

## 分区

- `defense/`：答辩讲解资料，包含代码结构、算法、数据库、ComfyUI 和亮点问答。
- `plans/`：项目实施计划、接口冻结、阶段推进和开放事项。
- `acceptance/`：第四阶段验收、人工验证、最小交付基线。
- `demo/`：演示脚本、个人/企业动态避让演示、快速启动、SQLite 演示和故障排查。
- `release/`：Windows 打包、版本策略和发布材料。

## 根目录保留原则

根目录只保留高频入口和协作必读文件。常用启动器保留在根目录，不常用开发脚本移动到 `tools/windows/`。
