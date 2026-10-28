from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from .demo_data import BANGKOK, RULES, DemoDataset
from .stats import two_proportion_z


DAY = timedelta(days=1)
MIN_N = 10


def _rate(bad: int, n: int) -> float | None:
    return round(bad / n * 100, 1) if n else None


def _week_start(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=value.weekday())


def _loan_due(loan: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(loan["due_at"])


def _due1_eligible(loan: dict[str, Any], now: datetime) -> bool:
    return now >= _loan_due(loan) + DAY


def _due7_eligible(loan: dict[str, Any], now: datetime) -> bool:
    return now >= _loan_due(loan) + 7 * DAY


def weekly_series(dataset: DemoDataset) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"week": "", "n": 0, "fo_bad": 0, "bad7": 0, "soft7": 0, "matured7": 0}
    )
    for loan in dataset.loans:
        due = _loan_due(loan)
        key = _week_start(due).date().isoformat()
        row = buckets[key]
        row["week"] = key
        row["n"] += 1
        row["fo_bad"] += int(loan["first_overdue"])
        if _due7_eligible(loan, dataset.as_of):
            row["matured7"] += 1
            row["bad7"] += int(loan["bad7"])
            row["soft7"] += int(loan["soft7"])
    series = []
    for key in sorted(buckets):
        row = buckets[key]
        start = datetime.fromisoformat(key).replace(tzinfo=BANGKOK)
        comparable = dataset.as_of > start + 8 * DAY
        series.append(
            {
                "week": key,
                "n": row["n"],
                "first_overdue_rate": _rate(row["fo_bad"], row["n"]) if comparable else None,
                "first_overdue_num": row["fo_bad"],
                "comparable": comparable,
                "dpd7_rate": _rate(row["bad7"], row["matured7"]),
                "dpd7_num": row["bad7"],
                "matured7": row["matured7"],
                "soft7_rate": _rate(row["soft7"], row["matured7"]),
                "soft7_num": row["soft7"],
            }
        )
    return series


