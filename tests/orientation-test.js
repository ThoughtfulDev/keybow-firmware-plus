const assert = require('node:assert/strict');
const {view, read, write} = require('../editor/static/orientation.js');
const expected = [
  [12, 9, 6, 3, 11, 8, 5, 2, 10, 7, 4, 1],
  [10, 11, 12, 7, 8, 9, 4, 5, 6, 1, 2, 3],
  [1, 4, 7, 10, 2, 5, 8, 11, 3, 6, 9, 12],
  [3, 2, 1, 6, 5, 4, 9, 8, 7, 12, 11, 10],
];
for (let turn = 0; turn < 4; turn++) {
  const result = view(turn * 90);
  assert.deepEqual(result.order.map(index => index + 1), expected[turn]);
  assert.equal(new Set(result.order).size, 12);
  assert.equal(result.columns, turn % 2 ? 3 : 4);
}
assert.deepEqual(view(360), view(0));
assert.deepEqual(view('90'), view(0));
const data = new Map();
const storage = {getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value)};
assert.equal(read(storage), 0);
write(storage, 270);
assert.equal(read(storage), 270);
storage.setItem('keybow-editor-orientation', '45');
assert.equal(read(storage), 0);
const blocked = {getItem() {throw Error('blocked');}, setItem() {throw Error('blocked');}};
assert.equal(read(blocked), 0);
write(blocked, 90);
console.log('Orientation mapping and storage fallbacks passed');
