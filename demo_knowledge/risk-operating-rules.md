# Risk Operating Rules

## 风控操作规则

风险结论必须说明来源文件、计算窗口和指标定义，缺少证据时要明确写出不确定性。
冻结额度、降额、加黑和停止放款属于人工负责的高风险动作，Agent 只能建议，不能执行。
模型 AUC 低于 0.55 视为接近随机，需要复核；展示 AUC 时必须同时展示样本量和分数方向。

> Updated: 2026-10-28
> Scope: risk strategy and operations

## Decision evidence

Risk conclusions must reference source file, calculation window and metric
definition. Missing evidence must be shown as an uncertainty.

## High-risk actions

Freeze limit, reduce limit, blacklist and stop disbursement are human-owned actions.
An agent may recommend them but may not execute them.

## Model review

Models with AUC below 0.55 are treated as close to random and require review.
Sample size and score direction must be shown with AUC.
