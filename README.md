# 奖池分账 `split_pool`：笔试作答

**结论**：原来的 `split_pool` 对每个人单独 `round`，舍入误差累加起来就会多发或少发，例如 `split_pool(10000, [1, 1, 1])` 只发出 9999 分。改为整数运算 + 最大余数法后，任何合法输入分完的总和都正好等于奖池，每人与精确份额相差不到 1 分；非法输入直接报错。同一套测试在原始代码上有 22 个失败，修改后 26 个全部通过。

| 文件 | 内容 |
|---|---|
| `pool_split.py` | 修改后的代码 |
| `test_pool_split.py` | 测试 |
| `README.md` | 第 1、3、4 项的说明，以及可选问题的回答 |
| `mutation_check.py` | 检验测试本身：把代码逐一改错，确认测试都能发现（见第 4 项） |
| `requirements.txt` | 测试依赖（pytest、Hypothesis） |

仓库按作答顺序提交：题目附件的原始代码（`d3e4d96`）→ 测试 → 修复 → 变异测试脚本 → README。

## 1. 会出错的输入

| pool_cents | weights | 当前代码返回 | 实际的和 | 应有的和 |
|---:|---|---|---:|---:|
| 10000 | `[1, 1, 1]` | `[3333, 3333, 3333]` | **9999** | 10000 |
| 100 | `[1, 1, 1, 1, 1, 1]` | `[17, 17, 17, 17, 17, 17]` | **102** | 100 |

第一组就是原文件 `__main__` 里那个"跑得通的例子"：程序不报错，但少发了 1 分。第二组方向相反，平台多发了 2 分。

原因：代码对每个人的份额**分别** `round`，再把结果相加。每个人的舍入误差不超过 0.5 分，但 n 个人的误差会累加，方向也不一定能抵消：三人各被舍掉 1/3 分，合计少 1 分；六人各被进位 1/3 分，合计多 2 分。把 `round`（Python 是"四舍六入五成双"）换成普通四舍五入、向下取整或向上取整，结果一样会错。问题出在逐人独立舍入，和用哪种舍入规则无关。

## 2. 修改方式

`split_pool` 的签名不变，正常输入的返回值仍是与 `weights` 一一对应的整数列表。

1. **全程整数运算**：用 `divmod(pool_cents * w, total)` 求每人精确份额的整数部分和余数，不经过 float。
2. **最大余数法**：先给每人发整数部分，这时一定还剩 `leftover` 分（`0 <= leftover < 人数`）；再按余数从大到小每人补 1 分，余数相同的按在 `weights` 中的顺序。补完后总和正好等于 `pool_cents`。
3. **非法输入显式报错**：奖池有钱但没有任何正权重（包括名单为空）、奖池或权重为负时抛 `ValueError`，不是整数时抛 `TypeError`，不再返回一个和不对的结果，也不会在中途除零崩溃。奖池为 0 时每人 0 分。

决定补给谁需要排序，复杂度为 O(n log n)，本机 100 万人不到 1 秒。

## 3. 测试与两次运行输出

| 测试 | 检查什么 | 输入组数 |
|---|---|---:|
| `test_known_counterexamples` | 第 1 项的反例等手写样例：和等于奖池 | 5 |
| `test_sum_rule_exhaustive_small_inputs` | 穷举奖池 0–50 分、1–4 人、每人权重 0–4 的全部组合：和等于奖池 | 39,576 |
| `test_properties_hold_for_random_inputs` | Hypothesis 随机生成（最多 30 人，数值最大 10^30）：和等于奖池、长度一致、非负整数，且与用 `Fraction` 独立算出的最大余数法结果逐项相同 | 每次 2,000 |
| `test_exact_beyond_float_range` | 超出 float 精度和范围的金额也分得精确 | 2 |
| `test_weights_may_be_an_iterator` | `weights` 传迭代器也能正确分 | 1 |
| `test_zero_pool_gives_everyone_zero` | 奖池为 0 时每人 0 分 | 3 |
| `test_invalid_input_raises` | 非法输入报错，而不是返回错误结果 | 6 |
| `test_leftover_cents_go_to_largest_remainders` | 剩下的几分钱给谁（具体样例） | 5 |
| `test_largest_remainder_rule_exhaustive_small_inputs` | 同一批 39,576 组穷举输入：与用 `Fraction` 独立算出的最大余数法结果逐项相同 | 39,576 |
| `test_split_is_closest_to_exact_shares` | 暴力枚举所有分法（奖池 0–12 分、1–3 人）：结果离精确份额最近 | 1,976 |

