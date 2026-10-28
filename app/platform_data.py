from __future__ import annotations

from typing import Any

from .demo_data import DemoDataset
from .knowledge import list_files


FEATURE_ROWS = [
    {
        "code": "android_lr_credit_bscore_v1",
        "name": "LR 信审分",
        "domain": "model_score",
        "source": "credit_behavior_snapshot",
        "owner": "model-risk",
        "status": "online",
        "type": "float",
        "missing": 0.4,
        "iv": 0.421,
        "ks": 0.312,
        "psi": 0.041,
        "freshness": "T+1",
        "used_by": ["lr_credit_v1", "ensemble_reloan_v1"],
    },
    {
        "code": "android_xgb_credit_bscore_v2",
        "name": "XGB 信审分",
        "domain": "model_score",
        "source": "credit_behavior_snapshot",
        "owner": "model-risk",
        "status": "online",
        "type": "float",
        "missing": 0.8,
        "iv": 0.538,
        "ks": 0.361,
        "psi": 0.063,
        "freshness": "T+1",
        "used_by": ["xgb_reloan_v2", "xgb_reloan_v1"],
    },
    {
        "code": "plt_act_apply_cnt_1d",
        "name": "1 日申请次数",
        "domain": "behavior",
        "source": "customer_event_30d",
        "owner": "strategy",
        "status": "online",
        "type": "integer",
        "missing": 0.0,
        "iv": 0.192,
        "ks": 0.184,
        "psi": 0.027,
        "freshness": "hourly",
        "used_by": ["strategy_1019"],
    },
    {
        "code": "plt_act_apply_cnt_3d",
        "name": "3 日申请次数",
        "domain": "behavior",
        "source": "customer_event_30d",
        "owner": "strategy",
        "status": "online",
        "type": "integer",
        "missing": 0.0,
        "iv": 0.241,
        "ks": 0.223,
        "psi": 0.038,
        "freshness": "hourly",
        "used_by": ["strategy_1019"],
    },
    {
        "code": "sms_loan_cnt_3d",
        "name": "3 日贷款短信数",
        "domain": "alternative",
        "source": "sms_feature_daily",
        "owner": "data-science",
        "status": "online",
        "type": "integer",
        "missing": 2.1,
        "iv": 0.286,
        "ks": 0.247,
        "psi": 0.091,
        "freshness": "T+1",
        "used_by": ["strategy_1019"],
    },
    {
        "code": "plt_unsett_amt_rt",
        "name": "未结清金额比例",
        "domain": "credit_behavior",
        "source": "loan_repayment_snapshot",
        "owner": "strategy",
        "status": "online",
        "type": "float",
        "missing": 0.0,
        "iv": 0.316,
        "ks": 0.265,
        "psi": 0.052,
        "freshness": "T+1",
        "used_by": ["strategy_1019"],
    },
    {
        "code": "sys_sett_cnt",
        "name": "历史结清次数",
        "domain": "credit_history",
        "source": "loan_repayment_history",
        "owner": "data-platform",
        "status": "online",
        "type": "integer",
        "missing": 0.0,
        "iv": 0.352,
        "ks": 0.281,
        "psi": 0.019,
        "freshness": "T+1",
        "used_by": ["strategy_1019", "model_xgb_v2"],
    },
    {
        "code": "sys_od_sett_cnt_30d",
        "name": "30 日逾期结清次数",
        "domain": "credit_history",
        "source": "loan_repayment_history",
        "owner": "data-platform",
        "status": "online",
        "type": "integer",
        "missing": 0.0,
        "iv": 0.402,
        "ks": 0.335,
        "psi": 0.024,
        "freshness": "T+1",
        "used_by": ["strategy_1019"],
    },
    {
        "code": "sys_lst6_pre_max",
        "name": "上笔最多提前天数",
        "domain": "repayment",
        "source": "loan_repayment_history",
        "owner": "strategy",
        "status": "online",
        "type": "integer",
        "missing": 0.3,
        "iv": 0.167,
        "ks": 0.142,
        "psi": 0.033,
        "freshness": "T+1",
        "used_by": ["strategy_freeze"],
    },
    {
        "code": "device_risk_score_v3",
        "name": "设备风险分 v3",
        "domain": "device",
        "source": "device_graph_daily",
        "owner": "fraud",
        "status": "candidate",
        "type": "float",
        "missing": 6.8,
        "iv": 0.334,
        "ks": 0.291,
        "psi": 0.118,
        "freshness": "hourly",
        "used_by": [],
    },
    {
        "code": "geo_cluster_risk_30d",
        "name": "地区集群风险",
        "domain": "geo",
        "source": "geo_province_daily",
        "owner": "fraud",
        "status": "candidate",
        "type": "float",
        "missing": 11.2,
        "iv": 0.178,
        "ks": 0.156,
        "psi": 0.204,
        "freshness": "daily",
        "used_by": [],
    },
    {
        "code": "repay_velocity_7d",
        "name": "7 日还款速度",
        "domain": "repayment",
        "source": "repayment_event_90d",
        "owner": "data-science",
        "status": "candidate",
        "type": "float",
        "missing": 3.4,
        "iv": 0.265,
        "ks": 0.231,
        "psi": 0.076,
        "freshness": "T+1",
        "used_by": [],
    },
]


