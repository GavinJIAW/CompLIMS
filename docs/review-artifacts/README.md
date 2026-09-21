# Local Review Artifacts

此目录用于保存 CompLIMS 本地 Source Review / Validation artifacts，典型内容包括：

- `*.patch`：source review patch、fix review patch。
- `*-inventory.txt`：变更清单。
- Review bundles。
- Temporary validation outputs。

除本 README 外，实际 artifacts 默认被 Git ignore，不应 commit，也不要使用 `git add -f` 将其加入版本控制。

推荐按模块和 review 类型组织：

```text
docs/review-artifacts/<module>/<review-type>/
```

例如 `docs/review-artifacts/M3/source-review/` 和 `docs/review-artifacts/M3/fix-review/`。仅在实际生成 artifact 时创建对应子目录，不提前创建空模块目录。

后续 Codex 生成 Review Bundle 或 validation artifact 时，优先写入此目录，不再在 repository 外创建随机 review 目录。已有外部历史 artifacts 不自动移动或删除，由用户决定是否保留。

Database backup 不存放在这里。数据库 dump 继续使用 `~/complims-backups/` 或当前已确认的 backup 区域。

README 和 artifacts 中均不得写入真实 token、password 或 credential。