### 运行方式

需要 Python 3.11 及以上（Hypothesis 6.170 的要求），下面的输出来自 Python 3.12.10：

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS / Linux：source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -v --tb=short    # 测试
python mutation_check.py          # 检验测试本身（见第 4 项）
```

第一次运行用的是题目附件的原始代码（运行前核对过 `pool_split.py` 的 SHA-256 与附件一致）。复现方法：

```bash
git checkout d3e4d96 -- pool_split.py   # 换回原始代码
python -m pytest -v --tb=short          # 22 failed, 4 passed
git checkout HEAD -- pool_split.py      # 换回修改后的代码
```

### 第一次：未修改的 `split_pool`，失败（22 failed, 4 passed）

- 5 个手写反例全部失败，例如 `split_pool(10000, [1, 1, 1]) = [3333, 3333, 3333]，和为 9999，应为 10000`。
- 穷举结果：`13810/39576 组输入的和不等于奖池`，约 35%。
- Hypothesis 自己找到并缩减出了最小反例 `split_pool(1, [1, 1]) = [0, 0]`：1 分钱分给两个人，`round(0.5)` 等于 0，这 1 分钱没发出去。
- 通过的 4 个是原代码恰好也满足的情形：奖池为 0 的两组（权重 `[1, 2, 3]`、名单为空），以及原代码恰好分对的 `split_pool(100, [1, 2])` 和 `split_pool(10, [1, 2, 3])`。

<details>
<summary>完整输出（264 行）</summary>

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- D:\tasks\fullstack\pool-split\.venv\Scripts\python.exe
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: D:\tasks\fullstack\pool-split
plugins: hypothesis-6.170.15
collecting ... collected 26 items

test_pool_split.py::test_known_counterexamples[10000-[1,1,1]] FAILED     [  3%]
test_pool_split.py::test_known_counterexamples[100-[1]*6] FAILED         [  7%]
test_pool_split.py::test_known_counterexamples[1-[1,1]] FAILED           [ 11%]
test_pool_split.py::test_known_counterexamples[3-[1,1]] FAILED           [ 15%]
test_pool_split.py::test_known_counterexamples[5-[1,1]] FAILED           [ 19%]
test_pool_split.py::test_sum_rule_exhaustive_small_inputs FAILED         [ 23%]
test_pool_split.py::test_properties_hold_for_random_inputs FAILED        [ 26%]
test_pool_split.py::test_exact_beyond_float_range[float-cannot-represent] FAILED [ 30%]
test_pool_split.py::test_exact_beyond_float_range[float-overflow] FAILED [ 34%]
test_pool_split.py::test_weights_may_be_an_iterator FAILED               [ 38%]
test_pool_split.py::test_zero_pool_gives_everyone_zero[some-weights] PASSED [ 42%]
test_pool_split.py::test_zero_pool_gives_everyone_zero[all-weights-zero] FAILED [ 46%]
test_pool_split.py::test_zero_pool_gives_everyone_zero[nobody] PASSED    [ 50%]
test_pool_split.py::test_invalid_input_raises[nobody-to-pay] FAILED      [ 53%]
test_pool_split.py::test_invalid_input_raises[all-weights-zero] FAILED   [ 57%]
test_pool_split.py::test_invalid_input_raises[negative-pool] FAILED      [ 61%]
test_pool_split.py::test_invalid_input_raises[negative-weight] FAILED    [ 65%]
test_pool_split.py::test_invalid_input_raises[float-weight] FAILED       [ 69%]
test_pool_split.py::test_invalid_input_raises[float-pool] FAILED         [ 73%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[tie-by-order] FAILED [ 76%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[4-cents-left] FAILED [ 80%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[larger-remainder-first] PASSED [ 84%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[integer-share-unchanged] PASSED [ 88%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[zero-weight-gets-nothing] FAILED [ 92%]
test_pool_split.py::test_largest_remainder_rule_exhaustive_small_inputs FAILED [ 96%]
test_pool_split.py::test_split_is_closest_to_exact_shares FAILED         [100%]

================================== FAILURES ===================================
__________________ test_known_counterexamples[10000-[1,1,1]] __________________
test_pool_split.py:93: in test_known_counterexamples
    assert_sum_equals_pool(pool_cents, weights, split_pool(pool_cents, weights))
test_pool_split.py:42: in assert_sum_equals_pool
    assert sum(amounts) == pool_cents, (
E   AssertionError: split_pool(10000, [1, 1, 1]) = [3333, 3333, 3333]，和为 9999，应为 10000
E   assert 9999 == 10000
E    +  where 9999 = sum([3333, 3333, 3333])
____________________ test_known_counterexamples[100-[1]*6] ____________________
test_pool_split.py:93: in test_known_counterexamples
    assert_sum_equals_pool(pool_cents, weights, split_pool(pool_cents, weights))
test_pool_split.py:42: in assert_sum_equals_pool
    assert sum(amounts) == pool_cents, (
E   AssertionError: split_pool(100, [1, 1, 1, 1, 1, 1]) = [17, 17, 17, 17, 17, 17]，和为 102，应为 100
E   assert 102 == 100
E    +  where 102 = sum([17, 17, 17, 17, 17, 17])
_____________________ test_known_counterexamples[1-[1,1]] _____________________
test_pool_split.py:93: in test_known_counterexamples
    assert_sum_equals_pool(pool_cents, weights, split_pool(pool_cents, weights))
test_pool_split.py:42: in assert_sum_equals_pool
    assert sum(amounts) == pool_cents, (
E   AssertionError: split_pool(1, [1, 1]) = [0, 0]，和为 0，应为 1
E   assert 0 == 1
E    +  where 0 = sum([0, 0])
_____________________ test_known_counterexamples[3-[1,1]] _____________________
test_pool_split.py:93: in test_known_counterexamples
    assert_sum_equals_pool(pool_cents, weights, split_pool(pool_cents, weights))
test_pool_split.py:42: in assert_sum_equals_pool
    assert sum(amounts) == pool_cents, (
E   AssertionError: split_pool(3, [1, 1]) = [2, 2]，和为 4，应为 3
E   assert 4 == 3
E    +  where 4 = sum([2, 2])
_____________________ test_known_counterexamples[5-[1,1]] _____________________
test_pool_split.py:93: in test_known_counterexamples
    assert_sum_equals_pool(pool_cents, weights, split_pool(pool_cents, weights))
test_pool_split.py:42: in assert_sum_equals_pool
    assert sum(amounts) == pool_cents, (
E   AssertionError: split_pool(5, [1, 1]) = [2, 2]，和为 4，应为 5
E   assert 4 == 5
E    +  where 4 = sum([2, 2])
____________________ test_sum_rule_exhaustive_small_inputs ____________________
test_pool_split.py:107: in test_sum_rule_exhaustive_small_inputs
    pytest.fail(
E   Failed: 13810/39576 组输入的和不等于奖池，例如：
E   split_pool(1, [1, 1]) = [0, 0]，和为 0
E   split_pool(3, [1, 1]) = [2, 2]，和为 4
E   split_pool(5, [1, 1]) = [2, 2]，和为 4
E   split_pool(7, [1, 1]) = [4, 4]，和为 8
E   split_pool(9, [1, 1]) = [4, 4]，和为 8
___________________ test_properties_hold_for_random_inputs ____________________
test_pool_split.py:113: in test_properties_hold_for_random_inputs
    @given(pool_cents=ints, weights=st.lists(ints, min_size=1, max_size=30).filter(any))
                   ^^^
test_pool_split.py:116: in test_properties_hold_for_random_inputs
    assert_sum_equals_pool(pool_cents, weights, amounts)
test_pool_split.py:42: in assert_sum_equals_pool
    assert sum(amounts) == pool_cents, (
E   AssertionError: split_pool(1, [1, 1]) = [0, 0]，和为 0，应为 1
E   assert 0 == 1
E    +  where 0 = sum([0, 0])
E   Failing test case: test_properties_hold_for_random_inputs(
E       pool_cents=1,
E       weights=[1, 1],
E   )
E   Explanation:
E       These lines were always and only run by failing test cases:
E           D:\tasks\fullstack\pool-split\test_pool_split.py:44
____________ test_exact_beyond_float_range[float-cannot-represent] ____________
test_pool_split.py:130: in test_exact_beyond_float_range
    assert split_pool(pool_cents, weights) == expected
E   AssertionError: assert [9007199254740992] == [9007199254740993]
E     
E     At index 0 diff: 9007199254740992 != 9007199254740993
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E       [
E     -     9007199254740993,
E     ?                    ^...
E     
E     ...Full output truncated, use '-vv' to show
________________ test_exact_beyond_float_range[float-overflow] ________________
test_pool_split.py:130: in test_exact_beyond_float_range
    assert split_pool(pool_cents, weights) == expected
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
pool_split.py:27: in split_pool
    return [round(pool_cents * w / total) for w in weights]
                  ^^^^^^^^^^^^^^^^^^^^^^
E   OverflowError: integer division result too large for a float
_______________________ test_weights_may_be_an_iterator _______________________
test_pool_split.py:134: in test_weights_may_be_an_iterator
    assert split_pool(100, iter([1, 3])) == [25, 75]
E   assert [] == [25, 75]
E     
E     Right contains 2 more items, first extra item: 25
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E     + []
E     - [
E     -     25,
E     -     75,
E     - ]
____________ test_zero_pool_gives_everyone_zero[all-weights-zero] _____________
test_pool_split.py:149: in test_zero_pool_gives_everyone_zero
    assert split_pool(0, weights) == [0] * len(weights)
           ^^^^^^^^^^^^^^^^^^^^^^
pool_split.py:27: in split_pool
    return [round(pool_cents * w / total) for w in weights]
                  ^^^^^^^^^^^^^^^^^^^^^^
E   ZeroDivisionError: division by zero
__________________ test_invalid_input_raises[nobody-to-pay] ___________________
test_pool_split.py:164: in test_invalid_input_raises
    with pytest.raises(error):
         ^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE ValueError
_________________ test_invalid_input_raises[all-weights-zero] _________________
test_pool_split.py:165: in test_invalid_input_raises
    split_pool(pool_cents, weights)
pool_split.py:27: in split_pool
    return [round(pool_cents * w / total) for w in weights]
                  ^^^^^^^^^^^^^^^^^^^^^^
E   ZeroDivisionError: division by zero
__________________ test_invalid_input_raises[negative-pool] ___________________
test_pool_split.py:164: in test_invalid_input_raises
    with pytest.raises(error):
         ^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE ValueError
_________________ test_invalid_input_raises[negative-weight] __________________
test_pool_split.py:164: in test_invalid_input_raises
    with pytest.raises(error):
         ^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE ValueError
___________________ test_invalid_input_raises[float-weight] ___________________
test_pool_split.py:164: in test_invalid_input_raises
    with pytest.raises(error):
         ^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE TypeError
____________________ test_invalid_input_raises[float-pool] ____________________
test_pool_split.py:164: in test_invalid_input_raises
    with pytest.raises(error):
         ^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE TypeError
_________ test_leftover_cents_go_to_largest_remainders[tie-by-order] __________
test_pool_split.py:182: in test_leftover_cents_go_to_largest_remainders
    assert split_pool(pool_cents, weights) == expected
E   AssertionError: assert [3333, 3333, 3333] == [3334, 3333, 3333]
E     
E     At index 0 diff: 3333 != 3334
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E       [
E     -     3334,
E     ?        ^...
E     
E     ...Full output truncated, use '-vv' to show
_________ test_leftover_cents_go_to_largest_remainders[4-cents-left] __________
test_pool_split.py:182: in test_leftover_cents_go_to_largest_remainders
    assert split_pool(pool_cents, weights) == expected
E   AssertionError: assert [17, 17, 17, 17, 17, 17] == [17, 17, 17, 17, 16, 16]
E     
E     At index 4 diff: 17 != 16
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E       [
E           17,
E           17,...
E     
E     ...Full output truncated, use '-vv' to show
___ test_leftover_cents_go_to_largest_remainders[zero-weight-gets-nothing] ____
test_pool_split.py:182: in test_leftover_cents_go_to_largest_remainders
    assert split_pool(pool_cents, weights) == expected
E   AssertionError: assert [0, 2, 2] == [0, 3, 2]
E     
E     At index 1 diff: 2 != 3
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E       [
E           0,
E     -     3,...
E     
E     ...Full output truncated, use '-vv' to show
_____________ test_largest_remainder_rule_exhaustive_small_inputs _____________
test_pool_split.py:187: in test_largest_remainder_rule_exhaustive_small_inputs
    assert_largest_remainder(pool_cents, weights, split_pool(pool_cents, weights))
test_pool_split.py:59: in assert_largest_remainder
    assert amounts == expected, (
E   AssertionError: split_pool(1, [1, 1]) = [0, 0]，应为 [1, 0]
E   assert [0, 0] == [1, 0]
E     
E     At index 0 diff: 0 != 1
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E       [
E     -     1,
E     ?     ^...
E     
E     ...Full output truncated, use '-vv' to show
____________________ test_split_is_closest_to_exact_shares ____________________
test_pool_split.py:195: in test_split_is_closest_to_exact_shares
    assert_sum_equals_pool(pool_cents, weights, amounts)
test_pool_split.py:42: in assert_sum_equals_pool
    assert sum(amounts) == pool_cents, (
E   AssertionError: split_pool(1, [1, 1]) = [0, 0]，和为 0，应为 1
E   assert 0 == 1
E    +  where 0 = sum([0, 0])
=========================== short test summary info ===========================
FAILED test_pool_split.py::test_known_counterexamples[10000-[1,1,1]] - Assert...
FAILED test_pool_split.py::test_known_counterexamples[100-[1]*6] - AssertionE...
FAILED test_pool_split.py::test_known_counterexamples[1-[1,1]] - AssertionErr...
FAILED test_pool_split.py::test_known_counterexamples[3-[1,1]] - AssertionErr...
FAILED test_pool_split.py::test_known_counterexamples[5-[1,1]] - AssertionErr...
FAILED test_pool_split.py::test_sum_rule_exhaustive_small_inputs - Failed: 13...
FAILED test_pool_split.py::test_properties_hold_for_random_inputs - Assertion...
FAILED test_pool_split.py::test_exact_beyond_float_range[float-cannot-represent]
FAILED test_pool_split.py::test_exact_beyond_float_range[float-overflow] - Ov...
FAILED test_pool_split.py::test_weights_may_be_an_iterator - assert [] == [25...
FAILED test_pool_split.py::test_zero_pool_gives_everyone_zero[all-weights-zero]
FAILED test_pool_split.py::test_invalid_input_raises[nobody-to-pay] - Failed:...
FAILED test_pool_split.py::test_invalid_input_raises[all-weights-zero] - Zero...
FAILED test_pool_split.py::test_invalid_input_raises[negative-pool] - Failed:...
FAILED test_pool_split.py::test_invalid_input_raises[negative-weight] - Faile...
FAILED test_pool_split.py::test_invalid_input_raises[float-weight] - Failed: ...
FAILED test_pool_split.py::test_invalid_input_raises[float-pool] - Failed: DI...
FAILED test_pool_split.py::test_leftover_cents_go_to_largest_remainders[tie-by-order]
FAILED test_pool_split.py::test_leftover_cents_go_to_largest_remainders[4-cents-left]
FAILED test_pool_split.py::test_leftover_cents_go_to_largest_remainders[zero-weight-gets-nothing]
FAILED test_pool_split.py::test_largest_remainder_rule_exhaustive_small_inputs
FAILED test_pool_split.py::test_split_is_closest_to_exact_shares - AssertionE...
======================== 22 failed, 4 passed in 0.93s =========================
```

