# 豆瓣图书 Top250 榜单数据分析

用 250 本书的评分、评价人数、出版社与版本年份，回答一个问题：**这份榜单是怎么构成的。**

榜单每天被人翻，但它只给排名，不解释构成——为什么有的书评分更高却排在后面？哪些出版社在榜上反复出现？榜上的书到底有多"老"？

这个项目用一次完整的数据分析流程（采集 → 清洗 → 探索 → 可视化 → 结论）把榜单拆开来看。

**在线预览**：`https://<你的用户名>.github.io/douban-top250-portfolio/`（部署后把这段换成实际地址）

---

## 页面

| 文件 | 内容 | 适合 |
| --- | --- | --- |
| `index.html` | 四张图 + 四条结论，一页读完 | 第一眼 |
| `project.html` | 分析问题、流程设计、数据源与局限性 | 看思路 |
| `dashboard.html` | 六张图的另一版解读，更细 | 看细节 |
| `report.html` | 完整报告全文，约 440 行 | 看全过程 |

三个 HTML 页面的配色、字体与排版是同一套，页脚有互通的导航，跳转不会割裂。

> 在 GitHub 仓库页里直接点 `.html` 文件只会看到源码，要看渲染效果请访问上面的 Pages 地址。

## 四条结论

| # | 结论 | 依据 |
| :--- | :--- | :--- |
| 1 | 榜内评分几乎没有区分度 | 250 本全在 8.5–9.7，标准差仅 0.24 |
| 2 | 口碑与热度是两条独立的赛道 | 相关系数 −0.07，两者兼得者 21.2% |
| 3 | 席位集中在少数出版社 | 71 家上榜，前 10 家占 56%；第一名 38 本 |
| 4 | 年份说的是版本，不是作品 | 84% 为 2000 年后的版本，不能读成"偏爱新书" |

## 目录结构

```
douban-top250-portfolio/
├── index.html            首页：四图与结论
├── project.html          项目背景与目标
├── dashboard.html        六图可视化看板
├── report.html           完整分析报告
├── report.md             同一份报告的 Markdown 源文件
├── _config.yml           Pages 配置（排除 report.md，避免与 report.html 冲突）
├── data/
│   ├── books_raw_20261023.csv      采集原始数据（250 行 × 11 列）
│   └── books_clean_20261023.csv    清洗后数据（250 行 × 15 列）
├── figures/                        四张成品图
├── spider_top250.py     ① 采集（requests + bs4）
├── clean_and_eda.py     ② 清洗与探索分析（pandas）
├── visualize_basic.py   ③ 出图（matplotlib）
└── requirements.txt
```

## 本地查看

不需要起服务，直接双击 `index.html` 即可。四个页面之间可以互相跳转。

## 复现

```bash
pip install -r requirements.txt
python spider_top250.py      # 联网采集 10 页，间隔 3–5 秒
python clean_and_eda.py      # 生成 data/books_clean_*.csv
python visualize_basic.py    # 生成 figures/ 下四张图
```

`html_cache/` 不随仓库提供。第一次运行采集脚本需要联网（10 次请求，约 1 分钟），之后重跑会走本地缓存，不再发请求。

## 说明

- 数据来自豆瓣读书公开榜单页，仅作学习与作品展示用途，采集于 2026 年 10 月。
- 数据版权归豆瓣及相应出版社所有，不代表豆瓣立场。
- 本项目为描述性分析，未做假设检验与建模，不对排名机制下因果结论。
