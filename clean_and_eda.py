# -*- coding: utf-8 -*-
"""
豆瓣图书 Top250 · 步骤 3：数据清洗 + EDA 探索性分析

输入：data/books_raw_20261023.csv        （爬虫原始输出，不做任何改动）
输出：data/books_clean_20261023.csv      （清洗后分析用数据）
      figures_eda/fig1 ~ fig6            （EDA 阶段的调试图）

运行：python clean_and_eda.py
依赖：pandas、numpy、matplotlib

说明：
    本脚本只用基础 pandas 操作（查询、字符串处理、分箱、分组聚合、相关矩阵），
    不使用任何建模或高阶方法。每一步清洗都写明"为什么这么处理"。
"""

import os

import matplotlib
matplotlib.use("Agg")               # 不弹窗，直接存图，方便在 PyCharm 里跑
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ============================================================
# 0. 路径与全局配置
# ============================================================
RAW_CSV = r"data/books_raw_20261023.csv"
CLEAN_CSV = r"data/books_clean_20261023.csv"
FIG_DIR = "figures_eda"

os.makedirs(FIG_DIR, exist_ok=True)

# 中文字体：Windows 优先微软雅黑，其次黑体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False      # 负号正常显示
plt.rcParams["figure.dpi"] = 130
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["axes.edgecolor"] = "#cccccc"


