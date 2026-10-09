# daily-records

单文件个人记录卡片：运动统计、力量训练、有氧训练、碎片思考、读书和看房记录。

数据权威源是仓库内的 `data/records.json`，页面由 GitHub Pages 直接读取，无 Supabase 依赖。网页内的增删改会保存为当前浏览器的本机草稿，不会直接写 GitHub；通过小Q记录时，由小Q更新 JSON、校验并提交推送。右上角“导出备份”可随时下载包含图片的完整 JSON。

## 部署

仓库无需构建步骤。更新 `index.html` 或 `data/records.json` 并推送到默认分支后，GitHub Pages 会自动发布。

## 数据文件

`data/records.json` 顶层包含 `app`、`version`、`source`、`exportedAt` 和 `records`。每条记录必须有唯一 `id`，`module` 只能是 `thought`、`sport`、`book` 或 `house`。看房图片保存在对应记录的 `images` 数组中，格式为 JPEG data URI。

页面仍使用 localStorage 保存轻量离线缓存，并使用 IndexedDB 保存图片缓存；这些缓存不是跨设备权威数据。

## 校验与更新

运行 `python3 scripts/records_store.py validate` 可完整检查记录数、唯一 ID、模块字段、内容签名和图片数据。小Q写入时使用同一脚本执行 `upsert` 或 `delete`，脚本会加进程锁、更新 `exportedAt`、全量校验并原子替换 JSON；校验失败时不会改动源文件。
