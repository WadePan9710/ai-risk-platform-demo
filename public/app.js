const $ = (selector) => document.querySelector(selector)
const $$ = (selector) => [...document.querySelectorAll(selector)]
const num = (value, digits = 1) => value == null ? '—' : Number(value).toFixed(digits).replace(/\.0$/, '')
const pct = (value) => value == null ? '—' : `${num(value)}%`
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]))
const tone = (verdict) => {
  if (['精准', '正常', 'success', 'online'].includes(verdict)) return 'good'
  if (['待复核', '衰减', '样本不足', 'pending', 'draft'].includes(verdict)) return 'warn'
  if (['接近随机', 'error'].includes(verdict)) return 'bad'
  return ''
}

const workspace = { data: null, featureStatus: 'all' }

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options)
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || body.error || `HTTP ${response.status}`)
  return body
}

async function loadWorkspace() {
  workspace.data = await fetchJson('/api/workspace')
  $('#workspace-time').textContent = `as of ${workspace.data.generated_at.slice(0, 10)}`
  renderOverview(workspace.data.overview)
  renderStrategy(workspace.data)
  renderModels(workspace.data.models)
  renderFeatures(workspace.data.features)
  renderLineage(workspace.data.lineage)
  renderCases(workspace.data.cases)
  renderAudit(workspace.data.audit)
  $('#knowledge-count').textContent = `${workspace.data.knowledge.documents} docs`
  $('#overview-health').textContent = 'data ready'
}

function renderOverview(overview) {
  const summary = overview.summary
  $('#m-decisions').textContent = summary.decisions
  $('#m-approval').textContent = pct(summary.approval_rate)
  $('#m-approval-note').textContent = `${summary.approved} approved / ${summary.decisions}`
  $('#m-fo').textContent = pct(summary.first_overdue_rate)
  $('#m-fo-note').textContent = `${summary.first_overdue_num} overdue / ${summary.due1}`
  $('#m-rules').textContent = `${overview.rule_quality.testable}/${overview.rule_quality.rows.length}`
  $('#m-rules-note').textContent = 'rules with valid controls'
  $('#window-chip').textContent = `as of ${overview.as_of.slice(0, 10)}`
  const series = overview.weekly_series.slice(-10)
  const max = Math.max(...series.map((row) => row.first_overdue_rate ?? 0), 1)
  $('#sparkline').innerHTML = series.map((row) => {
    const height = row.first_overdue_rate == null ? 15 : Math.max(7, row.first_overdue_rate / max * 100)
    return `<div class="bar ${row.comparable ? '' : 'observing'}" style="height:${height}%" data-label="${esc(`${row.week}: ${row.first_overdue_rate ?? '观察中'}`)}"></div>`
  }).join('')
  $('#trend-start').textContent = series[0]?.week ?? '—'
  $('#trend-end').textContent = series.at(-1)?.week ?? '—'
  $('#tier-rows').innerHTML = overview.tier_table.map((row) => `
    <tr><td class="strong">${row.tier}</td><td class="num">${row.eg_due1}</td>
    <td class="num">${pct(row.eg_fo_rate)} <span style="color:var(--faint)">(${row.eg_fo_num}/${row.eg_due1})</span></td>
    <td class="num">${row.cg_due1}</td><td class="num">${pct(row.cg_fo_rate)} <span style="color:var(--faint)">(${row.cg_fo_num}/${row.cg_due1})</span></td>
    <td><span class="chip ${row.significant ? 'good' : row.testable ? 'warn' : ''}">${row.significant ? 'significant' : row.testable ? 'testable' : 'sample gate'}</span></td></tr>
  `).join('')
}

function renderStrategy(data) {
  $('#strategy-rows').innerHTML = data.strategy.strategies.map((row) => `
    <tr><td class="strong">${esc(row.name)}</td><td class="mono">${esc(row.version)}</td><td>${row.group}</td>
    <td><span class="chip ${tone(row.status)}">${esc(row.status)}</span></td><td>${row.rules}</td>
    <td class="num">${pct(row.hit_rate)}</td><td>${esc(row.owner)}</td></tr>
  `).join('')
  $('#rule-rows').innerHTML = data.overview.rule_quality.rows.map((row) => `
    <tr><td class="strong">${esc(row.label)}</td><td>${row.base_tier}</td><td class="num">${row.fired.n}</td>
    <td class="num">${pct(row.fired.rate)} (${row.fired.bad}/${row.fired.n})</td>
    <td class="num">${pct(row.control.rate)} (${row.control.bad}/${row.control.n})</td>
    <td class="num">${row.delta_pp == null ? '—' : `${row.delta_pp > 0 ? '+' : ''}${row.delta_pp}pp`}</td>
    <td><span class="chip ${tone(row.verdict)}">${esc(row.verdict)}</span></td></tr>
  `).join('')
}

