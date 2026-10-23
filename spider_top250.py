# -*- coding: utf-8 -*-
"""
豆瓣图书 Top250 数据采集（完整版）

用法：
    python spider_top250.py

产出：
    data/books_raw_YYYYMMDD.csv     原始数据（未清洗）
    html_cache/top250_start*.html   原始页面缓存，可离线调试解析逻辑

说明：
    所有TODO解析代码已经补全，末尾已加上启动入口
"""

import csv
import os
import random
import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

# ============================================================
# 1. 配置区
# ============================================================
BASE_URL = "https://book.douban.com/top250"
START_LIST = list(range(0, 250, 25))     # 0, 25, ..., 225 共 10 页
DELAY_RANGE = (3, 5)                     # 随机延时区间（秒）
TIMEOUT = 10
HTML_DIR = "html_cache"                  # 原始页面缓存目录
OUT_DIR = "data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

FIELDS = [
    "rank", "book_name", "author_raw", "publisher", "publish_date",
    "price", "rating", "rating_count", "quote", "url", "info_raw",
]

# 出版日期形态：YYYY / YYYY-M / YYYY-M-D / YYYY年M月（最后一种是老书的写法）
# 用于从出版信息串里定位"日期"这一段，其余字段按它前后分配
DATE_RE = re.compile(r"^\d{4}(\s*[-/年]\s*\d{1,2}\s*月?)?(\s*[-/年]\s*\d{1,2}\s*日?)?$")


# ============================================================
# 2. 采集层（已写完，可直接用）
# ============================================================
def fetch_page(start, session):
    """请求单页，成功返回 HTML 文本，失败返回 None。"""
    url = f"{BASE_URL}?start={start}"
    try:
        resp = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[请求异常] {url} -> {e}")
        return None

    # 遇到限流或封禁直接停，不重试、不换 IP
    if resp.status_code in (403, 429):
        print(f"[被限流] 状态码 {resp.status_code}，建议停止本次采集")
        return None
    if resp.status_code != 200:
        print(f"[状态码异常] {resp.status_code} @ {url}")
        return None

    resp.encoding = "utf-8"     # 页面是 UTF-8，不要用 apparent_encoding
    return resp.text


