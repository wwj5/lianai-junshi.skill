# -*- coding: utf-8 -*-
"""从 200 段实录里按 阶段 + 性格 + 句式 捞真实对话，供 skill 参考。

用法示例：
  python 工具\取料.py --stage 冲突 --tag 女性格:戏多 --n 3
  python 工具\取料.py --stage 暧昧,初识 --style 短句 --n 5
  python 工具\取料.py --list
  python 工具\取料.py --stage 挽回 --n 3 --brief
"""
import argparse
import json
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import JSONL as SRC


def load(minlen=15):
    rows = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("roles_conf") != "ok":
                continue
            if sum(len(t) for w, t in r["turns"]) < minlen:
                continue
            rows.append(r)
    return rows


def tag_value(r, key):
    for t in r.get("tags", []):
        if t.startswith(key + ":"):
            return t.split(":", 1)[1]
    return ""


def score(r, stages, tags, styles):
    """返回 (分数, 命中的标签数)；None 表示不符合阶段条件被排除。"""
    s = 0.5
    if stages:
        if r["stage"] not in stages:
            return None
        s += 5
    hit_tags = 0
    for t in tags:
        key, val = (t.split(":", 1) + [""])[:2]
        cur = tag_value(r, key)
        if cur and val and cur == val:
            hit_tags += 1
            s += 2
        elif cur and (not val or val in cur):
            hit_tags += 1
            s += 1
    if tags and hit_tags == 0:
        s -= 1   # 库里标签只覆盖四成，缺标签的段降权保留，不直接排除
    st = r.get("style") or {}
    for w in styles:
        if w in ("碎片连发", "短句", "中长句", "长段"):
            if st.get("pattern") == w:
                s += 2
        elif w in ("无标点", "半标点", "全标点", "问号多", "省略号多", "空格断句"):
            if st.get("punct") == w:
                s += 2
    return s, hit_tags


def render(r, brief=False, idx=None):
    roles = r["roles"]
    male, female = roles.get("男"), roles.get("女")
    st = r.get("style") or {}
    fv = tag_value(r, "女性格")
    mv = tag_value(r, "男性格")
    res = tag_value(r, "结果")
    lines = []
    if idx is not None:
        lines.append("── 样例 %d " % idx + "─" * 26)
    if not brief:
        meta = [r["stage"]]
        if fv:
            meta.append("女方" + fv)
        if mv:
            meta.append("男方" + mv)
        lines.append(" | ".join(meta))
        sub = []
        if st:
            sub.append("%s·%s" % (st.get("pattern", "?"), st.get("punct", "?")))
            sub.append("平均%d字" % st.get("len_avg", 0))
            if st.get("inverted"):
                sub.append("有倒装")
        if res:
            sub.append("结果:" + res)
        sub.append(r["source"])
        lines.append(" ".join(sub))
    for w, t in r["turns"]:
        if w == male:
            who = "男方"
        elif w == female:
            who = "女方"
        else:
            who = w + "(?)"
        lines.append("%s：%s" % (who, t))
    return "\n".join(lines)


def cmd_list(rows):
    print("可用阶段（%d 段）：" % len(rows))
    for k, v in Counter(r["stage"] for r in rows).most_common():
        print("  %-6s %d" % (k, v))
    print("\n女性格 / 男性格取值：")
    for key in ("女性格", "男性格"):
        vals = Counter(tag_value(r, key) for r in rows if tag_value(r, key))
        print("  %s：%s" % (key, "、".join("%s(%d)" % (k, v) for k, v in vals.most_common())))
    print("\n句式：")
    for key in ("pattern", "punct"):
        vals = Counter((r.get("style") or {}).get(key) for r in rows)
        print("  %-8s %s" % (key, "、".join("%s(%d)" % (k, v) for k, v in vals.most_common() if k)))
    print("\n结果：")
    vals = Counter(tag_value(r, "结果") for r in rows if tag_value(r, "结果"))
    print("  " + "、".join("%s(%d)" % (k, v) for k, v in vals.most_common()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="", help="阶段，可逗号分隔")
    ap.add_argument("--tag", default="", help="标签如 女性格:戏多，可逗号分隔")
    ap.add_argument("--style", default="", help="句式如 短句/碎片连发/无标点")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--brief", action="store_true", help="只输出对话本身")
    ap.add_argument("--list", action="store_true", help="列出可用取值")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--minlen", type=int, default=15, help="总字数低于此值的段直接跳过")
    a = ap.parse_args()

    rows = load(a.minlen)
    if a.list:
        cmd_list(rows)
        return

    stages = [x.strip() for x in a.stage.split(",") if x.strip()]
    tags = [x.strip() for x in a.tag.split(",") if x.strip()]
    styles = [x.strip() for x in a.style.split(",") if x.strip()]
    n = max(1, min(a.n, 10))

    scored = []
    exact = 0
    for r in rows:
        res = score(r, stages, tags, styles)
        if res is None:
            continue
        s, hit = res
        if tags and hit:
            exact += 1
        scored.append((s, r))
    if not scored and a.minlen > 0:
        print("（该档没有超过 %d 字的段落，把长度门槛放宽到 0 重试）" % a.minlen)
        for r in load(0):
            res = score(r, stages, tags, styles)
            if res is None:
                continue
            scored.append((res[0], r))
    if not scored:
        print("没有匹配的段落。放宽条件：先去掉 --tag，或换 --stage。可用取值见 --list。")
        return

    random.seed(a.seed)
    # 同分时优先人工标注段：规则匹配判"冷淡""日常"容易把打情骂俏判成冷场
    scored.sort(key=lambda x: (-x[0],
                               0 if "人工" in (x[1].get("stage_method") or "") else 1,
                               random.random()))
    picked = scored[:n]

    extra = ""
    if tags:
        extra = "，其中按标签精确命中 %d 段、其余按阶段/句式降级匹配" % exact
    print("命中 %d 段%s，取前 %d（条件：阶段=%s 标签=%s 句式=%s）\n"
          % (len(scored), extra, len(picked), a.stage or "不限", a.tag or "不限", a.style or "不限"))
    if "日常" in stages:
        cnt = sum(1 for _s, _r in scored if _r["stage"] == "日常")
        print("注意：日常档是兜底档，当前可检索 %d 段，全部是\"轮数不足或不是情侣对话、档位判不了\"才落在这里的。"
              "借口气可以，别拿它当阶段依据；要聊正经阶段，换成初识/暧昧/热恋/冲突。\n" % cnt)
    for i, (s, r) in enumerate(picked, 1):
        print(render(r, a.brief, None if a.brief else i))
        if not a.brief:
            print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
