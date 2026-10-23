'use strict';
// Run with node code/d3/check-peladometro.cjs. No browser or atlas build.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({window: {}});
vm.runInContext(fs.readFileSync(path.join(__dirname, 'peladometro.js'), 'utf8'), context);
const calculate = options => JSON.parse(JSON.stringify(context.window.peladometroData(options)));
const person = (name, id, score) => ({name, wikidata_id: id, hair: score === null ? null : {score}});
const data = {
  profiles: {people: [
    person('Nombre A', 'Q1', 100), person('Alias A', 'Q1', 100),
    person('Nombre B', null, 0), person('Nombre C', null, null),
    person('Nombre D', null, '50'), person('Nombre E', null, 25),
    person('Nombre F', null, 50), person('Nombre G', null, 75),
    person('Sin cargo ministerial', 'Q999', 100)
  ]},
  ministers: [
    {name: 'Nombre A', start: '1982-12-31'}, {name: 'Alias A', start: '1990-01-01'},
    {name: 'Nombre B', start: '1983-01-01'}, {name: 'Nombre B', start: '2000-01-01'},
    {name: 'Nombre C', start: '2001-01-01'}, {name: 'Nombre D', start: '2002-01-01'},
    {name: 'Nombre E', start: '2003-01-01'}, {name: 'Nombre F', start: '2004-01-01'},
    {name: 'Nombre G', start: '2005-01-01'}, {name: 'Sin ficha ni fecha'}
  ]
};
const original = JSON.stringify(data);
const all = calculate({data});
assert.equal(all.total, 8, 'One observation per identity; non-ministers excluded');
assert.equal(all.denominator, 5, 'Zero is evaluated; null and numeric strings are missing');
assert.equal(all.missing, 3, 'Include ministers without profile in the missing count');
assert.equal(all.numerator, 3);
assert.equal(all.proportion, 3 / 5);
assert.deepEqual(all.distribution.map(bin => bin.count), [1, 1, 1, 1, 1]);
for (const [threshold, numerator] of [[25, 4], [50, 3], [75, 2], [100, 1]]) {
  assert.equal(calculate({data, threshold}).numerator, numerator, 'Threshold includes equality');
}
const before = calculate({data, period: 'before1983'});
assert.equal(before.total, 1, 'Aliases share their earliest appointment');
assert.equal(before.observations[0].firstAppointment, '1982-12-31');
assert.equal(before.proportion, 1);
const after = calculate({data, period: 'from1983'});
assert.equal(after.total, 6, 'January 1, 1983 belongs in the later group');
assert.equal(after.unknownFirstAppointment, 1);
assert.equal(after.denominator, 4);
assert.equal(after.numerator, 2);
assert.equal(calculate({data,period:'active1966'}).total,7);
const recentBoundary={profiles:{people:[person('Termina justo',null,100),person('Atraviesa',null,25),person('Empieza justo',null,0)]},ministers:[
  {name:'Termina justo',start:'1960-01-01',end:'1966-01-01'},
  {name:'Atraviesa',start:'1960-01-01',end:'1966-01-02'},
  {name:'Empieza justo',start:'1966-01-01',end:'1967-01-01'}
]};
assert.equal(calculate({data:recentBoundary,period:'active1966'}).total,2,'Recent service respects half-open boundaries, not only first appointment');
assert.equal(JSON.stringify(data), original, 'Helper must not mutate source records');
all.observations[0].hair.score = 0;
assert.equal(JSON.stringify(data), original, 'Returned hair metadata must not alias source records');
const conflict = JSON.parse(original);
conflict.profiles.people[1].hair.score = 75;
assert.equal(calculate({data: conflict}).conflicts, 1);
assert.equal(calculate({data: conflict}).denominator, 4);
assert.equal(calculate().proportion, null, 'Empty denominator does not produce zero or NaN');
assert.equal(context.window.mountPeladometro(), null, 'Missing host is harmless');

const real = JSON.parse(fs.readFileSync(path.join(__dirname, '../../data/processed/atlas/atlas.json'), 'utf8'));
const curated = JSON.parse(fs.readFileSync(path.join(__dirname, '../../data/curated/minister-profiles.json'), 'utf8'));
// The generated snapshot may predate the curated Wikidata IDs. Exercise both
// without rebuilding or modifying either input file.
const snapshot = calculate({data: real});
assert.equal(snapshot.distribution.reduce((sum, bin) => sum + bin.count, 0), snapshot.denominator);
const actual = calculate({data: {...real, profiles: curated}});
assert.equal(actual.denominator + actual.missing, actual.total);
assert.equal(actual.distribution.reduce((sum, bin) => sum + bin.count, 0), actual.denominator);
assert.ok(actual.numerator <= actual.denominator);
const dagnino = actual.observations.filter(p => p.name.includes('Dagnino'));
assert.equal(dagnino.length, 1, 'The two Dagnino Pastore profiles share a Wikidata identity');
console.log(JSON.stringify({status: 'ok', total: actual.total, evaluated: actual.denominator,
  missing: actual.missing, atLeast50: actual.numerator, distribution: actual.distribution}, null, 2));
