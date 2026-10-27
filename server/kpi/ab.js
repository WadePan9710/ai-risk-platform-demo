// KPI 复算层：输入数据集，输出 A/B 分档对比 + 功效检验（纯函数，数据注入）。
// 口径：首逾期主线（到期≥1天未结清，T+1 可判）；soft7/dpd7 为成熟单对照。
import { twoPropZ } from './power.js'

const DAY = 86400000

function weekBucket(ts) {
  const d = new Date(ts)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  const y = d.getFullYear(), m = d.getMonth() + 1, dd = d.getDate()
  return `${y}-${String(m).padStart(2, '0')}-${String(dd).padStart(2, '0')}`
}

// ---------- 老客首逾期周序列 ----------
export function dueWeekSeries(loans, dueFrom, dueTo) {
  const weeks = new Map()
  for (const b of loans) {
    const k = weekBucket(b.dueTs)
    if (dueFrom && k < dueFrom) continue
    if (dueTo && k > dueTo) continue
    if (!weeks.has(k)) weeks.set(k, { week: k, n: 0, foBad: 0, obs7: 0, bad7: 0, soft7: 0 })
    const w = weeks.get(k)
    w.n++
    w.foBad += b.firstOverdue
    if (Date.now() > b.dueTs + 7 * DAY) {
      w.obs7++
      w.bad7 += b.bad7
      w.soft7 += b.soft7
    }
  }
  return [...weeks.values()].sort((a, b) => a.week.localeCompare(b.week)).map((w) => {
    const weekEnd = new Date(w.week + 'T00:00:00').getTime() + 7 * DAY
    const foComparable = Date.now() > weekEnd + DAY
    return {
      week: w.week, n: w.n,
      firstOverdueRate: foComparable ? +(w.foBad / w.n * 100).toFixed(1) : null,
      foComparable,
      dpd7Rate: w.obs7 ? +(w.bad7 / w.obs7 * 100).toFixed(1) : null,
      soft7Rate: w.obs7 ? +(w.soft7 / w.obs7 * 100).toFixed(1) : null,
    }
  })
}

export function weekOverWeek(series) {
  const done = series.filter((w) => w.foComparable)
  const latest = done[done.length - 1] ?? null
  const prev = done.length >= 2 ? done[done.length - 2] : null
  if (!latest || !prev) return { unavailable: '数据源未就绪：无两个整周到期的老客到期周', latest: null, prev: null }
  const diff = +(latest.firstOverdueRate - prev.firstOverdueRate).toFixed(1)
  const observing = [...series].reverse().find((w) => !w.foComparable)
  return {
    latestWeek: latest.week, latestRate: latest.firstOverdueRate, latestN: latest.n,
    prevWeek: prev.week, prevRate: prev.firstOverdueRate, prevN: prev.n,
    diff,
    direction: diff > 0.5 ? '↑ 恶化' : diff < -0.5 ? '↓ 改善' : '→ 持平',
    dpd7Ref: { latest: latest.dpd7Rate, prev: prev.dpd7Rate },
    soft7Ref: { latest: latest.soft7Rate, prev: prev.soft7Rate },
    observing: observing ? { week: observing.week, n: observing.n } : null,
  }
}

// ---------- EG/CG 组级摘要 ----------
export function abGroupSummary(loans, now) {
  const out = {}
  for (const key of ['EG', 'CG']) {
    const list = loans.filter((l) => l.group === key)
    const due1 = list.filter((l) => now - l.dueTs >= DAY)
    const foN = due1.filter((l) => l.firstOverdue).length
    out[key] = {
      loans: list.length,
      dueAll: due1.length,
      firstOverdueRate: due1.length ? +((foN / due1.length) * 100).toFixed(1) : null,
    }
  }
  return out
}

// 分档表：每格分子分母同时下发（Due1/FONum = 首逾期；Due7/Bad7Num = dpd7 对照）
export function abTierTable(loans, now) {
  const tiers = ['A', 'B', 'C', 'D', 'E', 'F']
  return tiers.map((tier) => {
    const row = { tier }
    for (const key of ['EG', 'CG']) {
      const groupLoans = loans.filter((l) => l.group === key && l.tier === tier)
      const due1 = groupLoans.filter((l) => now - l.dueTs >= DAY)
      const due7 = due1.filter((l) => now - l.dueTs >= 7 * DAY)
      const foNum = due1.filter((l) => l.firstOverdue).length
      const bad7Num = due7.filter((l) => l.bad7 === 1).length
      row[`${key}Decisions`] = groupLoans.reduce((s, l) => s + (l.decisionCount ?? 0), 0)
      row[`${key}Loans`] = groupLoans.length
      row[`${key}Due1`] = due1.length
      row[`${key}FONum`] = foNum
      row[`${key}FO`] = due1.length ? +((foNum / due1.length) * 100).toFixed(1) : null
      row[`${key}Due7`] = due7.length
      row[`${key}Bad7Num`] = bad7Num
      row[`${key}DPD7`] = due7.length ? +((bad7Num / due7.length) * 100).toFixed(1) : null
    }
    return row
  })
}

// 功效：两比例 z（双尾，min n≥minN 可判）+ 合并检验
export function abPower(tierTable, loans, now, minN = 10) {
  const cells = []
  let testable = 0, significant = 0
  for (const row of tierTable) {
    const t = twoPropZ(row.EGFONum, row.EGDue1, row.CGFONum, row.CGDue1)
    const ok = t !== null && Math.min(row.EGDue1, row.CGDue1) >= minN
    if (ok) testable++
    if (ok && t.p < 0.05) significant++
    cells.push({ tier: row.tier, testable: ok, p: t ? t.p : null })
  }
  const allDue1 = loans.filter((l) => now - l.dueTs >= DAY)
  const pooled = twoPropZ(
    allDue1.filter((l) => l.group === 'EG' && l.firstOverdue).length,
    allDue1.filter((l) => l.group === 'EG').length,
    allDue1.filter((l) => l.group === 'CG' && l.firstOverdue).length,
    allDue1.filter((l) => l.group === 'CG').length,
  )
  return { minN, testable, significant, cells, pooled }
}

// 生成结论文案（数字全部由上方计算产出，不写死）
export function conclusions(tierTable, loans, now, minN = 10) {
  const out = []
  for (const key of ['EG', 'CG']) {
    const list = loans.filter((l) => l.group === key)
    const due1 = list.filter((l) => now - l.dueTs >= DAY)
    const foN = due1.filter((l) => l.firstOverdue).length
    const rate = due1.length ? +((foN / due1.length) * 100).toFixed(1) : null
    out.push({ group: key, dueN: due1.length, firstOverdueRate: rate })
  }
  const [eg, cg] = out
  if (eg.dueN >= 30 && cg.dueN >= 30 && eg.firstOverdueRate != null && cg.firstOverdueRate != null) {
    const diff = +(eg.firstOverdueRate - cg.firstOverdueRate).toFixed(1)
    out.verdict = `首逾期主线（大样本）：EG ${eg.dueN} 笔 ${eg.firstOverdueRate}% vs CG ${cg.dueN} 笔 ${cg.firstOverdueRate}%（差 ${diff > 0 ? '+' : ''}${diff}pp）`
  } else {
    out.verdict = '首逾期样本不足（<30 笔/组），组级对比暂不具备统计意义，继续积累表现期。'
  }
  return out
}
