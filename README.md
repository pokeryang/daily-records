# daily-records

单文件个人记录卡片：运动统计 / 力量训练 / 有氧训练 / 碎片思考 / 读书 / 看房记录。

- 前端：纯 vanilla JS + HTML，单文件 `index.html`，可直接 GitHub Pages 托管。
- 数据：Supabase（Tokyo 区）自动实时同步，任何设备打开同一个 URL 都能看到最新数据。
- 离线：本地 localStorage 兜底，断网也能写，联网后自动补同步。
- 备份：任何时候可点右上角「导出备份」下载 JSON。

## 部署

已通过 GitHub Pages 部署，无需构建步骤。

## 在任意设备打开

访问部署后的 Pages URL 即可，桌面/手机均可用；数据通过 Supabase publishable key 与云端同步。
