// 统计工具：两比例 z 检验（双尾）+ Wilson 区间。erf 用 Abramowitz-Stegun 7.1.26 近似（误差 <1.5e-7）。
export function erf(x) {
  const s = x < 0 ? -1 : 1
  const ax = Math.abs(x)
  const t = 1 / (1 + 0.3275911 * ax)
  const y = 1 - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-ax * ax)
  return s * y
}

// 两比例 z 检验：返回 {z, p}（p 为双尾）。任一分母为 0 返回 null。
export function twoPropZ(x1, n1, x2, n2) {
  if (!n1 || !n2) return null
  const p1 = x1 / n1, p2 = x2 / n2
  const p = (x1 + x2) / (n1 + n2)
  const se = Math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
  if (se === 0) return { z: 0, p: 1 }
  const z = (p1 - p2) / se
  const pval = +(2 * (1 - 0.5 * (1 + erf(Math.abs(z) / Math.SQRT2)))).toFixed(3)
  return { z: +z.toFixed(3), p: pval }
}

// Wilson 95% 置信区间
export function wilson(x, n) {
  if (!n) return null
  const z = 1.959963984540054
  const p = x / n
  const d = 1 + z * z / n
  const center = p + z * z / (2 * n)
  const spread = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
  return { lo: +(((center - spread) / d) * 100).toFixed(1), hi: +(((center + spread) / d) * 100).toFixed(1) }
}

const pct = (x, n) => (n ? +((x / n) * 100).toFixed(1) : null)

// 分档格子可判性：min n≥minN 才可检验
export function judgeCell(egN, cgN, minN) {
  return Math.min(egN, cgN) >= minN
}

// 聚合组：首逾期（主线）+ soft7/dpd7（成熟对照）
export function groupPerf(list, now, dueWindow = null) {
  const inWin = (r, ts) => (dueWindow ? ts >= dueWindow.from && ts <= dueWindow.to : true)
  const due1 = list.filter((r) => r.dueTs && now - r.dueTs >= 1 * DAY && inWin(r, r.dueTs))
  const matured = due1.filter((r) => now - r.dueTs >= 7 * DAY)
  const settled = matured.filter((r) => r.settledTs != null)
  const foN = due1.filter((r) => r.firstOverdue).length
  const bad7N = matured.filter((r) => r.bad7 === 1).length
  const soft7N = matured.filter((r) => r.soft7 === 1).length
  const paid = settled.reduce((s, r) => s + (r.paidAmount ?? r.amount), 0)
  const principal = settled.reduce((s, r) => s + r.amount, 0)
  return {
    loans: list.length,
    dueAll: due1.length,
    firstOverdue: pct(foN, due1.length),
    foN, foDenom: due1.length,
    dpd7Ref: pct(bad7N, matured.length), bad7N, matured,
    soft7Ref: pct(soft7N, matured.length), soft7N: soft7Bad.length,
    paidRate: principal ? +((paid / principal) * 100).toFixed(1) : null,
  }
}

const DAY = 86400000