function renderModels(models) {
  $('#model-summary').textContent = `${models.summary.normal} normal · ${models.summary.watch} watch · ${models.summary.unknown} unknown`
  $('#model-rows').innerHTML = models.models.map((row) => `
    <tr><td class="strong mono">${esc(row.name)}</td><td>${esc(row.path)}</td><td class="num">${row.n}</td>
    <td class="num">${row.auc ?? '—'}</td><td><span class="chip ${tone(row.verdict)}">${esc(row.verdict)}</span></td><td>${esc(row.sourceTable ?? '—')}</td></tr>
  `).join('')
}

function renderFeatures(features) {
  $('#f-total').textContent = features.summary.total
  $('#f-online').textContent = features.summary.online
  $('#f-candidate').textContent = features.summary.candidate
  $('#f-psi').textContent = features.summary.high_psi
  renderFeatureRows(features.rows)
  $('#feature-jobs').innerHTML = features.dev_jobs.map((job) => `
    <div class="job-row"><div class="job-name mono">${esc(job.name)}</div><div class="job-meta">${job.status} · ${job.owner}${job.progress ? ` · ${job.progress}%` : ''}${job.oot_ks ? ` · OOT KS ${job.oot_ks}` : ''}</div></div>
  `).join('')
}

function renderFeatureRows(rows) {
  const filtered = workspace.featureStatus === 'all' ? rows : rows.filter((row) => row.status === workspace.featureStatus)
  $('#feature-rows').innerHTML = filtered.map((row) => `
    <tr><td class="strong mono">${esc(row.code)}</td><td>${esc(row.domain)}</td><td>${esc(row.source)}</td>
    <td><span class="chip ${tone(row.status)}">${esc(row.status)}</span></td><td class="num ${row.missing > 5 ? 'warn' : ''}">${row.missing}%</td>
    <td class="num">${row.iv}</td><td class="num">${row.ks}</td><td class="num ${row.psi >= 0.1 ? 'warn' : ''}">${row.psi}</td></tr>
  `).join('')
}

function renderLineage(lineage) {
  $('#lineage-summary').textContent = `${lineage.summary.nodes} nodes · ${lineage.summary.edges} edges`
  const labels = ['Source', 'Feature', 'Metric', 'Model / Strategy', 'Decision']
  $('#lineage-canvas').innerHTML = labels.map((label, layer) => `
    <div class="lineage-column"><h4>${label}</h4>${lineage.nodes.filter((node) => node.layer === layer).map((node) => `<div class="lineage-node kind-${node.kind}">${esc(node.label)}</div>`).join('')}</div>
  `).join('')
  const byId = Object.fromEntries(lineage.nodes.map((node) => [node.id, node.label]))
  $('#lineage-rows').innerHTML = lineage.edges.map((edge) => `<tr><td class="mono">${esc(byId[edge.from])}</td><td class="mono">${esc(byId[edge.to])}</td><td>${esc(edge.rule)}</td></tr>`).join('')
}

function renderCases(cases) {
  $('#c-total').textContent = cases.summary.total
  $('#c-open').textContent = cases.summary.open
  $('#c-high').textContent = cases.summary.high
  $('#c-fp').textContent = cases.summary.false_positive
  $('#case-rows').innerHTML = cases.rows.map((row) => `
    <tr><td class="strong mono">${esc(row.case_id)}</td><td class="mono">${esc(row.user_id)}</td><td>${esc(row.title)}</td>
    <td><span class="chip ${row.level === 'high' ? 'bad' : 'warn'}">${row.level}</span></td><td>${row.sla_hours}h</td><td class="num">${row.evidence_count}</td>
    <td><span class="chip ${tone(row.status)}">${esc(row.status)}</span></td></tr>
  `).join('')
}

function renderAudit(audit) {
  $('#audit-summary').textContent = `${audit.summary.events} events · ${audit.summary.pending} pending`
  $('#audit-rows').innerHTML = audit.rows.map((row) => `
    <tr><td class="mono">${esc(String(row.at).slice(0, 19))}</td><td>${esc(row.actor)}</td><td class="mono">${esc(row.action)}</td>
    <td>${esc(row.object)}</td><td><span class="chip ${tone(row.result)}">${esc(row.result)}</span></td></tr>
  `).join('')
}

async function loadKnowledgeFiles() {
  const data = await fetchJson('/api/knowledge/files')
  $('#doc-list').innerHTML = data.files.map((file) => `<div class="doc"><div class="doc-name">${esc(file.title)}</div><div class="doc-meta mono">${esc(file.path)} · ${file.size} B</div></div>`).join('')
}

function renderKnowledge(data) {
  const restricted = data.status === 'approval_required'
  $('#knowledge-output').className = `knowledge-answer ${restricted ? 'restricted' : ''}`
  $('#knowledge-output').innerHTML = `
    <h3>${restricted ? 'Approval required' : data.status === 'no_evidence' ? 'No grounded answer' : 'Grounded answer'}</h3>
    <p>${esc(data.answer)}</p>
    ${(data.citations ?? []).map((item) => `<div class="citation"><b>${esc(item.title)}</b> <span class="mono">${esc(item.ref)}</span><div>${esc(item.snippet)}</div></div>`).join('')}
  `
}

