'use strict';

/**
 * Angel Wings — 40-Line Deterministic Trailing Profit Shield for Binary Prediction Markets
 * ========================================================================================
 * Designed for manual mobile traders on fast 5m/15m binary contracts (Polymarket US / Kalshi):
 *   1. ZERO resting GTC limit orders -> your mobile "Cash Out" button stays 100% unlocked.
 *   2. NEVER sells at a loss -> strictly requires `curBid >= avgCost + 0.04`.
 *   3. Low-entry runner shield (`avgCost <= 0.35`, e.g., 20c-35c bounce entries):
 *        - Ignores noisy 20c -> 50c -> 30c mid-round chop so you aren't shaken out early.
 *        - Arms once `peakBid >= 0.62`: lets 70c / 80c / 90c+ runners fly, then locks
 *          immediately on a >=5c pullback from peak OR any dip back to the 60c hard floor.
 *   4. Standard entries (`avgCost > 0.35`):
 *        - Tight 6c trailing lock once `peakBid >= 0.70` (and >=12c above entry).
 *        - Standard 8c trailing lock once `peakBid >= avgCost + 0.15`.
 *
 * Prices are in USD per share (0.01 to 0.99). Poll L2 WebSocket best bid every 250ms and
 * fire an IOC limit sell when `downsideProfitExit()` returns a non-null reason string.
 */
function downsideProfitExit({ avgCost, peakBid, curBid }) {
  if (![avgCost, peakBid, curBid].every(Number.isFinite)) return null;
  if (curBid < avgCost + 0.04 - 1e-9) return null;

  const entryC = Math.round(avgCost * 100);
  const peakC = Math.round(peakBid * 100);
  const bidC = Math.round(curBid * 100);

  // Tier 0: Low-entry runner shield (<=35c entry -> armed at 62c+, 5c peak-trail + 60c hard floor)
  if (avgCost <= 0.35 + 1e-9) {
    if (peakBid >= 0.62 - 1e-9) {
      const drop = peakBid - curBid;
      if (drop >= 0.05 - 1e-9 || curBid <= 0.60 + 1e-9) {
        return `ANGEL WING 20s-RUNNER LOCK (entry ${entryC}c -> peak ${peakC}c -> bid ${bidC}c)`;
      }
    }
    return null;
  }

  // Tier 1: High-peak lock (peak >= 70c -> 6c trail)
  if (peakBid >= 0.70 - 1e-9 && peakBid >= avgCost + 0.12 - 1e-9) {
    if (peakBid - curBid >= 0.06 - 1e-9) {
      return `ANGEL WING HIGH-PEAK LOCK (entry ${entryC}c -> peak ${peakC}c -> bid ${bidC}c)`;
    }
  }

  // Tier 2: Standard profit trail (peak >= entry + 15c -> 8c trail)
  if (peakBid >= avgCost + 0.15 - 1e-9 && (peakBid - curBid) >= 0.08 - 1e-9) {
    return `ANGEL WING PEAK-TRAIL SAVE (entry ${entryC}c -> peak ${peakC}c -> bid ${bidC}c)`;
  }

  return null;
}

module.exports = { downsideProfitExit };
