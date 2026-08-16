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
const { applySnapshot, isParentSnapshotCredentialReady, ParentSnapshotPollingController } = await import(join(outputDirectory, 'parent-snapshot-adapter.js'));

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

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

test('does not poll with mock credentials before the real create adapter is available', () => {
  assert.equal(isParentSnapshotCredentialReady('demo-mission-ican', 'mock-parent-token'), false);
  assert.equal(isParentSnapshotCredentialReady('mission-1', 'parent-token'), true);
});

test('serializes polling and keeps the completed response after an overlapping retry', async () => {
  const first = deferred();
  let requests = 0;
  const controller = new ParentSnapshotPollingController({ cursor: 0, events: [] }, async () => {
    requests += 1;
    return first.promise;
  });

  const initial = controller.refresh();
  const overlapping = await controller.refresh();
  first.resolve({ events: [{ eventId: 4 }], nextEventId: 4 });
  const completed = await initial;

  assert.equal(requests, 1);
  assert.deepEqual(overlapping, { kind: 'skipped' });
  assert.equal(completed.kind, 'updated');
  assert.equal(controller.current.cursor, 4);
});

test('ignores a deferred response after unmount or credential replacement', async () => {
  const pending = deferred();
  const controller = new ParentSnapshotPollingController({ cursor: 7, events: [] }, async () => pending.promise);

  const request = controller.refresh();
  controller.dispose();
  pending.resolve({ events: [{ eventId: 8 }], nextEventId: 8 });

  assert.deepEqual(await request, { kind: 'skipped' });
  assert.equal(controller.current.cursor, 7);
});

test('allows a retry after an error without changing the cursor', async () => {
  let fail = true;
  const controller = new ParentSnapshotPollingController({ cursor: 2, events: [] }, async () => {
    if (fail) {
      fail = false;
      throw new Error('offline');
    }
    return { events: [{ eventId: 3 }], nextEventId: 3 };
  });

  const error = await controller.refresh();
  const retry = await controller.refresh();

  assert.equal(error.kind, 'error');
  assert.equal(retry.kind, 'updated');
  assert.equal(controller.current.cursor, 3);
});

test.after(() => rmSync(outputDirectory, { force: true, recursive: true }));