async function askKnowledge(question) {
  if (!question.trim()) return
  $('#knowledge-output').className = 'knowledge-empty'
  $('#knowledge-output').textContent = 'Searching approved knowledge…'
  try {
    renderKnowledge(await fetchJson('/api/knowledge/query', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ question }) }))
  } catch (error) {
    $('#knowledge-output').innerHTML = `<div class="load-error">${esc(error.message)}</div>`
  }
}

function traceRows(state) {
  const rows = [['route', `Routed to ${state.route ?? 'unknown'}`, state.routing_reason]]
  for (const call of state.tool_calls ?? []) rows.push(['tool', `Called ${call.tool}`, call.call_id])
  for (const item of state.findings ?? []) rows.push(['finding', `${item.label}: ${item.value ?? '—'}`, item.unit || 'structured evidence'])
  if (state.final_action) rows.push(['action', state.final_action.type, state.final_action.executed ? 'executed' : 'not executed'])
  if (state.model) rows.push(['model', state.model, `${state.model_calls ?? 0} model calls`])
  return rows
}

function renderAgent(data) {
  const state = data.state
  const approval = data.interrupt
  $('#agent-mode').textContent = data.interrupted ? 'approval' : state.status || 'done'
  $('#agent-mode').className = `chip ${data.interrupted ? 'warn' : 'good'}`
  $('#agent-output').className = 'agent-result'
  $('#agent-output').innerHTML = `
    <div class="answer">${esc(state.answer || 'The graph completed without a narrative.')}</div>
    ${traceRows(state).map(([kind, label, detail], index) => `<div class="trace-line"><div class="trace-index">${String(index + 1).padStart(2, '0')}</div><div><div class="trace-label">${esc(label)}</div><div class="trace-detail">${esc(detail ?? '')}</div></div><span class="chip ${kind === 'action' ? 'warn' : ''}">${esc(kind)}</span></div>`).join('')}
    ${approval ? `<div class="approval"><div class="approval-title">Human approval required</div><p>${esc(approval.reason)} <span class="mono">${esc(approval.action?.type)}</span></p><div class="approval-actions"><button class="primary" id="approve-action">Approve</button><button class="secondary" id="reject-action">Reject</button></div></div>` : ''}
  `
  if (approval) {
    $('#approve-action').addEventListener('click', () => resumeAgent(data.thread_id, 'approve'))
    $('#reject-action').addEventListener('click', () => resumeAgent(data.thread_id, 'reject'))
  }
}

async function runAgent(question) {
  if (!question.trim()) return
  $('#agent-run').disabled = true
  $('#agent-mode').textContent = 'routing'
  $('#agent-mode').className = 'chip warn'
  $('#agent-output').className = 'agent-result'
  $('#agent-output').innerHTML = '<div class="answer muted">Route → evidence → findings → narrator…</div>'
  try {
    renderAgent(await fetchJson('/api/agent/runs', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ question }) }))
  } catch (error) {
    $('#agent-output').innerHTML = `<div class="load-error">${esc(error.message)}</div>`
  } finally {
    $('#agent-run').disabled = false
  }
}

async function resumeAgent(threadId, decision) {
  try {
    renderAgent(await fetchJson(`/api/agent/runs/${threadId}/resume`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ decision, note: 'demo approval' }) }))
  } catch (error) {
    $('#agent-output').innerHTML = `<div class="load-error">${esc(error.message)}</div>`
  }
}

function showView(name) {
  const valid = $$('.view').some((view) => view.id === `view-${name}`) ? name : 'overview'
  $$('.view').forEach((view) => view.classList.toggle('active', view.id === `view-${valid}`))
  $$('.nav-item').forEach((button) => button.classList.toggle('active', button.dataset.view === valid))
  history.replaceState(null, '', `#${valid}`)
}

$$('.nav-item').forEach((button) => button.addEventListener('click', () => showView(button.dataset.view)))
$$('[data-fstatus]').forEach((button) => button.addEventListener('click', () => {
  workspace.featureStatus = button.dataset.fstatus
  $$('[data-fstatus]').forEach((item) => item.classList.toggle('active', item === button))
  if (workspace.data) renderFeatureRows(workspace.data.features.rows)
}))
$$('[data-question]').forEach((button) => button.addEventListener('click', () => {
  $('#agent-question').value = button.dataset.question
  runAgent(button.dataset.question)
}))
$('#agent-form').addEventListener('submit', (event) => { event.preventDefault(); runAgent($('#agent-question').value) })
$('#knowledge-form').addEventListener('submit', (event) => { event.preventDefault(); askKnowledge($('#knowledge-question').value) })

Promise.all([loadWorkspace(), loadKnowledgeFiles()]).catch((error) => {
  $('#overview-health').textContent = error.message
  $('#overview-health').className = 'chip bad'
})
showView(location.hash.slice(1) || 'overview')

const deepLinkQuestion = new URLSearchParams(location.search).get('ask')
if (deepLinkQuestion) {
  $('#agent-question').value = deepLinkQuestion
  setTimeout(() => runAgent(deepLinkQuestion), 300)
}
