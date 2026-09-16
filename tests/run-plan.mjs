// Child-process entry point for tests/timezone.test.mjs.
//
// Runs a fixed set of plans against the committed fixture with a pinned end date
// and prints the result as canonical JSON. Nothing here reads the clock, so the
// only thing that can vary between two runs is the process timezone — which is
// exactly what the timezone test is looking for.
//
// This file is not itself a test; `node --test tests/` skips it.

import { loadEngine, btcAsset, FIXTURE, utc } from './harness.mjs';

const engine = loadEngine();
const BTC    = btcAsset(engine);
const END    = utc('2020-11-20');

// Weekly from the first close spans both US daylight-saving changes of 2020
// (8 March and 1 November); the other cadences land on different weekdays.
const PLANS = [
    { start: '2020-01-01', freq: 7,  own: 100 },
    { start: '2020-02-29', freq: 14, own: 250 },
    { start: '2020-03-07', freq: 7,  own: 75  },
    { start: '2020-03-08', freq: 30, own: 500 },
    { start: '2020-10-25', freq: 7,  own: 50  },
];

const results = PLANS.map((plan) => {
    const r = engine.simulate(FIXTURE.prices, plan, BTC, END);
    return {
        plan,
        purchases:     r.purchases.map(p => `${p.date}@${p.price}`),
        totalInvested: r.totalInvested,
        totalUnits:    r.totalUnits,
        finalPrice:    r.finalPrice,
        finalValue:    r.finalValue,
        roi:           r.roi,
        avgCost:       r.avgCost,
        meanPaid:      r.meanPaid,
        annual:        r.annual,
        duration:      r.duration,
        finalDate:     r.finalDate,
        labels:        r.labels,
    };
});

// `env` is expected to differ between runs — it proves TZ actually took hold.
// `results` must be byte-identical.
process.stdout.write(JSON.stringify({
    env: {
        tz:     Intl.DateTimeFormat().resolvedOptions().timeZone,
        winter: new Date('2020-01-15T00:00:00Z').getTimezoneOffset(),
        summer: new Date('2020-07-15T00:00:00Z').getTimezoneOffset(),
    },
    results,
}, null, 1));
