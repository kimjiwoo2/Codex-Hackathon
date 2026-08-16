import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

const outputDirectory = mkdtempSync(join(tmpdir(), 'ican-parent-monitor-'));
execFileSync('./node_modules/.bin/tsc', [
  'features/mission/parent-monitor-presentation.ts',
  '--module',
  'commonjs',
  '--outDir',
  outputDirectory,
  '--target',
  'es2022',
], { stdio: 'inherit' });
const { getEventLabel, getMissionStatusPresentation } = await import(
  join(outputDirectory, 'parent-monitor-presentation.js')
);

test('shows a clear departure message before hazard events', () => {
  assert.deepEqual(getMissionStatusPresentation('WAITING'), {
    label: '출발 대기 중',
    message: '이준이가 참여 코드를 입력하면 출발해요.',
    progress: 6,
  });
  assert.deepEqual(getMissionStatusPresentation('GOING'), {
    label: '마트로 이동 중',
    message: '이준이가 마트로 출발했어요.',
    progress: 32,
  });
});

test('moves progress forward with each mission status', () => {
  const statuses = ['WAITING', 'GOING', 'SHOPPING', 'RETURNING', 'COMPLETED'];
  assert.deepEqual(statuses.map((status) => getMissionStatusPresentation(status).progress), [6, 32, 58, 80, 100]);
});

test('translates backend event codes into parent-facing Korean', () => {
  assert.equal(getEventLabel('ARRIVED_STORE'), '행복 슈퍼에 도착했어요');
  assert.equal(getEventLabel('ROAD_HAZARD'), '주변 위험을 확인하고 있어요');
  assert.equal(getEventLabel('RETURNING'), '집으로 출발했어요');
  assert.equal(getEventLabel('UNKNOWN_EVENT'), '새로운 진행 알림');
});

test.after(() => rmSync(outputDirectory, { force: true, recursive: true }));