def save_html(start, html):
    """把原始页面落盘，供离线调试解析逻辑，避免反复请求。"""
    os.makedirs(HTML_DIR, exist_ok=True)
    path = os.path.join(HTML_DIR, f"top250_start{start}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def load_html(start):
    """优先读本地缓存，没有则返回 None。"""
    path = os.path.join(HTML_DIR, f"top250_start{start}.html")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return None


# ============================================================
# 3. 解析层（补全完成）
# ============================================================
def parse_one_row(row, rank):
    """
    从一行 <tr class="item"> 中抽出 10 个字段，返回 dict。

    row : BeautifulSoup 的 Tag 对象，代表一本书
    rank: 该书的排名（由外部计算好传入）
    """
    item = {f: "" for f in FIELDS}
    item["rank"] = rank

    # ---------- TODO 1：书名 ----------
    a_tag = row.select_one("div.pl2 > a")
    if a_tag:
        item["book_name"] = a_tag.get("title", "").strip()

    # ---------- TODO 2：作者 / 出版社 / 日期 / 价格 ----------
    # 不能按固定位置倒序切！实测有两种破坏性情况：
    #   ① 套装书价格本身带斜杠："... / 1981-8 / 53.00元/68.00元" → 切成 6 段
    #   ② 网页缺价格："叶永烈 / 少年儿童出版社 / 1962-12" → 只有 3 段
    # 正确做法：先用正则找到"出版日期"这一段作为锚点，其余按它前后分配。
    pl = row.select_one("p.pl")
    info_raw = pl.get_text(strip=True) if pl else ""
    item["info_raw"] = info_raw                      # 原文留档，清洗阶段可复核
    parts = [p.strip() for p in info_raw.split("/") if p.strip()]

    # 从后往前找第一个形如日期的段
    date_idx = -1
    for idx in range(len(parts) - 1, -1, -1):
        if DATE_RE.match(parts[idx]):
            date_idx = idx
            break

    if date_idx >= 0:
        item["publish_date"] = parts[date_idx]
        # 日期之后的都是价格（可能是空、一个价、或 "53.00元/68.00元" 两个价）
        item["price"] = "/".join(parts[date_idx + 1:])
        # 日期前一段是出版社，再往前全部是作者信息（可能含译者）
        item["publisher"] = parts[date_idx - 1] if date_idx >= 1 else ""
        item["author_raw"] = " / ".join(parts[:date_idx - 1])
    else:
        # 找不到日期：整串先归到作者，避免信息丢失，交给清洗阶段人工判断
        item["author_raw"] = " / ".join(parts)

    # ---------- TODO 3：评分 / 评价人数 ----------
    rating_tag = row.select_one(".rating_nums")
    if rating_tag:
        item["rating"] = rating_tag.get_text(strip=True)
    count_tag = row.select_one(".star .pl")
    if count_tag:
        cnt_text = count_tag.get_text()
        m = re.search(r"(\d+)", cnt_text)
        if m:
            item["rating_count"] = m.group(1)

    # ---------- TODO 4：短评 / 链接 ----------
    quote_tag = row.select_one(".quote .inq")
    if quote_tag:
        item["quote"] = quote_tag.get_text(strip=True)
    link_tag = row.select_one("a.nbg")
    if link_tag:
        item["url"] = link_tag.get("href", "").strip()

    return item


def parse_page(html, start):
    """解析一整页，返回记录列表。"""
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("div.indent tr.item")

    if not rows:
        print(f"[警告] start={start} 没有解析到任何行，页面结构可能变了")

    # 页面没有排名元素，用 start + 页内序号 + 1 计算
    return [parse_one_row(row, start + i + 1) for i, row in enumerate(rows)]


# ============================================================
# 4. 校验层（已写完）
# ============================================================
def check(records):
    """采集完立刻自检，能直接看出哪个字段为空。"""
    print("=" * 46)
    print(f"总条数：{len(records)}（期望 250）")

    ranks = [r["rank"] for r in records]
    print(f"排名连续：{ranks == list(range(1, len(records) + 1))}")

    for f in FIELDS:
        empty = sum(1 for r in records if str(r[f]).strip() == "")
        if empty:
            print(f"  空值字段 {f}: {empty} 条")
    print("=" * 46)


# ============================================================
# 5. 存储层（已写完）
# ============================================================
def save_csv(records, path):
    """保存为 CSV，utf-8-sig 保证 Excel 直接打开不乱码。"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    print(f"已保存：{path}")


# ============================================================
# 6. 主流程（已写完）
# ============================================================
def main():
    print("===== 豆瓣Top250爬虫启动 =====")
    os.makedirs(OUT_DIR, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    all_records = []
    total = len(START_LIST)

    for i, start in enumerate(START_LIST, 1):
        html = load_html(start)         # 有缓存就不再请求网络
        from_cache = html is not None

        if html is None:
            html = fetch_page(start, session)
            if html is None:
                print("采集中断，保留已取到的数据")
                break
            save_html(start, html)

        recs = parse_page(html, start)
        all_records.extend(recs)
        tag = "缓存" if from_cache else "网络"
        print(f"[{i}/{total}] start={start:>3}  解析 {len(recs)} 条  "
              f"累计 {len(all_records)}  （{tag}）")

        # 只在真正发起网络请求后才延时
        if i < total and not from_cache:
            time.sleep(random.uniform(*DELAY_RANGE))

    check(all_records)

    if all_records:
        out = os.path.join(OUT_DIR, f"books_raw_{date.today():%Y%m%d}.csv")
        save_csv(all_records, out)


# ========== 启动入口，已经加上了 ==========
if __name__ == "__main__":
    main()
