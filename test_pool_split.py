"""split_pool 的测试。运行：python -m pytest -v --tb=short

硬规则：所有人拿到的金额之和必须正好等于 pool_cents。
除手写样例外，还用了两种不依赖手写样例的方法：
  · 穷举：小范围内的全部输入，共 39576 组；
  · 基于性质的随机测试（Hypothesis）：每次 2000 组，含远超 float 精度的大整数，
    出错时自动缩减成最小反例。
最后三个测试检查「剩下的几分钱给谁」：每人先拿精确份额的整数部分，剩下的按被舍掉的
小数部分从大到小每人补 1 分，小数部分相同的按列表顺序；并用暴力枚举确认这样分最接近精确份额。
"""

import itertools
import math
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pool_split import split_pool

# pool 0..50 分，1~4 人，每人权重 0..4（排除全为 0）
SMALL_INPUTS = [
    (pool_cents, list(weights))
    for n in range(1, 5)
    for weights in itertools.product(range(5), repeat=n)
    if any(weights)
    for pool_cents in range(51)
]

# 暴力枚举所有分法时用更小的范围：pool 0..12 分，1~3 人
TINY_INPUTS = [(p, w) for p, w in SMALL_INPUTS if p <= 12 and len(w) <= 3]

# 较小的整数，以及远超 float 53 位精度的大整数
ints = st.one_of(
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=10**30),
)


def assert_sum_equals_pool(pool_cents, weights, amounts):
    assert sum(amounts) == pool_cents, (
        f"split_pool({pool_cents}, {weights}) = {amounts}，和为 {sum(amounts)}，应为 {pool_cents}"
    )


def assert_largest_remainder(pool_cents, weights, amounts):
    """检查结果与用分数精确算出的最大余数法分配逐项相同。

    每人先拿精确份额的整数部分；剩下的 pool_cents - Σ整数部分 分钱，补给小数部分最大的
    那几个人，每人 1 分，小数部分相同的按列表顺序。
    """
    total = sum(weights)
    exact = [Fraction(pool_cents * w, total) for w in weights]
    expected = [math.floor(x) for x in exact]
    by_fraction = sorted(range(len(weights)), key=lambda i: (-(exact[i] % 1), i))
    for i in by_fraction[: pool_cents - sum(expected)]:
        expected[i] += 1
    assert amounts == expected, (
        f"split_pool({pool_cents}, {weights}) = {amounts}，应为 {expected}"
    )


def all_splits(pool_cents, n):
    """所有由 n 个非负整数组成、总和为 pool_cents 的分法（隔板法）。"""
    for bars in itertools.combinations(range(pool_cents + n - 1), n - 1):
        edges = (-1, *bars, pool_cents + n - 1)
        yield [right - left - 1 for left, right in itertools.pairwise(edges)]


def scaled_deviations(pool_cents, weights, amounts):
    """每人与精确份额的偏差，乘以 total 后都是整数。"""
    total = sum(weights)
    return [
        abs(a * total - pool_cents * w) for a, w in zip(amounts, weights, strict=True)
    ]


# ---------- 硬规则：和等于池子总额 ----------


@pytest.mark.parametrize(
    ("pool_cents", "weights"),
    [
        pytest.param(10000, [1, 1, 1], id="10000-[1,1,1]"),
        pytest.param(100, [1] * 6, id="100-[1]*6"),
        pytest.param(1, [1, 1], id="1-[1,1]"),
        pytest.param(3, [1, 1], id="3-[1,1]"),
        pytest.param(5, [1, 1], id="5-[1,1]"),
    ],
)
def test_known_counterexamples(pool_cents, weights):
    assert_sum_equals_pool(pool_cents, weights, split_pool(pool_cents, weights))


def test_sum_rule_exhaustive_small_inputs():
    assert len(SMALL_INPUTS) == 39576
    wrong = []
    for pool_cents, weights in SMALL_INPUTS:
        amounts = split_pool(pool_cents, weights)
        if sum(amounts) != pool_cents:
            wrong.append(
                f"split_pool({pool_cents}, {weights}) = {amounts}，和为 {sum(amounts)}"
            )
    if wrong:
        examples = "\n".join(wrong[:5])
        pytest.fail(
            f"{len(wrong)}/{len(SMALL_INPUTS)} 组输入的和不等于奖池，例如：\n{examples}"
        )


