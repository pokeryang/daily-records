# daily-records

单文件个人记录卡片：运动统计、力量训练、有氧训练、碎片思考、读书和看房记录。

Supabase `records` 表是唯一权威数据源。网页和小Q都直接读写同一张表，因此网页内新增、修改、删除后会同步到其他设备，小Q录入也会直接出现在网页中。GitHub Pages 只负责部署前端，不承担数据库职责。

## 部署

仓库无需构建步骤。更新 `index.html` 并推送到默认分支后，GitHub Pages 会自动发布。Supabase publishable key 可以放在前端；自定义数据密钥仅保存在浏览器 localStorage 和本机小Q技能中，不提交到公开仓库。

## 数据与离线兜底

Supabase 行包含 `id`、`module`、`time`、`data`、`created_at` 和 `updated_at`，完整记录对象放在 `data` JSONB 中。`module` 只能是 `thought`、`sport`、`book` 或 `house`。看房图片保存在记录的 `images` 数组中，格式为 JPEG data URI。

页面使用 localStorage 保存不含 base64 图片的轻量缓存，并用 IndexedDB 保存图片缓存和离线待同步内容；重新联网后自动补传。云端加载成功时始终以 Supabase 为准，避免已在其他设备删除的记录从旧缓存中恢复。

## GitHub JSON 备份

`data/records.json` 是版本化备份，不是网页或小Q的日常写入源。运行 `python3 scripts/records_store.py validate` 可检查备份的记录数、唯一 ID、模块字段、内容签名和图片数据。需要刷新备份时，应先从 Supabase 导出完整快照，再更新该文件并单独校验、提交。
