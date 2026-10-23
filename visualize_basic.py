# -*- coding: utf-8 -*-
"""
豆瓣图书 Top250 —— 极简 4 图可视化
================================================
输入：data/books_clean_20261023.csv（步骤 3 清洗后的数据，250 行）
输出：figures/ 下 4 张 PNG

设计原则：
1. 只用 matplotlib，不引入 seaborn / plotly，不用渐变色、阴影、3D 等特效
2. 一个函数画一张图，改哪张就动哪个函数
3. 每张图只回答一个业务问题，标题直接写结论，副标题交代数据口径
4. 配色只用 3 个颜色：主色（墨绿）、强调色（砖红）、灰色（辅助线）
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ============================================================
# 第 0 步：环境设置
# ============================================================

# ---------- 0.1 中文字体 ----------
# matplotlib 默认字体不含中文，不设置会出现「方块 + 警告」。
# 这里按优先级挨个试，本机装了哪个用哪个（Windows 一般是 Microsoft YaHei / SimHei）。
CANDIDATES = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
              "Source Han Sans SC", "PingFang SC", "Arial Unicode MS"]
installed = {f.name for f in font_manager.fontManager.ttflist}
for name in CANDIDATES:
    if name in installed:
        plt.rcParams["font.sans-serif"] = [name]
        print(f"使用中文字体：{name}")
        break
else:
    print("警告：未找到中文字体，中文可能显示为方块")
# 中文字体里没有「−」这个负号字形，换成 ASCII 减号，否则坐标轴负号也会变方块
plt.rcParams["axes.unicode_minus"] = False

# ---------- 0.2 全局样式 ----------
# 关掉上边框和右边框，网格调淡，让数据本身成为视觉主体
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.color"] = "#e8e8e8"
plt.rcParams["grid.linewidth"] = 0.8
plt.rcParams["axes.axisbelow"] = True          # 网格画在数据下面，不遮住柱子
plt.rcParams["figure.dpi"] = 120

MAIN = "#2f6b56"      # 主色：墨绿，贴合"图书"题材
ACCENT = "#c0563b"    # 强调色：砖红，只用来标重点
GREY = "#7a7f85"      # 辅助色：参考线、注释

OUT_DIR = "figures"
os.makedirs(OUT_DIR, exist_ok=True)


# ---------- 0.3 统一出图的小工具 ----------
def new_canvas(index, title, subtitle, figsize=(8, 4.8), left=0.115):
    """
    开一张新画布，并在顶部写「编号 + 结论标题 + 口径副标题」。
    标题直接写结论、副标题写口径，是为了让图脱离正文也能被看懂——
    作品集里别人可能只截图不看文字。
    left 参数：左侧留白，中文纵轴标题比较宽，默认给足 0.115。
    """
    fig, ax = plt.subplots(figsize=figsize)
    fig.text(0.06, 0.965, f"图 {index}　{title}", fontsize=15, fontweight="bold",
             color="#1f2328", ha="left", va="top")
    fig.text(0.06, 0.895, subtitle, fontsize=9.5, color=GREY,
             ha="left", va="top", linespacing=1.7)
    fig.subplots_adjust(left=left, right=0.96, top=0.78, bottom=0.135)
    return fig, ax


def save(fig, filename):
    """
    保存并关闭。
    bbox_inches='tight'：防止长社名、注释文字被裁掉
    dpi=200：屏幕预览用不到这么高，但作品集页面在 2 倍屏上会放大，
             120 dpi 存出来只有 900 px 宽，字会发虚
    """
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, bbox_inches="tight", facecolor="white", dpi=200)
    plt.close(fig)
    print("已生成", path)


# ============================================================
# 第 1 步：读数据
# ============================================================
df = pd.read_csv("data/books_clean_20261023.csv")
print(f"数据规模：{len(df)} 行 × {df.shape[1]} 列")

# 本文件复用的几个统计量，先算好，后面直接引用
RATING_MEAN = df["rating"].mean()      # 9.07
RATING_STD = df["rating"].std()        # 0.24
MED_RATING = df["rating"].median()     # 9.1
MED_COUNT = df["rating_count"].median()  # 57415
CORR = df["rating"].corr(df["rating_count"])  # -0.067


# ============================================================
# 图 1：评分分布直方图
# 业务问题：这 250 本书的评分，到底有多大差别？
# ============================================================
def fig1_rating_dist():
    fig, ax = new_canvas(
        1,
        "250 本书的评分全部挤在 8.5–9.7 之间",
        f"横轴为豆瓣评分，纵轴为图书数量｜均值 {RATING_MEAN:.2f}，标准差仅 {RATING_STD:.2f}｜"
        f"数据：豆瓣图书 Top250（{len(df)} 本）",
    )

    # 1.1 直方图
    # 注意 bins 不能随手写 15：豆瓣评分是 0.1 一档的离散值（8.5 / 8.6 / …），
    # 若把 1.2 分平均切成 15 份（每份 0.08），分箱边界和 0.1 档位对不齐，
    # 会出现"有的柱子空了、有的柱子装两个档位"的锯齿。
    # 直接按 0.1 一档设边界，一根柱子就是一个评分档，映射关系最干净。
    edges = np.arange(8.45, 9.76, 0.1)
    counts, _, _ = ax.hist(df["rating"], bins=edges, color=MAIN,
                           edgecolor="white", linewidth=1.2)

    # 纵轴上限显式定死：既给上方注释留位置，也方便下面画参考线
    top = counts.max() * 1.18
    ax.set_ylim(-11, top)

    # 1.2 均值参考线（只画在数据区，不穿过下方的注释文字）
    ax.vlines(RATING_MEAN, 0, top, color=ACCENT, linestyles="--", linewidth=1.6)
    ax.annotate(f"均值 {RATING_MEAN:.2f}", xy=(RATING_MEAN, top * 0.94),
                xytext=(8, 0), textcoords="offset points", color=ACCENT,
                fontsize=10, fontweight="bold", va="top",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor="none", alpha=0.85))

    # 1.3 标出数据跨度，把"窄"这个结论量化
    # 箭头画在坐标轴下方（负值区），避免和数据柱、坐标轴叠在一起
    lo, hi = df["rating"].min(), df["rating"].max()
    ax.annotate("", xy=(lo, -3), xytext=(hi, -3),
                arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.2))
    ax.text((lo + hi) / 2, -7, f"跨度仅 {hi - lo:.1f} 分（{lo} – {hi}）",
            ha="center", va="top", fontsize=9.5, color=GREY)

    ax.set_xlabel("豆瓣评分")
    ax.set_ylabel("图书数量", labelpad=10)
    save(fig, "fig1_评分分布.png")


# ============================================================
# 图 2：口碑 × 热度散点图
# 业务问题：评分高的书，是不是看的人也多？
# ============================================================
def fig2_rating_vs_count():
    fig, ax = new_canvas(
        2,
        "叫好与叫座，是两件事",
        f"横轴为评价人数（对数刻度，跨 {df['rating_count'].min():,}–{df['rating_count'].max():,} 人）｜"
        f"纵轴为评分｜虚线为两项中位数｜相关系数 {CORR:.2f}",
        figsize=(8, 5.1),
    )

    # 2.1 散点：评价人数从 1 万到 90 万，必须用对数轴，
    #     否则 90% 的点会挤在左边一条竖线上
    ax.scatter(df["rating_count"], df["rating"],
               s=26, color=MAIN, alpha=0.55, edgecolors="white", linewidths=0.5)
    ax.set_xscale("log")

    # 2.2 中位数十字线，把平面切成四个象限
    ax.axhline(MED_RATING, color=GREY, linestyle="--", linewidth=1.1)
    ax.axvline(MED_COUNT, color=GREY, linestyle="--", linewidth=1.1)

    # 2.3 四个角标象限名 + 占比（比图例直观，也不会盖住数据点）
    box = dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="none", alpha=0.8)
    ax.text(0.015, 0.965, "高分 · 低热度\n80 本（32.0%）", transform=ax.transAxes,
            ha="left", va="top", fontsize=9.5, color=MAIN, bbox=box)
    ax.text(0.985, 0.965, "高分 · 高热度\n53 本（21.2%）", transform=ax.transAxes,
            ha="right", va="top", fontsize=9.5, color=ACCENT, fontweight="bold", bbox=box)
    ax.text(0.015, 0.02, "低分 · 低热度\n45 本（18.0%）", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=9.5, color=GREY, bbox=box)
    ax.text(0.985, 0.02, "低分 · 高热度\n72 本（28.8%）", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9.5, color=GREY, bbox=box)

    ax.set_xlabel("评价人数（对数刻度）")
    ax.set_ylabel("豆瓣评分", labelpad=10)
    save(fig, "fig2_口碑与热度.png")


# ============================================================
# 图 3：出版社 Top10 横向柱状图
# 业务问题：榜单上的书，主要集中在哪些出版社手里？
# ============================================================
def fig3_publisher():
    pub = df["publisher"].value_counts()          # 按上榜数量降序
    top10 = pub.head(10).sort_values()            # 画横柱要反过来排，最大值在上方
    cr10 = pub.head(10).sum() / len(df) * 100

    fig, ax = new_canvas(
        3,
        f"前 10 家出版社拿走 {cr10:.0f}% 的席位",
        f"共 {len(pub)} 家出版社上榜，其中 {(pub == 1).sum()} 家只有 1 本｜"
        f"按入榜图书数量排序，取前 10 名",
        figsize=(8, 5.2),
    )

    # 3.1 横向柱状图：横向排更适合放长中文社名
    bars = ax.barh(top10.index, top10.values, color=MAIN,
                   height=0.68, edgecolor="white", linewidth=0.8)

    # 3.2 柱子末端标数值，精确值不用读者去估
    for bar, v in zip(bars, top10.values):
        ax.text(v + 0.4, bar.get_y() + bar.get_height() / 2, f"{v} 本",
                va="center", fontsize=9, color="#1f2328")

    # 3.3 第一名单独着色，突出"一家独大"
    bars[-1].set_color(ACCENT)

    ax.set_xlabel("入榜图书数量")
    ax.set_xlim(0, top10.max() * 1.16)
    ax.grid(axis="y", visible=False)     # 横柱图不需要横向网格线
    fig.subplots_adjust(left=0.245)      # 左边留够，否则长社名被裁
    save(fig, "fig3_出版社集中度.png")


# ============================================================
# 图 4：出版年份分布柱状图
# 业务问题：上榜的书，版本集中在哪个年代？
# ============================================================
def fig4_year():
    # 4.1 按 10 年分段统计（比逐年更稳，避免某一年样本太少导致柱子忽高忽低）
    bins = [1960, 1980, 1990, 2000, 2010, 2020, 2025]
    labels = ["1980 前", "1980s", "1990s", "2000s", "2010s", "2020 后"]
    seg = pd.cut(df["year"], bins=bins, right=False, labels=labels)
    counts = seg.value_counts().reindex(labels)

    recent = int(counts.loc[["2010s", "2020 后"]].sum())   # 2010 年以后的版本数
    fig, ax = new_canvas(
        4,
        f"2010 年以后的版本占了榜单的 {recent / len(df) * 100:.0f}%",
        f"横轴为版本出版年代，纵轴为图书数量｜注意：这是该版本的印刷年份，"
        f"不是作品的首次出版年份｜{len(df)} 本",
    )

    bars = ax.bar(labels, counts.values, color=MAIN, width=0.62,
                  edgecolor="white", linewidth=1.2)

    # 4.2 每根柱子标「本数 + 占比」，两个口径一起给
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5,
                f"{v}\n{v / len(df) * 100:.0f}%",
                ha="center", va="bottom", fontsize=9, color="#1f2328")

    # 4.3 最高的一根柱子换成强调色，直接指向"峰值在哪"
    bars[counts.values.argmax()].set_color(ACCENT)

    ax.set_xlabel("版本出版年代")
    ax.set_ylabel("图书数量", labelpad=10)
    ax.set_ylim(0, counts.max() * 1.22)
    ax.grid(axis="x", visible=False)
    save(fig, "fig4_出版年份分布.png")


# ============================================================
# 执行
# ============================================================
if __name__ == "__main__":
    fig1_rating_dist()
    fig2_rating_vs_count()
    fig3_publisher()
    fig4_year()
    print("\n4 张图已全部生成到", os.path.abspath(OUT_DIR))
