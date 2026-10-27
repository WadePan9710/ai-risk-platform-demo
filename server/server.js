// AI 风控策略驾驶舱 demo：零依赖（Node ≥18 内置模块），内存合成数据，静态托管 + JSON API。
// 生产版同款 KPI 复算逻辑：首逾期主线（T+1 可判）、soft7/dpd7 成熟对照、整周可比门控、
// EG/CG 分子分母 + 两比例 z 功效、fail-loudly 数据源校验。
import http from 'node:http'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { dataset } from './mock/generator.js'
import { dueWeekSeries, weekOverWeek, abGroupSummary, abTierTable, abPower } from './kpi/ab.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PUBLIC = path.join(__dirname, '..', 'public')
const PORT = process.env.PORT || 3000
const DAY = 86400000

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml' }

// ---------- KPI 组装 ----------
function kpi({ dueFrom, dueTo } = {}) {
  const ds = dataset()
  const now = Date.now()
  const series = dueWeekSeries(ds.loans, dueFrom, dueTo)
  const wow = weekOverWeek(series)
  const tierTable = abTierTable(ds.loans, now)
  const power = abPower(tierTable, ds.loans, now)
  const groupSummary = abGroupSummary(ds.loans, now)

  // 卡2 主线
  const card2 = {
    source: '合成放款数据（借据级，到期周分桶）',
    refresh: '实时',
    metric: '首逾期率（到期≥1天未结清，T+1 可判）主线；soft7/dpd7 为到期≥7天成熟单对照',
    latestWeek: wow.latest?.week ?? null,
    latestRate: wow.latest?.firstOverdueRate ?? null, latestN: wow.latest?.n ?? 0,
    prevWeek: wow.prev?.week ?? null, prevRate: wow.prev?.firstOverdueRate ?? null, prevN: wow.prev?.n ?? 0,
    diff: wow.diff ?? null, direction: wow.direction ?? null,
    dpd7Ref: wow.dpd7Ref, soft7Ref: wow.soft7Ref,
    observing: wow.observing,
    unavailable: wow.unavailable ?? null,
  }

  // 卡4 分档表 + 功效
  const card4 = {
    source: '合成授信/放款数据（EG/CG 分组）',
    tierTable, power: abPower(tierTable, ds.loans, now),
    tierBasis: '档名口径：EG = 降档后档名；CG = 基线档名。同档可能混含选择效应，基线口径表见下方折叠。',
    baseTierTable: buildBaseTierTable(ds),
    unavailable: null,
  }

  // 卡5 模型体检（fail-loudly 校验：缺字段显式上报）
  const mh = ds.modelHealth
  const missing = []
  for (const k of ['sampleSize', 'baselineBadRate', 'decisionFreshness', 'models', 'thresholds']) {
    if (mh[k] == null) missing.push(`体检.${k}`)
  }
  const card5 = {
    source: '合成模型体检数据（AUC 值为示例）',
    refresh: '每周',
    data: missing.length ? null : mh,
    unavailable: missing.length ? `数据源未就绪：${missing.join('；')}` : null,
  }

  return {
    ok: true,
    dueWindow: { dueFrom: dueFrom ?? '(默认近70天)', dueTo: dueTo ?? '今天' },
    generatedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
    card1: buildCard1(ds),
    card2,
    card3: { source: card2.source, refresh: card2.refresh, series },
    card4, card5,
    card6: buildCard6(ds),
  }
}

function buildCard1(ds) {
  const now = Date.now()
  const yesterday = now - DAY
  const loans = ds.loans.filter((l) => l.dueTs >= yesterday && l.dueTs < now)
  const decisions = ds.decisions.filter((d) => d.applyTs >= yesterday && d.applyTs < now)
  const approved = decisions.filter((d) => d.approved).length
  return {
    source: '合成放款/授信数据（按申请/放款时间筛选）',
    refresh: '每次打开实时查询',
    loans: loans.length,
    disbAmt: loans.reduce((s, l) => s + l.amount, 0),
    decisions: decisions.length,
    approved,
    approvalRate: decisions.length ? +((approved / decisions.length) * 100).toFixed(1) : null,
  }
}

function buildCard6(ds) {
  const red = ds.dispositions.filter((d) => d.level === '🔴')
  const pending = red.filter((d) => d.result !== '误报')
  return {
    source: '合成处置工单（demo 数据）',
    refresh: '实时',
    redTotal: red.length, pending: pending.length,
    disposed: red.length - pending.length, falsePositive: red.filter((d) => d.result === '误报').length,
  }
}

function buildBaseTierTable(ds) {
  const tiers = ['A', 'B', 'C', 'D', 'E', 'F']
  return tiers.map((tier) => {
    const row = { tier }
    for (const key of ['EG', 'CG']) {
      const groupLoans = ds.loans.filter((l) => l.group === key && l.baseTier === tier)
      const due1 = groupLoans.filter((l) => Date.now() - l.dueTs >= DAY)
      const foNum = due1.filter((l) => l.firstOverdue).length
      const due7 = due1.filter((l) => Date.now() - l.dueTs >= 7 * DAY)
      const soft7Num = due7.filter((l) => l.soft7 === 1).length
      row[`${key}Loans`] = groupLoans.length
      row[`${key}Due1`] = due1.length
      row[`${key}FONum`] = foNum
      row[`${key}FO`] = due1.length ? +((foNum / due1.length) * 100).toFixed(1) : null
      row[`${key}Due7`] = due7.length
      row[`${key}Soft7Num`] = soft7Num
      row[`${key}Soft7`] = due7.length ? +((soft7Num / due7.length) * 100).toFixed(1) : null
    }
    return row
  })
}

// ---------- 静态文件 ----------
function serveStatic(req, res) {
  const urlPath = req.url === '/' ? '/index.html' : req.url.split('?')[0]
  const filePath = path.join(PUBLIC, path.normalize(urlPath).replace(/^([/\\])+/, ''))
  try {
    const data = readFileSync(filePath)
    res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] ?? 'application/octet-stream' })
    res.end(data)
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
    res.end('未找到文件')
  }
}

// ---------- API 路由 ----------
const routes = new Map()
routes.set('GET /api/kpi', (req, res, url) => {
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(JSON.stringify(kpi({
    dueFrom: url.searchParams.get('dueFrom') ?? undefined,
    dueTo: url.searchParams.get('dueTo') ?? undefined,
  })))
})

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`)
  const key = `${req.method} ${url.pathname}`
  const handler = routes.get(key)
  if (handler) return handler(req, res, url)
  serveStatic(req, res)
})

server.listen(PORT, () => {
  console.log(`AI 风控策略驾驶舱 demo 已启动: http://localhost:${PORT}`)
})
