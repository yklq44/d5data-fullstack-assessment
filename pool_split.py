"""
pool_split.py —— 每日瓜分奖池的分账逻辑

这是我们线上「每日瓜分奖池」的真实代码，为这道题做了简化
（去掉了数据库读写和日期处理，只留下算钱的部分）。

背景：
  平台每天放一个奖池。当天达标的用户，按各自的贡献权重瓜分池子里的钱。

约定：
  · 所有金额都是整数「分」，系统里不存在半分钱。
  · weights 是每个人的贡献权重（线上用的是「合格采集秒数」）。

硬规则（产品定的，不能破）：
  分完之后，所有人拿到的钱加起来必须【正好等于】池子总额。
  多一分 = 平台凭空多发了钱。
  少一分 = 有人的钱卡在系统里没发出去。
"""

import operator


def split_pool(pool_cents: int, weights: list[int]) -> list[int]:
    """把 pool_cents 按 weights 的比例分给每个人，返回每人拿到多少分。

    返回列表与 weights 一一对应，且所有人的钱加起来正好等于 pool_cents。

    分法（最大余数法），全程整数运算，不经过 float：
      1. 每人先拿精确份额 pool_cents * w / total 的整数部分；
      2. 整数部分加起来比池子少的那几分钱（一定少于人数），
         按被舍掉的小数部分从大到小，每人补 1 分；小数部分相同的，按在 weights 中的顺序。
    因此每人拿到的钱与精确份额相差不到 1 分，权重为 0 的人拿 0。

    池子有钱但没有任何正权重（没人可分）、pool_cents 或权重为负时抛 ValueError，
    不是整数时抛 TypeError，而不是返回一个和不对的结果。
    """
    pool_cents = operator.index(pool_cents)
    weights = [operator.index(w) for w in weights]
    if pool_cents < 0:
        raise ValueError(f"pool_cents 不能为负数：{pool_cents}")
    for i, w in enumerate(weights):
        if w < 0:
            raise ValueError(f"weights[{i}] = {w}，权重不能为负数")

    total = sum(weights)
    if total == 0:
        if pool_cents == 0:
            return [0] * len(weights)
        raise ValueError(f"没有任何正权重，{pool_cents} 分无法分配")

    shares = [divmod(pool_cents * w, total) for w in weights]
    amounts = [quotient for quotient, _ in shares]
    leftover = pool_cents - sum(amounts)
    # sorted 是稳定排序：余数相同的人保持在 weights 中的先后顺序
    by_remainder = sorted(range(len(weights)), key=lambda i: shares[i][1], reverse=True)
    for i in by_remainder[:leftover]:
        amounts[i] += 1
    return amounts


if __name__ == "__main__":
    # 一个跑得通的例子：奖池 100 元，三个人权重相同
    print(split_pool(10000, [1, 1, 1]))