STRATEGIES = [
    {
        "id": "stg_1019",
        "name": "老客额度策略 1019",
        "version": "v1019.3",
        "status": "online",
        "group": "EG",
        "owner": "额度策略",
        "rules": 7,
        "hit_rate": 12.8,
        "updated_at": "2026-10-28T09:30:00+07:00",
    },
    {
        "id": "stg_freeze",
        "name": "提前还款不涨额",
        "version": "v0831.2",
        "status": "online",
        "group": "EG",
        "owner": "额度策略",
        "rules": 1,
        "hit_rate": 5.2,
        "updated_at": "2026-10-21T11:20:00+07:00",
    },
    {
        "id": "stg_challenger",
        "name": "D 档短信阈值 challenger",
        "version": "draft-04",
        "status": "draft",
        "group": "EG",
        "owner": "策略实验",
        "rules": 2,
        "hit_rate": 0,
        "updated_at": "2026-10-27T16:10:00+07:00",
    },
]


def build_features(dataset: DemoDataset) -> dict[str, Any]:
    rows = [dict(row) for row in FEATURE_ROWS]
    online = [row for row in rows if row["status"] == "online"]
    candidate = [row for row in rows if row["status"] == "candidate"]
    high_psi = [row for row in rows if row["psi"] >= 0.1]
    return {
        "summary": {
            "total": len(rows),
            "online": len(online),
            "candidate": len(candidate),
            "high_psi": len(high_psi),
            "avg_missing": round(sum(row["missing"] for row in rows) / len(rows), 2),
        },
        "rows": rows,
        "candidates": candidate,
        "quality_alerts": [
            {
                "code": row["code"],
                "reason": f"PSI {row['psi']:.3f} 超过 0.10 稳定性警戒线",
                "owner": row["owner"],
            }
            for row in high_psi
        ],
        "dev_jobs": [
            {
                "id": "fd_job_101",
                "name": "repay_velocity_7d",
                "status": "completed",
                "owner": "data-science",
                "train_iv": 0.265,
                "oot_ks": 0.231,
                "created_at": dataset.as_of.isoformat(),
            },
            {
                "id": "fd_job_102",
                "name": "device_cluster_v4",
                "status": "running",
                "owner": "fraud",
                "progress": 62,
                "created_at": dataset.as_of.isoformat(),
            },
        ],
    }


def build_lineage() -> dict[str, Any]:
    nodes = [
        {"id": "src_credit", "label": "credit_behavior_snapshot", "kind": "source", "layer": 0},
        {"id": "src_event", "label": "customer_event_30d", "kind": "source", "layer": 0},
        {"id": "src_repay", "label": "loan_repayment_history", "kind": "source", "layer": 0},
        {"id": "feat_apply3", "label": "plt_act_apply_cnt_3d", "kind": "feature", "layer": 1},
        {"id": "feat_settle", "label": "sys_sett_cnt", "kind": "feature", "layer": 1},
        {"id": "feat_xgb", "label": "xgb_credit_bscore_v2", "kind": "feature", "layer": 1},
        {"id": "metric_fo", "label": "first_overdue_dpd1", "kind": "metric", "layer": 2},
        {"id": "metric_tier", "label": "tier_mix", "kind": "metric", "layer": 2},
        {"id": "model_xgb", "label": "xgb_reloan_v2", "kind": "model", "layer": 3},
        {"id": "strategy_1019", "label": "stg_1019", "kind": "strategy", "layer": 3},
        {"id": "decision", "label": "credit_decision", "kind": "output", "layer": 4},
    ]
    edges = [
        {"from": "src_credit", "to": "feat_xgb", "rule": "daily batch + score transform"},
        {"from": "src_event", "to": "feat_apply3", "rule": "30d event count"},
        {"from": "src_repay", "to": "feat_settle", "rule": "settled contract count"},
        {"from": "feat_settle", "to": "metric_fo", "rule": "cohort join"},
        {"from": "feat_apply3", "to": "metric_tier", "rule": "tier attribution"},
        {"from": "feat_xgb", "to": "model_xgb", "rule": "model input"},
        {"from": "feat_apply3", "to": "strategy_1019", "rule": "downgrade rule"},
        {"from": "feat_settle", "to": "strategy_1019", "rule": "segment rule"},
        {"from": "model_xgb", "to": "decision", "rule": "model score"},
        {"from": "strategy_1019", "to": "decision", "rule": "quota policy"},
        {"from": "metric_fo", "to": "decision", "rule": "monitoring feedback"},
        {"from": "metric_tier", "to": "decision", "rule": "monitoring feedback"},
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {"nodes": len(nodes), "edges": len(edges), "sources": 3, "features": 3},
        "unavailable": [
            {"item": "跨库字段级血缘", "why": "Demo uses curated lineage edges; production needs a metadata service."},
        ],
    }


