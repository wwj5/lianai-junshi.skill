#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""话术体检：把 SKILL.md 的硬规则变成可机械判的项，给生成的回复打分。

用法：
    python scripts\检查话术.py --text "噢噢 就没了？" --peer 2
    python scripts\检查话术.py --text "..." --peer 8 --stage 冲突
"""
import argparse
import re
import sys

# 出现即硬错：说明这不是能直接发的话，是在教人说话
INSTRUCTION_PATTERNS = [
    r"你可以(试着)?说", r"你可以(试|尝试)", r"类似的话", r"大概是这",
    r"建议你", r"不如这样", r"比如说", r"举个例子", r"以下几个",
    r"方案[一二三ABC]", r"选项[一二三ABC]",
]

# AI 腔 / 客服腔
AI_TONE = [
    "首先", "其次", "再者", "总的来说", "综上", "需要注意的是",
    "希望(这|以上)", "帮到你", "加油哦", "相信你", "祝你",
    "理解你的感受", "你的感受是(很)?(正常|重要)", "这很正常",
    "可以理解", "非常(重要|关键)", "值得注意",
]

# 空心正确话：说了等于没说
HOLLOW = [
    "真诚", "温柔", "用心", "自然(一点|而然)?", "放松(一点)?", "自信(一点)?",
    "保持(良好|积极)", "展现(你的)?(价值|魅力)", "尊重对方", "适度", "分寸感",
]

# 承诺式空话：真人也会说，AI 特别爱说，所以判警告不判错
SOFT = [
    "你要相信", "一直陪", "不会离开", "我们的感情", "时间会证明",
    "别想太多", "一切都会", "永远(都)?(爱|在)", "相信我", "给彼此一点时间",
]

# 分点结构痕迹
STRUCT = [r"^\s*[1-9１-９][\.、）)]", r"^\s*[-*•]\s", r"^\s*[①②③④⑤]"]


def count_sentences(t):
    return len([s for s in re.split(r"[。！？!?\n]", t) if s.strip()])


def check(text, peer_len=None, stage=None):
    t = text.strip()
    res = []          # (等级, 项目, 说明)  等级：错误 / 警告 / 提示 / 通过
    raw = re.sub(r"[\s\n]", "", t)
    n = len(raw)

    # 1 是否可直接发送
    for p in INSTRUCTION_PATTERNS:
        if re.search(p, t):
            res.append(("错误", "可直接发送", f"命中指导语「{re.search(p, t).group()}」——这是教人说话，不是话本身"))
            break
    else:
        res.append(("通过", "可直接发送", "没有任何指导语/方案化表述"))

    # 2 方案数量
    cues = len(re.findall(r"或者|也可以|要么|另一个", t))
    if cues >= 2:
        res.append(("错误", "只给一个", f"出现 {cues} 处备选连接词，读起来是 ABC 方案"))
    else:
        res.append(("通过", "只给一个", "单一路径"))

    # 3 长度匹配
    # 对方只回"嗯""噢噢""哦"这种极短句时，倍数判据会全员误杀（8 字对 2 字就是 4 倍，
    # 但真人对"噢噢"回一句 8 字完全正常）。这种改用绝对字数判。
    if peer_len:
        ratio = n / max(peer_len, 1)
        if peer_len <= 3:
            if n > 12:
                res.append(("错误", "长度匹配", f"对方只回 {peer_len} 字，你回 {n} 字，一句话把她堵死"))
            elif n > 8:
                res.append(("警告", "长度匹配", f"对方 {peer_len} 字，你 {n} 字，比短句回短句略长"))
            else:
                res.append(("通过", "长度匹配", f"对方 {peer_len} 字，你 {n} 字，短接短"))
        elif ratio > 3.5:
            res.append(("错误", "长度匹配", f"{n} 字 vs 对方 {peer_len} 字，{ratio:.1f} 倍——对方一句你一篇"))
        elif ratio > 2.2:
            res.append(("警告", "长度匹配", f"{ratio:.1f} 倍，偏长一档"))
        elif n <= 2 and peer_len >= 6:
            res.append(("警告", "长度匹配", "对方给了六字以上，你两个以下，接不住"))
        else:
            res.append(("通过", "长度匹配", f"{ratio:.1f} 倍，跟得上"))
    else:
        res.append(("提示", "长度匹配", f"未提供对方字数，本条 {n} 字"))

    # 4 问句
    q = t.count("?") + t.count("？")
    if q >= 3:
        res.append(("错误", "问句数量", f"{q} 个问号，像审讯"))
    elif q == 2:
        res.append(("警告", "问句数量", "连续两个问号，压得有点紧"))
    else:
        res.append(("通过", "问句数量", "不超过一个问号"))

    # 5 AI 腔
    hits = [w for w in AI_TONE if w in t]
    if hits:
        res.append(("错误", "去 AI 腔", "命中 " + "、".join(hits)))
    else:
        res.append(("通过", "去 AI 腔", "无客服腔词"))

    # 6 空心话
    hh = [w for w in HOLLOW if re.search(w, t)]
    if hh:
        res.append(("错误", "有实内容", "命中空心词 " + "、".join(hh)))
    else:
        res.append(("通过", "有实内容", "无空心词"))

    soft = [w for w in SOFT if re.search(w, t)]
    if soft:
        res.append(("警告", "空话风险", "命中 " + "、".join(soft) + "，确认这事你能兑现再发"))

    # 7 标点形态（默认空格断句、不打句号，口径见 references/口吻.md「标点」一节）
    commas = t.count("，") + t.count(",")
    per = t.count("。")
    dup = len(re.findall(r"[？！]\s*[？！]", t))
    if n:
        dens = (t.count("，") + t.count("。") + t.count("！") + t.count("？")) / n
        if dens > 0.18 and n > 8:
            res.append(("警告", "标点形态", f"标点密度 {dens:.2f}，偏书面"))
        else:
            res.append(("通过", "标点形态", f"标点密度 {dens:.2f}，口语态"))
    if per >= 1:
        res.append(("警告", "标点形态", f"{per} 个句号，真人聊天不打句号"))
    if commas >= 1:
        res.append(("警告", "标点形态", f"{commas} 个逗号，改用空格断"))
    if dup:
        res.append(("警告", "标点形态", f"问号叹号连用 {dup} 处"))
    if commas == 0 and per == 0 and (" " in t or "\u3000" in t):
        res.append(("通过", "标点形态", "空格断句，是目标形态"))

    # 8 结构痕迹
    for p in STRUCT:
        if re.search(p, t, re.M):
            res.append(("错误", "无排版腔", "出现分点/项目符号"))
            break
    else:
        res.append(("通过", "无排版腔", "无分点符号"))

    # 9 自我中心：全问句、没自己的东西
    mine = bool(re.search(r"我", t))
    if q >= 1 and not mine:
        res.append(("警告", "有自己", "只有问句，没有你自己的东西"))

    return n, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--peer", type=int, default=0, help="对方最后一条的字数")
    ap.add_argument("--stage", default="")
    a = ap.parse_args()

    n, res = check(a.text, a.peer or None, a.stage)
    errs = sum(1 for g, _, _ in res if g == "错误")
    warns = sum(1 for g, _, _ in res if g == "警告")
    print(f"\n话术：{a.text.strip()}")
    print(f"字数 {n}" + (f" / 对方 {a.peer}" if a.peer else "") + (f" / 阶段 {a.stage}" if a.stage else ""))
    print("-" * 46)
    for grade, item, note in res:
        mark = {"通过": " ok ", "提示": " .. ", "警告": " !  ", "错误": " XX "}[grade]
        print(f"[{mark}] {item}：{note}")
    print("-" * 46)
    print(f"结论：{errs} 项错误 / {warns} 项警告 → " + ("不合格" if errs else ("可用，有偏" if warns else "合格")))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