def week_over_week(series: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [row for row in series if row["comparable"]]
    if len(complete) < 2:
        return {
            "available": False,
            "reason": "数据源未就绪：需要至少两个完整到期周。",
            "latest": None,
            "previous": None,
        }
    latest, previous = complete[-1], complete[-2]
    diff = round(latest["first_overdue_rate"] - previous["first_overdue_rate"], 1)
    return {
        "available": True,
        "latest": latest,
        "previous": previous,
        "diff_pp": diff,
        "direction": "恶化" if diff > 0.5 else "改善" if diff < -0.5 else "持平",
        "observing_week": next((row for row in reversed(series) if not row["comparable"]), None),
    }


def group_summary(dataset: DemoDataset) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for group in ("EG", "CG"):
        rows = [loan for loan in dataset.loans if loan["group"] == group]
        due1 = [loan for loan in rows if _due1_eligible(loan, dataset.as_of)]
        bad1 = sum(1 for loan in due1 if loan["first_overdue"])
        matured = [loan for loan in due1 if _due7_eligible(loan, dataset.as_of)]
        bad7 = sum(1 for loan in matured if loan["bad7"])
        result[group] = {
            "decisions": len(rows),
            "approved": sum(1 for loan in rows if loan["approved"]),
            "approval_rate": _rate(sum(1 for loan in rows if loan["approved"]), len(rows)),
            "loans": len(rows),
            "ticket_avg": round(mean(loan["amount"] for loan in rows)) if rows else None,
            "due1": len(due1),
            "first_overdue_num": bad1,
            "first_overdue_rate": _rate(bad1, len(due1)),
            "matured7": len(matured),
            "bad7_num": bad7,
            "dpd7_rate": _rate(bad7, len(matured)),
        }
    return result


def tier_table(dataset: DemoDataset, groups: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    table = []
    cells = []
    for tier in "ABCDEF":
        row: dict[str, Any] = {"tier": tier}
        for group in ("EG", "CG"):
            rows = [loan for loan in dataset.loans if loan["group"] == group and loan["final_tier"] == tier]
            due1 = [loan for loan in rows if _due1_eligible(loan, dataset.as_of)]
            fo_num = sum(1 for loan in due1 if loan["first_overdue"])
            due7 = [loan for loan in due1 if _due7_eligible(loan, dataset.as_of)]
            bad7 = sum(1 for loan in due7 if loan["bad7"])
            row[f"{group.lower()}_decisions"] = len(rows)
            row[f"{group.lower()}_due1"] = len(due1)
            row[f"{group.lower()}_fo_num"] = fo_num
            row[f"{group.lower()}_fo_rate"] = _rate(fo_num, len(due1))
            row[f"{group.lower()}_due7"] = len(due7)
            row[f"{group.lower()}_bad7_num"] = bad7
            row[f"{group.lower()}_dpd7_rate"] = _rate(bad7, len(due7))
        z = two_proportion_z(
            row["eg_fo_num"],
            row["eg_due1"],
            row["cg_fo_num"],
            row["cg_due1"],
        )
        testable = row["eg_due1"] >= MIN_N and row["cg_due1"] >= MIN_N
        row["testable"] = testable
        row["p_value"] = z["p"] if z else None
        row["significant"] = bool(testable and z and z["p"] < 0.05)
        cells.append({"tier": tier, "testable": testable, "p_value": row["p_value"]})
        table.append(row)

    due1 = [loan for loan in dataset.loans if _due1_eligible(loan, dataset.as_of)]
    eg_rows = [loan for loan in due1 if loan["group"] == "EG"]
    cg_rows = [loan for loan in due1 if loan["group"] == "CG"]
    pooled = two_proportion_z(
        sum(1 for loan in eg_rows if loan["first_overdue"]),
        len(eg_rows),
        sum(1 for loan in cg_rows if loan["first_overdue"]),
        len(cg_rows),
    )
    power = {
        "min_n": MIN_N,
        "testable": sum(1 for cell in cells if cell["testable"]),
        "significant": sum(1 for row in table if row["significant"]),
        "cells": cells,
        "pooled": {
            "eg_num": sum(1 for loan in eg_rows if loan["first_overdue"]),
            "eg_n": len(eg_rows),
            "cg_num": sum(1 for loan in cg_rows if loan["first_overdue"]),
            "cg_n": len(cg_rows),
            **(pooled or {}),
        },
    }
    return table, power


def rule_quality(dataset: DemoDataset) -> list[dict[str, Any]]:
    eg = [loan for loan in dataset.loans if loan["group"] == "EG" and _due1_eligible(loan, dataset.as_of)]
    result = []
    for rule_id, rule in RULES.items():
        fired = [loan for loan in eg if rule_id in loan["rule_ids"]]
        control = [
            loan
            for loan in eg
            if loan["base_tier"] == rule["base"] and not loan["downgraded"] and rule_id not in loan["rule_ids"]
        ]
        fired_bad = sum(1 for loan in fired if loan["first_overdue"])
        control_bad = sum(1 for loan in control if loan["first_overdue"])
        fired_rate = _rate(fired_bad, len(fired))
        control_rate = _rate(control_bad, len(control))
        testable = len(fired) >= MIN_N and len(control) >= MIN_N
        delta = (
            round(fired_rate - control_rate, 1)
            if fired_rate is not None and control_rate is not None
            else None
        )
        ratio = (
            round(fired_rate / control_rate, 2)
            if fired_rate is not None and control_rate not in (None, 0)
            else None
        )
        if not testable:
            verdict = "待观察"
            reason = f"命中 {len(fired)} / 对照 {len(control)}，两组各 ≥{MIN_N} 才判定"
        elif fired_rate is not None and control_rate == 0:
            verdict = "精准"
            reason = f"命中组 {fired_rate}% / 对照组 0%，绝对差 {delta}pp"
        elif delta is not None and delta >= 2 and ratio is not None and ratio >= 1.3:
            verdict = "精准"
            reason = f"首逾高 {delta}pp，命中组为对照组的 {ratio}x"
        elif delta is not None and delta < -2:
            verdict = "待复核"
            reason = f"命中组风险反而低 {abs(delta)}pp，可能误伤"
        elif delta is not None and abs(delta) < 2:
            verdict = "陪跑"
            reason = f"与对照基本持平（{delta}pp）"
        else:
            verdict = "待观察"
            reason = "方向正确但区分度不足"
        result.append(
            {
                "rule_id": rule_id,
                "label": rule["label"],
                "base_tier": rule["base"],
                "fired": {"n": len(fired), "bad": fired_bad, "rate": fired_rate},
                "control": {"n": len(control), "bad": control_bad, "rate": control_rate},
                "delta_pp": delta,
                "ratio": ratio,
                "testable": testable,
                "verdict": verdict,
                "reason": reason,
            }
        )
    return result


def disposition_summary(dataset: DemoDataset) -> dict[str, Any]:
    high = [row for row in dataset.dispositions if row["level"] == "high"]
    return {
        "total": len(dataset.dispositions),
        "high": len(high),
        "open": sum(1 for row in high if row["status"] == "open"),
        "false_positive": sum(1 for row in high if row["status"] == "false_positive"),
        "rows": dataset.dispositions,
    }


def build_kpi(dataset: DemoDataset) -> dict[str, Any]:
    series = weekly_series(dataset)
    groups = group_summary(dataset)
    table, power = tier_table(dataset, groups)
    rules = rule_quality(dataset)
    portfolio_due1 = groups["EG"]["due1"] + groups["CG"]["due1"]
    portfolio_fo = groups["EG"]["first_overdue_num"] + groups["CG"]["first_overdue_num"]
    return {
        "ok": True,
        "generated_at": dataset.as_of.isoformat(),
        "as_of": dataset.as_of.isoformat(),
        "source": "deterministic synthetic dataset",
        "summary": {
            "decisions": len(dataset.decisions),
            "approved": sum(1 for loan in dataset.decisions if loan["approved"]),
            "approval_rate": _rate(sum(1 for loan in dataset.decisions if loan["approved"]), len(dataset.decisions)),
            "loans": len(dataset.loans),
            "due1": portfolio_due1,
            "first_overdue_num": portfolio_fo,
            "first_overdue_rate": _rate(portfolio_fo, portfolio_due1),
        },
        "groups": groups,
        "weekly_series": series,
        "week_over_week": week_over_week(series),
        "tier_table": table,
        "power": power,
        "rule_quality": {
            "min_n": MIN_N,
            "testable": sum(1 for row in rules if row["testable"]),
            "rows": rules,
        },
        "model_health": dataset.model_health,
        "dispositions": disposition_summary(dataset),
        "caliber": {
            "main_metric": "首逾期 = 首期到期 +1 天时点仍未结清；dpd7 / soft7 为成熟对照。",
            "denominator": "所有率值同时返回分子和分母；样本过小时不参与统计判定。",
            "window": "展示到期日落在所选窗口内的借据；周环比只使用完整到期周。",
        },
    }
