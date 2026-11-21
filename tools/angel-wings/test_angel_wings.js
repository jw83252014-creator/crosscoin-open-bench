'use strict';

const assert = require('assert');
const { downsideProfitExit } = require('./angel_wings_policy');

const cases = [
  ['Never sells at a loss', { avgCost: 0.50, peakBid: 0.75, curBid: 0.48 }, false],
  ['25c -> 52c -> 40c chop stays open (HOLD)', { avgCost: 0.25, peakBid: 0.52, curBid: 0.40 }, false],
  ['25c -> 65c -> 63c runner stays open (HOLD)', { avgCost: 0.25, peakBid: 0.65, curBid: 0.63 }, false],
  ['25c -> 63c -> 60c hits 60c floor (LOCK)', { avgCost: 0.25, peakBid: 0.63, curBid: 0.60 }, true],
  ['27c -> 78c -> 71c locks runner peak (LOCK)', { avgCost: 0.27, peakBid: 0.78, curBid: 0.71 }, true],
  ['55c -> 75c -> 69c standard high-peak (LOCK)', { avgCost: 0.55, peakBid: 0.75, curBid: 0.69 }, true],
];

for (const [label, input, shouldLock] of cases) {
  const res = downsideProfitExit(input);
  assert.strictEqual(Boolean(res), shouldLock, `Failed: ${label} (got ${res})`);
  console.log(`PASS | ${label} => ${res || 'HOLD'}`);
}
