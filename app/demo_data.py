from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from random import Random
from statistics import mean
from typing import Any
BANGKOK = timezone(timedelta(hours=7), name="Asia/Bangkok")
RULES = {
    "B_app1_cnt": {"base": "B", "label": "B 档 · 1 日申请 ≥2 次", "risk_lift": 1.32},
    "B_sms3_cnt": {"base": "B", "label": "B 档 · 3 日贷款短信 ≥6 条", "risk_lift": 0.82},
    "C_app3_cnt": {"base": "C", "label": "C 档 · 3 日申请 ≥5 次", "risk_lift": 1.38},
    "C_unsettled": {"base": "C", "label": "C 档 · 未结清比例 ≥22%", "risk_lift": 1.16},
    "D_sms3_cnt": {"base": "D", "label": "D 档 · 3 日贷款短信 ≥5 条", "risk_lift": 1.08},
    "E_app3_cnt": {"base": "E", "label": "E 档 · 3 日申请 ≥8 次", "risk_lift": 0.76},
}


def as_of_from_text(value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value)
        return parsed.replace(tzinfo=BANGKOK) if parsed.tzinfo is None else parsed.astimezone(BANGKOK)
    return datetime.now(BANGKOK)


def _monday(value: datetime) -> datetime:
    day = value.replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass
class DemoDataset:
    as_of: datetime
    loans: list[dict[str, Any]]
    dispositions: list[dict[str, Any]]
    model_health: dict[str, Any]

    @property
    def decisions(self) -> list[dict[str, Any]]:
        return [loan for loan in self.loans if loan["decision_id"]]