</details>

### 第二次：修改后的 `split_pool`，通过（26 passed）

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- D:\tasks\fullstack\pool-split\.venv\Scripts\python.exe
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: D:\tasks\fullstack\pool-split
plugins: hypothesis-6.170.15
collecting ... collected 26 items

test_pool_split.py::test_known_counterexamples[10000-[1,1,1]] PASSED     [  3%]
test_pool_split.py::test_known_counterexamples[100-[1]*6] PASSED         [  7%]
test_pool_split.py::test_known_counterexamples[1-[1,1]] PASSED           [ 11%]
test_pool_split.py::test_known_counterexamples[3-[1,1]] PASSED           [ 15%]
test_pool_split.py::test_known_counterexamples[5-[1,1]] PASSED           [ 19%]
test_pool_split.py::test_sum_rule_exhaustive_small_inputs PASSED         [ 23%]
test_pool_split.py::test_properties_hold_for_random_inputs PASSED        [ 26%]
test_pool_split.py::test_exact_beyond_float_range[float-cannot-represent] PASSED [ 30%]
test_pool_split.py::test_exact_beyond_float_range[float-overflow] PASSED [ 34%]
test_pool_split.py::test_weights_may_be_an_iterator PASSED               [ 38%]
test_pool_split.py::test_zero_pool_gives_everyone_zero[some-weights] PASSED [ 42%]
test_pool_split.py::test_zero_pool_gives_everyone_zero[all-weights-zero] PASSED [ 46%]
test_pool_split.py::test_zero_pool_gives_everyone_zero[nobody] PASSED    [ 50%]
test_pool_split.py::test_invalid_input_raises[nobody-to-pay] PASSED      [ 53%]
test_pool_split.py::test_invalid_input_raises[all-weights-zero] PASSED   [ 57%]
test_pool_split.py::test_invalid_input_raises[negative-pool] PASSED      [ 61%]
test_pool_split.py::test_invalid_input_raises[negative-weight] PASSED    [ 65%]
test_pool_split.py::test_invalid_input_raises[float-weight] PASSED       [ 69%]
test_pool_split.py::test_invalid_input_raises[float-pool] PASSED         [ 73%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[tie-by-order] PASSED [ 76%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[4-cents-left] PASSED [ 80%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[larger-remainder-first] PASSED [ 84%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[integer-share-unchanged] PASSED [ 88%]
test_pool_split.py::test_leftover_cents_go_to_largest_remainders[zero-weight-gets-nothing] PASSED [ 92%]
test_pool_split.py::test_largest_remainder_rule_exhaustive_small_inputs PASSED [ 96%]
test_pool_split.py::test_split_is_closest_to_exact_shares PASSED         [100%]

============================= 26 passed in 3.54s ==============================
```

## 4. AI 使用情况

作答过程中使用了 Cursor 的 Agent 模式（模型为 Claude Opus 5.5）。

**提出的问题**

1. 给出题目链接，要求完成全部作答项：反例、修改、测试和两次运行输出、说明文档。
2. 要求对完成的提交做一次全面复查，按高标准修改。

**得到的回答**

- 第一次：反例及成因分析；整数运算 + 最大余数法的修改；手写样例、穷举和 Hypothesis 随机测试；说明文档。
- 第二次（复查）：
  - 把"这样分最接近精确份额"从一次性脚本改成正式测试 `test_split_is_closest_to_exact_shares`；
  - 最大余数法的检查改为与用 `Fraction` 独立算出的参照结果逐项比较，不再从被测结果本身推算补了几分钱；
  - 把变异测试整理成可复现的 `mutation_check.py`，覆盖 7 种典型的错误写法；
  - 补充 Python 版本要求；
  - Hypothesis 关闭 deadline，避免在慢机器上误报超时；
  - 统一代码格式并通过 ruff 检查，`pool_split.py` 和 `mutation_check.py` 通过 `mypy --strict`。

**是否直接采用**：没有直接采用。第一版经复查后做了上面这些修改，每个结论都对照下面的检查结果确认后才保留。

**如何确认其正确**

1. 反例：在原始代码上实际运行，返回值和求和与第 1 项的表格一致。
2. 测试确实能发现问题：同一套测试在原始代码上有 22 个失败，修改后全部通过（第 3 项的两次输出）。
3. 测试不会被"看起来对"的错误修法蒙混过去（变异测试）：`python mutation_check.py` 在修改后的代码上每次只改错一处，生成 7 个错误版本，分别跑整套测试，7 个都被判为失败：

   ```text
   拦下  前面的人各自 round，差额由最后一人兜底：7 failed, 19 passed in 1.09s
   拦下  向下取整，差额全给权重最大的人：5 failed, 21 passed in 0.86s
   拦下  按 float 算出的小数部分排序：3 failed, 23 passed in 0.80s
   拦下  小数部分相同时，补给排在后面的人：5 failed, 21 passed in 0.70s
   拦下  排序方向写反：补给余数最小的人：6 failed, 20 passed in 0.59s
   拦下  差一错误：补钱的人数算成 leftover - 1：17 failed, 9 passed in 0.79s
   拦下  发现负权重但不报错：1 failed, 25 passed in 2.86s

   7/7 个错误版本被测试拦下
   ```

4. 分配依据：`test_split_is_closest_to_exact_shares` 对 1,976 组小输入暴力枚举所有和等于奖池的分法，修改后的结果与精确份额的总偏差、最大偏差都是所有分法中最小的。
5. 读代码确认不变量：全程没有 float；`leftover = 余数之和 / total`，而每个余数都小于 `total`，所以 `leftover` 小于"余数不为 0 的人数"。因此每人最多补 1 分，余数为 0 的人（包括权重为 0 的人）不会被补。
6. 从干净的 git 克隆、新建虚拟环境，按上面的步骤重跑，两次运行的结果与本文一致。

## 可选问题

### 测试覆盖了多少组输入？有没有比手写若干样例更不容易漏掉问题的写法？

每次运行检查 22 组手写输入、39,576 组穷举输入（两个测试各检查一遍）、1,976 组暴力枚举输入和 2,000 组随机输入。

更不容易漏的写法是：**不写"某个输入应该得到某个输出"，而写"任何输入都必须满足的性质"**（和等于奖池、每人与精确份额相差不到 1 分、非负整数、长度一致），再让程序来生成输入。

- 小范围穷举：范围内的组合一个不漏。原代码在 39,576 组里有 13,810 组出错；如果只手写几个样例，很容易恰好挑到不出错的，比如 `split_pool(10, [1, 2, 3])` 原代码就是对的。
- 基于性质的随机测试（Hypothesis）：覆盖穷举够不到的大数值和长名单，失败时自动缩减成最小反例。在原代码上，它自己找到了 `split_pool(1, [1, 1])`。测试设置了 `derandomize=True`，每次运行检查同一批输入，结果可复现。

测试本身是否够严，可以用变异测试检验：故意把代码改错，看测试能否发现（第 4 项第 3 条）。

### 修改后，多出或缺少的那几分钱分配给了谁？依据是什么？换一个人是否可行？

修改后不会"多出"：每人先拿的整数部分加起来不会超过奖池，只会剩下几分钱（少于人数）。**这几分钱补给精确份额被舍掉的小数部分最大的那几个人，每人最多 1 分；小数部分相同的，按名单顺序。** 例如 `split_pool(10000, [1, 1, 1])` 的结果是 `[3334, 3333, 3333]`。

依据：

- 每个人拿到的都是自己的精确份额向下或向上取整，与应得的相差不到 1 分。
- 在所有"总和正好等于奖池"的整数分法中，这种分法与精确份额的总偏差和最大偏差都最小（`test_split_is_closest_to_exact_shares` 用暴力枚举验证）。直观的理由是：如果把补给小数部分为 a 的人的那 1 分，改给小数部分更小的 b（b < a），总偏差会增加 2(a − b)。
- 结果确定、可复算，便于对账；同一批输入重跑（比如任务重试）结果完全一样。

换一个人是否可行：只看硬规则是可行的，这几分钱只要全部发出去，总和就对。但换人有代价：

- 补给小数部分更小的人：总和仍然正确，但离精确份额更远。
- 全部补给某一个人（比如"最后一个人兜底差额"）：这个人最多可能多拿 n − 1 分。如果前面的人用的是 `round`，兜底的人甚至可能被算成负数。例如奖池 5 分、8 人权重相同，前 7 人各得 `round(0.625) = 1` 分，最后一人得 5 − 7 = −2 分。
- 留给平台：违反硬规则。

"小数部分相同按名单顺序"也有副作用：如果名单顺序长期固定（例如按 user_id 排序），排在前面的人每次平局都占优。线上可以改成按"日期 + 用户 ID"的哈希排序，长期看更公平，也仍然可复算。本题的函数拿不到日期和用户 ID，所以保留按顺序；调用方需要保证传入的名单顺序稳定。

另外，最大余数法有一个已知的副作用（Alabama 悖论）：`weights = [1, 3, 3]` 时，奖池 3 分分成 `[1, 1, 1]`，奖池 4 分却分成 `[0, 2, 2]`，第一个人在奖池变大时反而少了 1 分。每天的奖池金额是确定的，不会拿同一批人比较不同大小的奖池，所以这里可以接受。

### 这段代码是否还有其他会出错的输入？

有。除了第 1 项的舍入问题，原代码还有这些：

| 输入 | 原代码结果 | 问题 | 修改后 |
|---|---|---|---|
| `split_pool(100, [])` | `[]` | 名单为空，100 分静默"消失" | `ValueError` |
| `split_pool(100, [0, 0])` | `ZeroDivisionError` | 权重全为 0 时崩溃，奖池为 0 时也一样 | `ValueError`；奖池为 0 时返回 `[0, 0]` |
| `split_pool(100, [2, -1])` | `[200, -100]` | 和是对的，但一个人拿了超过整个奖池的钱，另一个人被倒扣 | `ValueError` |
| `split_pool(-100, [1, 2])` | `[-33, -67]` | 负奖池没有被拒绝 | `ValueError` |
| `split_pool(100, iter([1, 3]))` | `[]` | `sum()` 先把迭代器耗尽，后面的列表推导什么也拿不到 | `[25, 75]` |
| `split_pool(100, [1.5, 2])` | `[43, 57]` | 非整数权重被静默接受，与"权重是整数"的约定不符 | `TypeError` |
| `split_pool(2**53 + 1, [1])` | `[9007199254740992]` | 只有一个人也少 1 分：`pool_cents * w / total` 是 float，超过 2^53 就丢精度 | `[9007199254740993]` |
| `split_pool(10**400, [1])` | `OverflowError` | 超出 float 的表示范围 | `[10**400]` |

最后两个问题只在数额极大时出现：奖池金额 × 权重小于 2^52（约 4.5×10^15）时，float 算出的结果与精确计算一致。按常见的数额（例如奖池 100 万元即 10^8 分、单人权重不超过一天的 86,400 秒），乘积约 8.6×10^12，碰不到这个上限。但改成整数运算以后，就不用再去论证"数会不会太大"了。

关于"没有人可分"：规则要求分完的总和等于奖池，名单为空时任何返回值都做不到，所以抛 `ValueError`，由调用方决定顺延到第二天还是退回，而不是返回一个看起来正常的空列表。
