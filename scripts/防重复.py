#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""防重复台账：连着发之前先查一遍，哪几个开头用过了。

单条回复看不出模板感，连着三条就露。语料补不上的时候，用机制压。

用法：
    python scripts\\防重复.py --history 已发.txt
    python scripts\\防重复.py --text "那还等啥 上号|那不打 听你的|行 那我这手归你管了"
"""
import argparse
import re
import sys

OPENERS = ["那", "嗯", "行", "我", "你", "好", "就", "这", "哈"]
CALLS = ["老公", "老婆", "宝宝", "宝", "亲爱的", "宝贝", "哥哥", "姐姐", "小笨蛋", "笨蛋"]


def load(args):
    if args.text:
        return [x.strip() for x in args.text.split("|") if x.strip()]
    with open(args.history, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", default="")
    ap.add_argument("--text", default="")
    a = ap.parse_args()
    lines = load(a)
    if not lines:
        print("没有输入")
        return

    n = len(lines)
    lens = [len(re.sub(r"\s", "", x)) for x in lines]
    avg = sum(lens) / n

    # 首字
    firsts = [x[0] for x in lines]
    fc = {}
    for c in firsts:
        fc[c] = fc.get(c, 0) + 1

    # 起手词（前两个字里出现的口语虚词）
    used_open = [o for o in OPENERS if sum(1 for x in lines if x.startswith(o)) >= 1]

    # 称呼
    calls = {}
    for w in CALLS:
        c = sum(x.count(w) for x in lines)
        if c:
            calls[w] = c

    # 问句 / 感叹
    q = sum(x.count("?") + x.count("？") for x in lines)
    excl = sum(x.count("!") + x.count("！") for x in lines)

    # 句式骨架（去掉实词，只看形状）
    shape = []
    for x in lines:
        s = re.sub(r"\s", "", x)
        sk = ("短" if len(s) <= 6 else ("中" if len(s) <= 12 else "长"))
        sk += "·问" if ("?" in x or "？" in x) else "·陈"
        shape.append(sk)

    print(f"已发 {n} 条 | 平均 {avg:.1f} 字 | 问句 {q} | 感叹 {excl}")
    print("首字：" + "  ".join(f"{k}×{v}" if v > 1 else k for k, v in fc.items()))

    warn = []
    worst = max(fc.values())
    if worst >= 2:
        hot = [k for k, v in fc.items() if v == worst]
        warn.append(f"首字「{'、'.join(hot)}」已用 {worst} 次 —— 下一条必须换")
    if len(set(firsts)) == 1:
        warn.append("所有条同一首字，模板味最重")
    if n >= 3 and q == 0:
        warn.append("连着 3 条以上没有问句 —— 全在自说自话，给她留个口")
    if n >= 4 and len(set(shape)) == 1:
        warn.append("句式骨架完全一样（" + shape[0] + "）—— 换长句或拆成两条")
    if excl >= 2:
        warn.append("感叹号偏多，像在吵架")

    print("称呼：" + ("、".join(f"{k}×{v}" for k, v in calls.items()) if calls else "一条都没用"))
    if n >= 4 and not calls:
        warn.append("四条以上没叫过称呼 —— 对方叫了你没叫，热度会断层")
    print("句式形态：" + " / ".join(shape))

    print("-" * 46)
    if warn:
        print("这条发之前先改：")
        for i, w in enumerate(warn, 1):
            print(f"  {i}. {w}")
        ban = "、".join(sorted({x[0] for x in lines}))
        print(f"\n建议本轮禁用起手：{ban}")
    else:
        print("没有重复迹象，可以发。")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