def build_dataset(as_of: datetime | None = None, seed: int = 20261028) -> DemoDataset:
    now = (as_of or as_of_from_text(None)).astimezone(BANGKOK)
    rng = Random(seed)
    current_monday = _monday(now)
    loans: list[dict[str, Any]] = []

    tiers = ["A", "B", "B", "C", "C", "C", "D", "D", "E", "F"]
    for weeks_ago in range(12, 0, -1):
        week_start = current_monday - timedelta(days=weeks_ago * 7)
        n_loans = rng.randint(230, 300)
        trend = 1 + (12 - weeks_ago) * 0.012
        for index in range(n_loans):
            group = "EG" if rng.random() < 0.48 else "CG"
            base_tier = rng.choice(tiers)
            rule_ids: list[str] = []
            if group == "EG":
                eligible = [rule_id for rule_id, rule in RULES.items() if rule["base"] == base_tier]
                for rule_id in eligible:
                    if rng.random() < 0.16:
                        rule_ids.append(rule_id)
            final_tier = base_tier
            if rule_ids:
                final_tier = chr(min(ord(base_tier) + 1, ord("F")))

            due_at = week_start + timedelta(
                days=rng.randrange(7),
                hours=rng.randrange(8, 22),
                minutes=rng.randrange(60),
            )
            decision_at = due_at - timedelta(days=rng.randint(8, 20), hours=rng.randint(0, 7))
            risk_lift = max(
                (RULES[rule_id]["risk_lift"] for rule_id in rule_ids),
                default=1.0,
            )
            tier_lift = {"A": 0.72, "B": 0.85, "C": 1.0, "D": 1.14, "E": 1.25, "F": 1.34}[final_tier]
            group_lift = 1.0 if group == "EG" else 0.97
            first_overdue_probability = min(0.82, 0.31 * trend * risk_lift * tier_lift * group_lift)
            first_overdue = rng.random() < first_overdue_probability

            settle_days: int | None = None
            if first_overdue:
                settle_days = rng.choice([None, None, None, 2, 3, 5, 9, 12])
            else:
                settle_days = rng.choice([-1, 0, 0, 0, 1])
            settled_at = None if settle_days is None else due_at + timedelta(days=settle_days)
            bad7 = settled_at is None or settled_at > due_at + timedelta(days=7)
            extended = not bad7 and rng.random() < 0.06
            soft7 = bad7 or extended
            amount = 1500 + rng.randrange(14) * 500

            loans.append(
                {
                    "loan_id": f"L{week_start:%Y%m%d}-{index:03d}",
                    "decision_id": f"D{decision_at:%Y%m%d%H%M}-{index:03d}",
                    "user_id": f"U{100000 + rng.randrange(900000)}",
                    "group": group,
                    "base_tier": base_tier,
                    "final_tier": final_tier,
                    "rule_ids": rule_ids,
                    "downgraded": final_tier != base_tier,
                    "decision_at": _iso(decision_at),
                    "approved": rng.random() < 0.965,
                    "amount": amount,
                    "principal": amount,
                    "due_at": _iso(due_at),
                    "settled_at": _iso(settled_at),
                    "first_overdue": first_overdue,
                    "bad7": bad7,
                    "soft7": soft7,
                    "extended": extended,
                    "paid_amount": amount if settled_at and not bad7 else 0,
                }
            )

    top_users = [loan["user_id"] for loan in loans if loan["first_overdue"]][-8:]
    dispositions = [
        {
            "id": f"DP{index + 1:04d}",
            "user_id": user_id,
            "level": "high" if index >= 6 else "medium",
            "action": "manual_review",
            "status": "false_positive" if index == 5 else "open",
            "created_at": _iso(now - timedelta(days=index + 1)),
        }
        for index, user_id in enumerate(top_users)
    ]

    model_rows = [
        ("xgb_reloan_v2", "支用直连", 4089, 0.557),
        ("xgb_reloan_v1", "支用直连", 1550, 0.537),
        ("xgb_newloan_v2", "进件→放款", 9639, 0.508),
        ("lr_credit_v1", "进件→放款", 10599, 0.494),
        ("ascore_v1", "进件→放款", 6284, 0.518),
        ("ios_reloan_v1", "支用直连", 340, 0.623),
        ("ensemble_reloan_v1", "支用直连", 812, None),
        ("ascore_v2", "进件→放款", 1879, 0.561),
    ]
    models = []
    for name, path, n, auc in model_rows:
        if auc is None:
            verdict = "口径未定"
        elif n < 500:
            verdict = "样本不足"
        elif auc >= 0.60:
            verdict = "正常"
        elif auc >= 0.55:
            verdict = "衰减"
        else:
            verdict = "接近随机"
        models.append({"name": name, "path": path, "n": n, "auc": auc, "verdict": verdict})

    model_health = {
        "window": "近 90 天放款，首期到期 ≥7 天",
        "generated_at": _iso(now),
        "sample_size": {"loans": sum(model["n"] for model in models), "decisions": len(loans)},
        "baseline_bad_rate": round(mean(1 if loan["soft7"] else 0 for loan in loans) * 100, 1),
        "freshness": {"status": "fresh", "age_minutes": 12},
        "models": models,
        "thresholds": "AUC ≥0.60 正常；0.55–0.60 衰减；<0.55 接近随机；样本 <500 或方向未标定不出结论。",
    }
    return DemoDataset(as_of=now, loans=loans, dispositions=dispositions, model_health=model_health)


def query_demo(due_from: str | None = None, due_to: str | None = None) -> dict[str, Any]:
    from .config import get_settings

    dataset = build_dataset(as_of_from_text(get_settings().as_of or None))
    start = datetime.fromisoformat(due_from).replace(tzinfo=BANGKOK) if due_from else None
    end = datetime.fromisoformat(due_to).replace(tzinfo=BANGKOK) if due_to else None
    if start or end:
        loans = [
            loan
            for loan in dataset.loans
            if (start is None or datetime.fromisoformat(loan["due_at"]) >= start)
            and (end is None or datetime.fromisoformat(loan["due_at"]) <= end.replace(hour=23, minute=59, second=59))
        ]
        dataset = DemoDataset(dataset.as_of, loans, dataset.dispositions, dataset.model_health)
    return {"dataset": dataset, "due_from": due_from, "due_to": due_to}
