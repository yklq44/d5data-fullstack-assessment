"""检验测试本身：把 split_pool 改成几种"看起来对、其实错"的写法，测试必须全部判为失败。

每个错误版本都是在 pool_split.py 上只改一处得到的。运行：python mutation_check.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (错误写法, pool_split.py 中被替换的代码, 替换成的代码)
MUTANTS = [
    (
        "前面的人各自 round，差额由最后一人兜底",
        "    shares = [divmod(pool_cents * w, total) for w in weights]\n",
        "    amounts = [round(pool_cents * w / total) for w in weights[:-1]]\n"
        "    return amounts + [pool_cents - sum(amounts)]\n",
    ),
    (
        "向下取整，差额全给权重最大的人",
        "    for i in by_remainder[:leftover]:\n        amounts[i] += 1\n",
        "    amounts[weights.index(max(weights))] += leftover\n",
    ),
    (
        "按 float 算出的小数部分排序",
        "key=lambda i: shares[i][1]",
        "key=lambda i: pool_cents * weights[i] / total % 1",
    ),
    (
        "小数部分相同时，补给排在后面的人",
        "key=lambda i: shares[i][1]",
        "key=lambda i: (shares[i][1], i)",
    ),
    (
        "排序方向写反：补给余数最小的人",
        "reverse=True",
        "reverse=False",
    ),
    (
        "差一错误：补钱的人数算成 leftover - 1",
        "by_remainder[:leftover]",
        "by_remainder[: leftover - 1]",
    ),
    (
        "发现负权重但不报错",
        '            raise ValueError(f"weights[{i}] = {w}，权重不能为负数")\n',
        "            pass\n",
    ),
]


def run_tests(pool_split_source: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "pool_split.py").write_text(pool_split_source, encoding="utf-8")
        shutil.copy(HERE / "test_pool_split.py", tmp)
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
            cwd=tmp,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )


def main() -> int:
    source = (HERE / "pool_split.py").read_text(encoding="utf-8")
    survived = 0
    for name, old, new in MUTANTS:
        if source.count(old) != 1:
            sys.exit(f"pool_split.py 中找不到唯一的待替换代码：{old!r}")
        result = run_tests(source.replace(old, new))
        summary = (result.stdout.strip().splitlines() or ["（pytest 没有输出）"])[-1]
        # pytest 退出码 1 表示有测试失败；其他非 0 值说明错误版本本身没能跑起来
        caught = result.returncode == 1
        survived += not caught
        print(f"{'拦下' if caught else '漏过'}  {name}：{summary}")
    print(f"\n{len(MUTANTS) - survived}/{len(MUTANTS)} 个错误版本被测试拦下")
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main())
