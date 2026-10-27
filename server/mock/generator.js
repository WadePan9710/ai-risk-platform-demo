// 数据集构建（demo）：合成 12 个到期周的老客放款 + EG/CG 授信决策 + 规则命中。
// 全部为脱敏合成数据，零真实客户信息；接口契约与生产版一致。
// 口径：首逾 = 到期≥1天未结清（T+1 可判，主线）；soft7/dpd7 = 成熟单对照。

// 可复现伪随机（mulberry32）
export function rng(seed) {
  let a = seed >>> 0
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const DAY = 86400000
const WEEK_DAYS = 7

export function weekStartOf(ts) {
  const d = new Date(ts)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return d.getTime()
}

export function fmtDate(ts) {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export const DEMO_CONFIG = {
  seed: 20260930,
  dueWeeks: 12,
  loansPerWeek: [230, 300],
  egShare: 0.48,
  foBaseEG: 0.42,
  foBaseCG: 0.40,
  downgradeRateEG: 0.13,
  rules: [
    { id: 'R_B01', tier: 'B', label: 'B档: 近1天活跃申请≥2次', foLift: 1.35 },
    { id: 'R_B02', tier: 'B', label: 'B档: 近3天贷款短信≥6条', foLift: 0.85 },
    { id: 'R_C01', tier: 'C', label: 'C档: 近3天活跃申请≥5次', foLift: 1.28 },
    { id: 'R_C02', tier: 'C', label: 'C档: 未结清金额占比≥22%', foLift: 0.95 },
    { id: 'R_D01', tier: 'D', label: 'D档: 近3天贷款短信≥5条', foLift: 1.10 },
    { id: 'R_E01', tier: 'E', label: 'E档: 近3天活跃申请≥8次', foLift: 0.62 },
  ],
  modelHealth: {
    sampleSize: { loan: 6465, credit: 11933 },
    baselineBadRate: 0.444,
    models: [
      { name: 'xgb_reloan_v2', path: '支用直连', n: 4089, auc: 0.557, verdict: '⚠️ 衰减' },
      { name: 'xgb_reloan_v1', path: '支用直连', n: 1550, auc: 0.537, verdict: '🔴 接近随机' },
      { name: 'xgb_newloan_v2', path: '进件→放款', n: 9639, auc: 0.508, verdict: '🔴 接近随机' },
      { name: 'lr_credit_v1', path: '进件→放款', n: 10599, auc: 0.494, verdict: '🔴 接近随机' },
      { name: 'ascore_v1', path: '进件→放款', n: 6284, auc: 0.518, verdict: '🔴 接近随机' },
      { name: 'ios_reloan_v1', path: '支用直连', n: 340, auc: 0.623, verdict: '✅ 正常' },
      { name: 'ensemble_reloan_v1', path: '支用直连', n: 812, auc: null, verdict: '⚠️ 口径未定' },
      { name: 'ascore_v2', path: '进件→放款', n: 1879, auc: 0.561, verdict: '⚠️ 衰减' },
      { name: 'ios_ascore_v1', path: '进件→放款', n: 105, auc: null, verdict: '⚠️ 样本不足' },
    ],
  },
  dispositions: 6,
}

export function buildDataset(now = Date.now()) {
  const rand = rng(DEMO_CONFIG.seed)
  const cfg = DEMO_CONFIG
  const loans = []
  const decisions = []
  const thisWeekStart = weekStartOf(now)

  for (let w = cfg.dueWeeks; w >= 1; w--) {
    const weekStart = thisWeekStart - w * WEEK_DAYS * DAY
    const weekLabel = fmtDate(weekStart)
    const n = cfg.loansPerWeek[0] + Math.floor(rand() * (cfg.loansPerWeek[1] - cfg.loansPerWeek[0]))
    const trend = 1 + (cfg.dueWeeks - w) * 0.015

    for (let i = 0; i < n; i++) {
      const group = rand() < cfg.egShare ? 'EG' : 'CG'
      const foBase = group === 'EG' ? cfg.foBaseEG : cfg.foBaseCG
      const fo = rand() < Math.min(0.85, foBase * trend * (0.9 + rand() * 0.2)) ? 1 : 0
      const soft7 = fo === 1 ? (rand() < 0.9 ? 1 : 0) : rand() < 0.05 ? 1 : 0
      const dueTs = weekStart + Math.floor(rand() * WEEK_DAYS) * DAY
      const amount = 1500 + Math.floor(rand() * 13) * 500

      // 决策记录（约 95% 放款对应授信决策）
      const hasDecision = rand() < 0.95
      const tier = 'BCDEF'[Math.min(4, Math.floor(rand() * 5))]
      let decision = null
      if (hasDecision) {
        const downgraded = group === 'EG' && rand() < cfg.downgradeRateEG
        decision = {
          decisionId: `D${weekLabel.replace(/-/g, '')}_${i}`,
          group, tier,
          downgraded,
          applyWeek: weekLabel,
          approved: rand() < 0.965,
        }
        decisions.push(decision)
      }

      loans.push({
        loanId: `L${weekLabel.replace(/-/g, '')}_${i}`,
        userId: 100000 + Math.floor(rand() * 900000),
        group, tier,
        decisionId: decision ? decision.decisionId : null,
        dueTs, settledTs: fo === 1 ? null : dueTs - Math.floor(rand() * 3) * DAY,
        isExt: soft7 === 1 && fo === 0 && rand() < 0.5,
        amount,
        firstOverdue: fo,
        bad7: fo,
        soft7,
      })
    }
  }

  // 模型体检（示例脱敏数据：多模型 AUC，含口径未定）
  const modelHealth = {
    generatedAt: new Date(now).toLocaleString('zh-CN', { hour12: false }),
    window: '近90天放款、到期≥7天（示例参数）',
    sampleSize: { loan: 6465, credit: 11933 },
    baselineBadRate: 0.444,
    decisionFreshness: { gapDays: 0, verdict: '✅ 正常' },
    models: DEMO_CONFIG.modelHealth.models.map((m, i) => ({
      ...m,
      sourceTable: i < 2 ? 'loan_rt' : 'credit_rt',
      bad7Num: m.auc != null ? Math.round(m.n * (m.auc > 0.55 ? 0.35 : 0.5)) : 0,
    })),
    thresholds: 'AUC≥0.60 正常；0.55-0.60 衰减；<0.55 接近随机。方向未标定的模型 auc=null + ⚠️口径未定。',
  }

  // 待处置工单（示例）
  const dispositions = Array.from({ length: 8 }, (_, i) => ({
    id: `dp_demo_${i}`,
    userId: 200000 + i * 137,
    level: i === 7 ? '🟡' : '🔴',
    action: i % 2 ? '冻结额度' : '转人工',
    result: i === 5 ? '误报' : '已执行',
    createdAt: new Date(now - (i + 1) * 86400000).toISOString(),
  }))

  return { loans, decisions, modelHealth, dispositions, generatedAt: now }
}

// 数据集单例
let cached = null
export function dataset(now = Date.now()) {
  if (!cached) cached = buildDataset(now)
  return cached
}
export function resetDataset() { cached = null }
