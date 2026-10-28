# Data Governance

## 客户数据与外部传输

客户数据只能用于已批准的业务目的，并且仅限有权限的角色使用。
禁止未经数据负责人书面批准，把客户数据导出、外发、发送到外部邮箱或提交给第三方。
Agent 不能直接执行这类敏感操作，只能提示审批要求。
如果数据误发，应在 30 分钟内报告安全团队，并保留审计记录。

> Updated: 2026-10-18
> Scope: customer data, model inputs and analytical extracts

## Allowed use

Customer data may be used only for an approved business purpose and only by
authorized roles. Analytical output should contain the minimum fields needed.

## External transfer

Do not export customer data, attach it to external email, or send it to a third
party without written approval from the Data Owner. This action cannot be executed
directly by the agent.

## Incident handling

If data is sent to the wrong recipient, report the incident to Security within
30 minutes and preserve the audit trail.