@settings(max_examples=2000, derandomize=True, database=None, deadline=None)
@given(pool_cents=ints, weights=st.lists(ints, min_size=1, max_size=30).filter(any))
def test_properties_hold_for_random_inputs(pool_cents, weights):
    amounts = split_pool(pool_cents, weights)
    assert_sum_equals_pool(pool_cents, weights, amounts)
    assert len(amounts) == len(weights)
    assert all(type(a) is int and a >= 0 for a in amounts)
    assert_largest_remainder(pool_cents, weights, amounts)


@pytest.mark.parametrize(
    ("pool_cents", "weights", "expected"),
    [
        pytest.param(2**53 + 1, [1], [2**53 + 1], id="float-cannot-represent"),
        pytest.param(10**400, [1, 1], [5 * 10**399] * 2, id="float-overflow"),
    ],
)
def test_exact_beyond_float_range(pool_cents, weights, expected):
    assert split_pool(pool_cents, weights) == expected


def test_weights_may_be_an_iterator():
    assert split_pool(100, iter([1, 3])) == [25, 75]


# ---------- 边界与非法输入 ----------


@pytest.mark.parametrize(
    "weights",
    [
        pytest.param([1, 2, 3], id="some-weights"),
        pytest.param([0, 0], id="all-weights-zero"),
        pytest.param([], id="nobody"),
    ],
)
def test_zero_pool_gives_everyone_zero(weights):
    assert split_pool(0, weights) == [0] * len(weights)


@pytest.mark.parametrize(
    ("pool_cents", "weights", "error"),
    [
        pytest.param(100, [], ValueError, id="nobody-to-pay"),
        pytest.param(100, [0, 0], ValueError, id="all-weights-zero"),
        pytest.param(-100, [1, 2], ValueError, id="negative-pool"),
        pytest.param(100, [2, -1], ValueError, id="negative-weight"),
        pytest.param(100, [1.5, 2], TypeError, id="float-weight"),
        pytest.param(100.0, [1, 2], TypeError, id="float-pool"),
    ],
)
def test_invalid_input_raises(pool_cents, weights, error):
    with pytest.raises(error):
        split_pool(pool_cents, weights)


# ---------- 分配策略：剩下的几分钱给谁 ----------


@pytest.mark.parametrize(
    ("pool_cents", "weights", "expected"),
    [
        pytest.param(10000, [1, 1, 1], [3334, 3333, 3333], id="tie-by-order"),
        pytest.param(100, [1] * 6, [17, 17, 17, 17, 16, 16], id="4-cents-left"),
        pytest.param(100, [1, 2], [33, 67], id="larger-remainder-first"),
        pytest.param(10, [1, 2, 3], [2, 3, 5], id="integer-share-unchanged"),
        pytest.param(5, [0, 1, 1], [0, 3, 2], id="zero-weight-gets-nothing"),
    ],
)
def test_leftover_cents_go_to_largest_remainders(pool_cents, weights, expected):
    assert split_pool(pool_cents, weights) == expected


def test_largest_remainder_rule_exhaustive_small_inputs():
    for pool_cents, weights in SMALL_INPUTS:
        assert_largest_remainder(pool_cents, weights, split_pool(pool_cents, weights))


def test_split_is_closest_to_exact_shares():
    """暴力枚举所有和等于奖池的分法：结果与精确份额的总偏差、最大偏差都是最小的。"""
    assert len(TINY_INPUTS) == 1976
    for pool_cents, weights in TINY_INPUTS:
        amounts = split_pool(pool_cents, weights)
        assert_sum_equals_pool(pool_cents, weights, amounts)
        ours = scaled_deviations(pool_cents, weights, amounts)
        candidates = [
            scaled_deviations(pool_cents, weights, split)
            for split in all_splits(pool_cents, len(weights))
        ]
        call = f"split_pool({pool_cents}, {weights}) = {amounts}"
        assert sum(ours) == min(map(sum, candidates)), f"{call}，总偏差不是最小"
        assert max(ours) == min(map(max, candidates)), f"{call}，最大偏差不是最小"