def build_cases(dataset: DemoDataset) -> dict[str, Any]:
    rows = []
    for index, disposition in enumerate(dataset.dispositions):
        rows.append(
            {
                **disposition,
                "case_id": f"CASE-{index + 1:04d}",
                "title": "首期逾期后触发额度复核" if index % 2 == 0 else "同日多产品重复申请",
                "sla_hours": 24,
                "evidence_count": 3 + index % 4,
                "assignee": "risk-ops" if index % 2 else "fraud-ops",
            }
        )
    return {
        "summary": {
            "total": len(rows),
            "open": sum(1 for row in rows if row["status"] == "open"),
            "high": sum(1 for row in rows if row["level"] == "high"),
            "false_positive": sum(1 for row in rows if row["status"] == "false_positive"),
        },
        "rows": rows,
    }


def build_strategy() -> dict[str, Any]:
    return {
        "strategies": STRATEGIES,
        "rules": [
            {"id": "A_unsettled", "base": "A", "condition": "未结清金额比例 ≥22%", "action": "降 C", "status": "active"},
            {"id": "B_app1", "base": "B", "condition": "1 日申请 ≥2 次", "action": "降 D", "status": "active"},
            {"id": "B_sms3", "base": "B", "condition": "3 日贷款短信 ≥6 条", "action": "降 C", "status": "active"},
            {"id": "C_app3", "base": "C", "condition": "3 日申请 ≥5 次", "action": "降 D", "status": "active"},
            {"id": "D_sms3", "base": "D", "condition": "3 日贷款短信 ≥5 条", "action": "降 E", "status": "active"},
            {"id": "E_app3", "base": "E", "condition": "3 日申请 ≥8 次", "action": "降 F", "status": "active"},
        ],
    }


def build_models(dataset: DemoDataset) -> dict[str, Any]:
    rows = dataset.model_health["models"]
    return {
        **dataset.model_health,
        "summary": {
            "models": len(rows),
            "normal": sum(1 for row in rows if row["verdict"] == "正常"),
            "watch": sum(1 for row in rows if row["verdict"] in ("衰减", "接近随机")),
            "unknown": sum(1 for row in rows if row["verdict"] in ("口径未定", "样本不足")),
        },
    }


def build_audit(dataset: DemoDataset) -> dict[str, Any]:
    rows = [
        {
            "at": dataset.as_of.isoformat(),
            "actor": "strategy-owner",
            "action": "strategy.draft",
            "object": "stg_challenger",
            "result": "success",
        },
        {
            "at": dataset.as_of.isoformat(),
            "actor": "agent",
            "action": "agent.tool_call",
            "object": "rule_quality",
            "result": "success",
        },
        {
            "at": dataset.as_of.isoformat(),
            "actor": "risk-ops",
            "action": "case.disposition",
            "object": "CASE-0003",
            "result": "pending",
        },
    ]
    return {
        "rows": rows,
        "summary": {
            "events": len(rows),
            "actors": len({row["actor"] for row in rows}),
            "pending": sum(1 for row in rows if row["result"] == "pending"),
        },
    }


def build_workspace_snapshot(dataset: DemoDataset) -> dict[str, Any]:
    from .kpi import build_kpi

    return {
        "generated_at": dataset.as_of.isoformat(),
        "overview": build_kpi(dataset),
        "strategy": build_strategy(),
        "models": build_models(dataset),
        "features": build_features(dataset),
        "lineage": build_lineage(),
        "cases": build_cases(dataset),
        "audit": build_audit(dataset),
        "knowledge": {"documents": len(list_files())},
    }