def show(title):
    """统一的分节打印"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# ============================================================
# 1. 读取原始数据
# ============================================================
show("1. 读取原始数据")

# dtype=str + keep_default_na=False：
#   先把所有列当文本读进来，避免 pandas 自作主张把 "001" 变 1、把空串变 NaN。
#   清洗第一步永远是"看清楚原始长什么样"，而不是让库替我们猜。
df = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
df.columns = [c.strip() for c in df.columns]

print(f"原始形状：{df.shape[0]} 行 × {df.shape[1]} 列")
print(f"列名：{list(df.columns)}")

# 保留一份原始副本，用于最后核对"清洗到底改了什么"
raw_shape = df.shape


# ============================================================
# 2. 去重
# ============================================================
show("2. 去重（以 url 为唯一标识）")

# 业务意义：
#   豆瓣 Top250 里，同一本书的不同版本（不同出版社、不同译者）会被当作两条独立记录，
#   它们书名相同但 url 不同 —— 这是真实业务事实，不是脏数据，不能删。
#   真正需要去掉的只有"同一个 url 被抓了两次"这种采集层面的重复。
#   所以唯一键用 url，而不是书名。
dup_url = df.duplicated(subset=["url"]).sum()
print(f"按 url 判断的重复记录：{dup_url} 条")

if dup_url > 0:
    df = df.drop_duplicates(subset=["url"], keep="first").reset_index(drop=True)
    print(f"已去重，剩余 {len(df)} 条")
else:
    print("无重复，无需处理")

# 顺带看一下书名重复情况：如果有，说明是多版本，全部保留
dup_name = df["book_name"].duplicated().sum()
print(f"书名重复：{dup_name} 条（同名不同 url 属多版本图书，保留不删）")


# ============================================================
# 3. 缺失值处理
# ============================================================
show("3. 缺失值处理")

# 先把空串统一成 DataFrame 认可的缺失值，方便后续统计
df = df.replace("", np.nan)

missing = df.isna().sum()
missing = missing[missing > 0].sort_values(ascending=False)
print("各字段缺失情况：")
for col, n in missing.items():
    print(f"  {col:<14}{n:>4} 条（缺失率 {n / len(df) * 100:.1f}%）")

# 业务意义：缺失分两类，处理方式完全不同。
#
#   ① quote（短评）缺失 90 条、author_raw（作者）缺失 0 条：
#      这是豆瓣页面本身就没写，属于业务正常缺失。
#      不能填"未知"（会污染文本）、不能删行（会丢掉这本书的其他有效信息）。
#      → 处理方式：保留缺失，分析时按需排除。quote 本来也不参与数值分析。
#
#   ② price 缺失 1 条（#136 十万个为什么）：
#      网页上这本书确实没有标价，是原始数据的事实。
#      → 处理方式：保留为 NaN，价格相关分析时自动排除，不做均值填充。
#        因为价格分布右偏严重，均值填充会造出一个不存在的中等价位，扭曲结论。
print("\n处理原则：全部保留，不做填充、不删行。")
print("理由：这两类缺失都是『网页本来就没有』，填充等于凭空造数据。")

# 对确实需要的数值列，用 dropna 在具体分析时临时排除，而不是全局删行
print(f"\n清洗后仍保留 {len(df)} 行（未因缺失删掉任何一本书）")


# ============================================================
# 4. 字段类型转换
# ============================================================
show("4. 字段类型转换")

# ---------- 4.0 排名 → 整数 ----------
# 业务意义：排名读进来也是字符串，不转换就没法做区间切分和排序。
df["rank"] = pd.to_numeric(df["rank"], errors="coerce").astype(int)

# ---------- 4.1 评分、评价人数 → 数值 ----------
# 业务意义：原始数据里它们是字符串，字符串没法算平均值、没法比较大小。
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce")

# ---------- 4.2 价格 → 数值 ----------
# 业务意义：价格原始形态有三类问题——带单位（59.70元）、带空格（0.31 元）、
#          带斜杠（53.00元/68.00元）、带币种（NTD 350）、带说明文字（68.00元（有2020年7月34印本））。
#          必须统一成纯数字才能参与统计，但原始形态本身也是信息，要单独标记。

# 标记 1：是否套装双价（含斜杠）。不强行拆分，只打标签，分析时可按需排除。
df["has_multi_price"] = df["price"].str.contains("/", regex=False, na=False)

# 标记 2：币种。台版书用新台币，与人民币直接混算会严重失真。
df["currency"] = np.where(df["price"].str.contains("NTD", na=False), "NTD", "CNY")

# 提取第一个数字作为价格。用 (\d+(?:\.\d+)?) 而不是 \d+，否则 59.70 会被截成 59。
df["price"] = pd.to_numeric(
    df["price"].str.extract(r"(\d+(?:\.\d+)?)")[0], errors="coerce"
)

# ---------- 4.3 出版日期 → 年份 ----------
# 业务意义：日期有 4 种写法（1981-8 / 2014-6-9 / 1978年6月 / 1962），
#          做年度趋势只需要年份，所以统一抽 4 位数字。
#          注意：这是"该版本的印刷年份"，不是作品的首次出版年份，解读时必须说明。
df["year"] = pd.to_numeric(
    df["publish_date"].str.extract(r"(\d{4})")[0], errors="coerce"
)

# ---------- 4.4 出版社标准化 ----------
# 业务意义：出版社是分类字段，首尾空格会导致同一家社被统计成两组。
df["publisher"] = df["publisher"].str.strip()

print("转换结果：")
print(df[["rating", "rating_count", "price", "year"]].dtypes.to_string())
print(f"\n套装双价记录：{df['has_multi_price'].sum()} 条")
print(f"非人民币记录：{(df['currency'] != 'CNY').sum()} 条")
print(f"年份提取失败：{df['year'].isna().sum()} 条")
print(f"价格提取失败：{df['price'].isna().sum()} 条（与原始缺失一致）")


# ============================================================
# 5. 异常值处理
# ============================================================
show("5. 异常值识别（标记，不删除）")

# 业务意义：价格的极端值有两类来源，性质完全不同。
#   ① 1970 年代旧版书的真实定价（0.20~0.43 元）—— 真实但年代久远
#   ② 套装书/精装版的高价（498 元）—— 真实但代表的是多卷本
#   两类都是真数据，删掉会丢失信息，还会人为压缩分布。
#   做法：用 IQR 规则标记出来，分析时按需排除，并在结论里说明。

q1 = df["price"].quantile(0.25)
q3 = df["price"].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

df["price_outlier"] = (df["price"] < lower) | (df["price"] > upper)

print(f"价格四分位数：Q1={q1:.2f}  中位数={df['price'].median():.2f}  Q3={q3:.2f}")
print(f"IQR 合理区间：{lower:.2f} ~ {upper:.2f} 元")
print(f"标记为异常：{df['price_outlier'].sum()} 条")

print("\n异常值明细（全部保留）：")
outliers = df[df["price_outlier"]][["rank", "book_name", "price", "year", "publisher"]]
print(outliers.to_string(index=False))

# 评价人数同样右偏严重，但不做异常标记：
# 热度分布本身就是长尾，把头部标成"异常"没有业务意义，改为在可视化时用对数坐标。


# ============================================================
# 6. 保存清洗结果
# ============================================================
show("6. 保存清洗后数据")

# 分析用：去掉 info_raw（原文留档，分析用不上），保留所有标记列
df.to_csv(CLEAN_CSV, index=False, encoding="utf-8-sig")

print(f"已保存：{CLEAN_CSV}")
print(f"清洗前后：{raw_shape[0]} 行 × {raw_shape[1]} 列  →  {df.shape[0]} 行 × {df.shape[1]} 列")
print("未删除任何一行数据；列数增加，增加的都是标记列和派生字段。")


# ============================================================
# 7. EDA —— 描述统计
# ============================================================
show("7. EDA：描述统计")

# 只统计真正有分析价值的数值列
num_cols = ["rank", "rating", "rating_count", "price", "year"]
desc = df[num_cols].describe().T
desc["中位数"] = df[num_cols].median()
print(desc.round(2).to_string())

print("\n分布形态提示：")
print(f"  评分均值 {df['rating'].mean():.2f}，标准差仅 {df['rating'].std():.2f} —— 高度集中")
print(f"  评价人数均值 {df['rating_count'].mean():.0f}，中位数 {df['rating_count'].median():.0f}")
print(f"  均值远大于中位数，说明热度分布右偏（少数爆款拉高均值）")
print(f"  价格均值 {df['price'].mean():.2f}，中位数 {df['price'].median():.2f}")


# ============================================================
# 8. EDA —— 分组统计
# ============================================================
show("8. EDA：分组统计")

# ---------- 8.1 排名分段 vs 评分 ----------
# 业务问题：排名靠前是不是就等于评分更高？
df["rank_seg"] = pd.cut(
    df["rank"], bins=[0, 50, 100, 150, 200, 250],
    labels=["1-50", "51-100", "101-150", "151-200", "201-250"],
)
seg = df.groupby("rank_seg", observed=True)["rating"].agg(["count", "mean", "min", "max"])
print("\n【排名分段 vs 评分】")
print(seg.round(3).to_string())

# ---------- 8.2 出版年代分布 ----------
# 业务问题：这份榜单是不是"老人榜"？新书有机会进来吗？
df["era"] = pd.cut(
    df["year"], bins=[0, 1949, 1979, 1999, 2009, 2019, 2030],
    labels=["1949前", "1950-1979", "1980-1999", "2000-2009", "2010-2019", "2020后"],
)
era = df["era"].value_counts().sort_index()
era_pct = (era / len(df) * 100).round(1)
print("\n【出版年代分布】")
for k in era.index:
    print(f"  {k:<12}{era[k]:>3} 本  {era_pct[k]:>5.1f}%")

# ---------- 8.3 出版社集中度 ----------
# 业务问题：这份榜单是"少数出版社主导"还是"广泛分布"？
pub = df["publisher"].value_counts()
cr10 = pub.head(10).sum() / len(df) * 100
print(f"\n【出版社集中度】共 {len(pub)} 家")
print(f"  Top10 合计 {pub.head(10).sum()} 本，占全榜 {cr10:.1f}%")
print(f"  只上榜 1 本的出版社：{(pub == 1).sum()} 家")
print("\n  Top10 明细：")
for name, n in pub.head(10).items():
    print(f"    {name:<24}{n:>3} 本  （{n / len(df) * 100:.1f}%）")

# ---------- 8.4 口碑 × 热度四象限 ----------
# 业务问题：高分的书是不是也高热度？两者错位有多少？
med_rating = df["rating"].median()
med_count = df["rating_count"].median()

df["quadrant"] = np.select(
    [
        (df["rating"] >= med_rating) & (df["rating_count"] >= med_count),
        (df["rating"] >= med_rating) & (df["rating_count"] < med_count),
        (df["rating"] < med_rating) & (df["rating_count"] >= med_count),
    ],
    ["高分高热度", "高分低热度", "低分高热度"],
    default="低分低热度",
)
quad = df["quadrant"].value_counts()
print(f"\n【口碑×热度四象限】（以评分中位数 {med_rating:.1f}、人数中位数 {med_count:.0f} 为界）")
for k, n in quad.items():
    print(f"  {k:<10}{n:>3} 本  {n / len(df) * 100:>5.1f}%")

print("\n  高分低热度代表（评分高但人少）：")
for _, r in df[df["quadrant"] == "高分低热度"].nlargest(3, "rating").iterrows():
    print(f"    #{r['rank']:>3} {r['book_name']}（{r['rating']} 分，{r['rating_count']:,} 人）")

# ---------- 8.5 价格区间 vs 评分 ----------
# 业务问题：贵的书是不是更容易得高分？
df["price_seg"] = pd.cut(
    df["price"], bins=[0, 20, 30, 40, 60, 10000],
    labels=["20元以下", "20-30元", "30-40元", "40-60元", "60元以上"],
)
price_grp = df.groupby("price_seg", observed=True).agg(
    数量=("rating", "size"),
    评分均值=("rating", "mean"),
    人数均值=("rating_count", "mean"),
)
print("\n【价格区间 vs 评分】")
print(price_grp.round(2).to_string())

# ---------- 8.6 相关性 ----------
print("\n【数值字段相关系数】")
corr = df[["rank", "rating", "rating_count", "price", "year"]].corr().round(3)
print(corr.to_string())
print("\n  说明：相关系数只反映线性同向/反向关系的强弱，不代表因果。")


# ============================================================
# 9. 可视化
# ============================================================
show("9. 生成图表")


def save(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {path}")


# ---------- 图1：评分分布 ----------
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.hist(df["rating"], bins=13, color="#2f6b4f", edgecolor="white")
ax.axvline(df["rating"].mean(), color="#c0392b", linestyle="--", linewidth=1.4,
           label=f"均值 {df['rating'].mean():.2f}")
ax.set_title("Top250 图书评分分布", fontsize=13, pad=12)
ax.set_xlabel("豆瓣评分")
ax.set_ylabel("图书数量")
ax.legend(frameon=False)
save(fig, "fig1_评分分布.png")

# ---------- 图2：评价人数分布（对数） ----------
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.hist(df["rating_count"], bins=30, color="#3d7ea6", edgecolor="white")
ax.set_xscale("log")
ax.set_title("评价人数分布（横轴为对数刻度）", fontsize=13, pad=12)
ax.set_xlabel("评价人数（对数）")
ax.set_ylabel("图书数量")
ax.axvline(df["rating_count"].median(), color="#c0392b", linestyle="--", linewidth=1.4,
           label=f"中位数 {df['rating_count'].median():,.0f}")
ax.legend(frameon=False)
save(fig, "fig2_评价人数分布.png")

# ---------- 图3：出版年份分布 ----------
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.hist(df["year"].dropna(), bins=25, color="#8a6f4e", edgecolor="white")
ax.set_title("出版年份分布（该版本印刷年份）", fontsize=13, pad=12)
ax.set_xlabel("出版年份")
ax.set_ylabel("图书数量")
save(fig, "fig3_出版年份分布.png")

# ---------- 图4：排名分段 vs 评分 ----------
fig, ax = plt.subplots(figsize=(7, 4.2))
data = [df.loc[df["rank_seg"] == s, "rating"].dropna() for s in seg.index]
bp = ax.boxplot(data, patch_artist=True, widths=0.55)
ax.set_xticks(range(1, len(seg.index) + 1))
ax.set_xticklabels(list(seg.index))
for patch in bp["boxes"]:
    patch.set_facecolor("#cfdcd3")
    patch.set_edgecolor("#2f6b4f")
for med in bp["medians"]:
    med.set_color("#c0392b")
    med.set_linewidth(1.8)
ax.set_title("不同排名区间的评分分布", fontsize=13, pad=12)
ax.set_xlabel("排名区间")
ax.set_ylabel("豆瓣评分")
save(fig, "fig4_排名区间评分.png")

# ---------- 图5：出版社 Top15 ----------
top15 = pub.head(15).sort_values()
fig, ax = plt.subplots(figsize=(7, 5))
ax.barh(top15.index, top15.values, color="#2f6b4f", height=0.62)
for i, v in enumerate(top15.values):
    ax.text(v + 0.3, i, str(v), va="center", fontsize=9, color="#444")
ax.set_title("入榜图书最多的 15 家出版社", fontsize=13, pad=12)
ax.set_xlabel("入榜图书数量")
ax.grid(axis="y", visible=False)
save(fig, "fig5_出版社Top15.png")

# ---------- 图6：评分 × 评价人数四象限 ----------
fig, ax = plt.subplots(figsize=(7, 5))
colors = {"高分高热度": "#c0392b", "高分低热度": "#2f6b4f",
          "低分高热度": "#3d7ea6", "低分低热度": "#b0b0b0"}
for k, c in colors.items():
    sub = df[df["quadrant"] == k]
    ax.scatter(sub["rating_count"], sub["rating"], s=26, alpha=0.75,
               color=c, label=f"{k}（{len(sub)}）", edgecolors="white", linewidths=0.4)
ax.set_xscale("log")
ax.axhline(med_rating, color="#888", linestyle="--", linewidth=1)
ax.axvline(med_count, color="#888", linestyle="--", linewidth=1)
ax.set_title("口碑与热度：四象限分布", fontsize=13, pad=12)
ax.set_xlabel("评价人数（对数）")
ax.set_ylabel("豆瓣评分")
ax.legend(frameon=False, fontsize=9, loc="lower right")
save(fig, "fig6_口碑热度四象限.png")


# ============================================================
# 10. 汇总
# ============================================================
show("10. 完成")
print(f"清洗后数据：{CLEAN_CSV}")
print(f"图表目录  ：{FIG_DIR}/ 共 6 张（EDA 调试图）")
