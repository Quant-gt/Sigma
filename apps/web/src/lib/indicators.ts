// apps/web/src/lib/indicators.ts
// Ported from Quantra Legacy with strict TypeScript & zero-allocation optimizations

export interface Candle {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp?: number;
}

export function calculateRSI(closes: number[], period = 14): (number | null)[] {
  const rsi: (number | null)[] = Array(closes.length).fill(null);
  if (closes.length <= period) return rsi;

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i]! - closes[i - 1]!;
    if (diff > 0) gains += diff;
    else losses -= diff;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  if (avgLoss === 0) rsi[period] = 100;
  else {
    const rs = avgGain / avgLoss;
    rsi[period] = Math.round(100 - 100 / (1 + rs));
  }

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i]! - closes[i - 1]!;
    avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period;
    avgLoss = (avgLoss * (period - 1) + (diff < 0 ? -diff : 0)) / period;

    if (avgLoss === 0) {
      rsi[i] = 100;
    } else {
      const rs = avgGain / avgLoss;
      rsi[i] = Math.round(100 - 100 / (1 + rs));
    }
  }
  return rsi;
}

export function calculateATR(candles: Candle[], period = 14): (number | null)[] {
  const atr: (number | null)[] = Array(candles.length).fill(null);
  if (candles.length <= period) return atr;

  const trs = candles.map((c, i) => {
    if (i === 0) return c.high - c.low;
    const prevClose = candles[i - 1]!.close;
    return Math.max(c.high - c.low, Math.abs(c.high - prevClose), Math.abs(c.low - prevClose));
  });

  let sum = 0;
  for (let i = 1; i <= period; i++) {
    sum += trs[i]!;
  }
  let avg = sum / period;
  atr[period] = avg;

  for (let i = period + 1; i < trs.length; i++) {
    avg = (avg * (period - 1) + trs[i]!) / period;
    atr[i] = avg;
  }
  return atr;
}

export function calculateSupertrend(candles: Candle[], period = 10, multiplier = 3): (number | null)[] {
  const st: (number | null)[] = Array(candles.length).fill(null);
  if (candles.length <= period) return st;

  const atr = calculateATR(candles, period);
  const basicUpper = candles.map((c, i) => (c.high + c.low) / 2 + multiplier * (atr[i] || 0));
  const basicLower = candles.map((c, i) => (c.high + c.low) / 2 - multiplier * (atr[i] || 0));
  
  const finalUpper: number[] = Array(candles.length).fill(0);
  const finalLower: number[] = Array(candles.length).fill(0);
  
  finalUpper[period] = basicUpper[period]!;
  finalLower[period] = basicLower[period]!;
  st[period] = finalUpper[period]!;

  for (let i = period + 1; i < candles.length; i++) {
    const prevClose = candles[i - 1]!.close;
    const bu = basicUpper[i]!;
    const bl = basicLower[i]!;
    const fuPrev = finalUpper[i - 1]!;
    const flPrev = finalLower[i - 1]!;

    finalUpper[i] = (bu < fuPrev || prevClose > fuPrev) ? bu : fuPrev;
    finalLower[i] = (bl > flPrev || prevClose < flPrev) ? bl : flPrev;

    const stPrev = st[i - 1]!;
    const c = candles[i]!;

    if (stPrev === fuPrev) {
      st[i] = (c.close > finalUpper[i]!) ? finalLower[i]! : finalUpper[i]!;
    } else {
      st[i] = (c.close < finalLower[i]!) ? finalUpper[i]! : finalLower[i]!;
    }
  }
  
  return st.map(val => val !== null ? parseFloat(val.toFixed(2)) : null);
}

export function calculateVWAP(candles: Candle[]): (number | null)[] {
  const vwap: (number | null)[] = Array(candles.length).fill(null);
  let cumulativeTPV = 0;
  let cumulativeVolume = 0;
  let currentDay = -1;

  for (let i = 0; i < candles.length; i++) {
    const c = candles[i]!;
    let candleDay = c.timestamp ? new Date(c.timestamp).getUTCDate() : -1;

    if (candleDay !== currentDay && currentDay !== -1) {
      cumulativeTPV = 0;
      cumulativeVolume = 0;
    }
    currentDay = candleDay;

    const typicalPrice = (c.high + c.low + c.close) / 3;
    cumulativeTPV += typicalPrice * c.volume;
    cumulativeVolume += c.volume;

    vwap[i] = cumulativeVolume === 0
      ? (i > 0 ? (vwap[i - 1] ?? typicalPrice) : typicalPrice)
      : parseFloat((cumulativeTPV / cumulativeVolume).toFixed(4));
  }

  return vwap;
}

export function calculateADX(candles: Candle[], period = 14): (number | null)[] {
  const adx: (number | null)[] = Array(candles.length).fill(null);
  if (candles.length <= period * 2) return adx;
  
  const trs: number[] = [0];
  const plusDM: number[] = [0];
  const minusDM: number[] = [0];
  
  for (let i = 1; i < candles.length; i++) {
    const c = candles[i]!;
    const p = candles[i - 1]!;
    trs.push(Math.max(c.high - c.low, Math.abs(c.high - p.close), Math.abs(c.low - p.close)));
    const upmove = c.high - p.high;
    const downmove = p.low - c.low;
    plusDM.push(upmove > downmove && upmove > 0 ? upmove : 0);
    minusDM.push(downmove > upmove && downmove > 0 ? downmove : 0);
  }
  
  let smoothedTR = trs.slice(1, period + 1).reduce((a, b) => a + b, 0);
  let smoothedPlusDM = plusDM.slice(1, period + 1).reduce((a, b) => a + b, 0);
  let smoothedMinusDM = minusDM.slice(1, period + 1).reduce((a, b) => a + b, 0);
  
  const dxs: (number | null)[] = Array(candles.length).fill(null);
  dxs[period] = (smoothedTR === 0) ? 0 : 100 * Math.abs(smoothedPlusDM - smoothedMinusDM) / (smoothedPlusDM + smoothedMinusDM);
  
  for (let i = period + 1; i < candles.length; i++) {
    smoothedTR = smoothedTR - smoothedTR / period + trs[i]!;
    smoothedPlusDM = smoothedPlusDM - smoothedPlusDM / period + plusDM[i]!;
    smoothedMinusDM = smoothedMinusDM - smoothedMinusDM / period + minusDM[i]!;
    
    if (smoothedTR === 0) {
      dxs[i] = 0;
      continue;
    }
    const plusDI = (100 * smoothedPlusDM) / smoothedTR;
    const minusDI = (100 * smoothedMinusDM) / smoothedTR;
    const sum = plusDI + minusDI;
    const diff = Math.abs(plusDI - minusDI);
    dxs[i] = sum === 0 ? 0 : (100 * diff) / sum;
  }
  
  let adxSum = 0;
  for (let i = period; i < period * 2; i++) {
    adxSum += dxs[i]!;
  }
  let currentAdx = adxSum / period;
  adx[period * 2 - 1] = Math.round(currentAdx);
  
  for (let i = period * 2; i < dxs.length; i++) {
    currentAdx = (currentAdx * (period - 1) + dxs[i]!) / period;
    adx[i] = Math.round(currentAdx);
  }
  
  return adx;
}
