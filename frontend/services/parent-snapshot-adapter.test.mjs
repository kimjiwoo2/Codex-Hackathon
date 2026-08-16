import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

const outputDirectory = mkdtempSync(join(tmpdir(), 'ican-parent-snapshot-'));
execFileSync('./node_modules/.bin/tsc', [
  'services/parent-snapshot-adapter.ts',
  '--module',
  'commonjs',
  '--outDir',
  outputDirectory,
  '--target',
  'es2022',
], { stdio: 'inherit' });
const { applySnapshot } = await import(join(outputDirectory, 'parent-snapshot-adapter.js'));

test('keeps the greatest cursor and deduplicates events after a reconnect', () => {
  const first = applySnapshot(
    { cursor: 0, events: [] },
    { events: [{ eventId: 3 }], nextEventId: 3 },
  );
  const recovered = applySnapshot(first, {
    events: [{ eventId: 3 }, { eventId: 5 }],
    nextEventId: 5,
  });
  const staleResponse = applySnapshot(recovered, { events: [{ eventId: 3 }], nextEventId: 3 });

  assert.equal(staleResponse.cursor, 5);
  assert.deepEqual(staleResponse.events.map((event) => event.eventId), [3, 5]);
});

test('requests the snapshot endpoint with the stored cursor and parent token', async () => {
  process.env.EXPO_PUBLIC_API_BASE_URL = 'https://api.example.test/';
  const { fetchParentSnapshot } = await import(join(outputDirectory, 'parent-snapshot-adapter.js'));
  let requestUrl;
  let requestOptions;
  const result = await fetchParentSnapshot('mission/1', 'parent-token', 5, async (url, options) => {
    requestUrl = url;
    requestOptions = options;
    return { ok: true, json: async () => ({ events: [], nextEventId: 5 }) };
  });

  assert.equal(requestUrl, 'https://api.example.test/missions/mission%2F1/snapshot?afterEventId=5');
  assert.equal(requestOptions.headers.Authorization, 'Bearer parent-token');
  assert.equal(result.nextEventId, 5);
});

test.after(() => rmSync(outputDirectory, { force: true, recursive: true }));
