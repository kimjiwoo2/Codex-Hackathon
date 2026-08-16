import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

const outputDirectory = mkdtempSync(join(tmpdir(), 'ican-child-mission-state-'));
execFileSync('./node_modules/.bin/tsc', [
  'features/child/child-mission-state.ts',
  'features/mission/types.ts',
  '--module',
  'commonjs',
  '--outDir',
  outputDirectory,
  '--target',
  'es2022',
  '--rootDir',
  '.',
], { stdio: 'inherit' });
const {
  applyVerificationToMission,
  createChildMissionState,
  startReturningMission,
} = await import(join(outputDirectory, 'features/child/child-mission-state.js'));

test('join picks the first unmatched item instead of the first array entry', () => {
  const state = createChildMissionState({
    missionId: 'mission-1',
    childToken: 'child-token',
    status: 'GOING',
    instructionCode: 'CONTINUE',
    message: '마트로 출발해요.',
    items: [
      { itemId: 'item-1', name: '우유', brand: '서울우유', size: '1L', verdict: 'MATCH', detectedLabel: '서울우유' },
      { itemId: 'item-2', name: '계란', brand: null, size: '10개', verdict: 'UNKNOWN', detectedLabel: null },
    ],
  });

  assert.equal(state.selectedItem?.itemId, 'item-2');
});

test('MATCH while still shopping advances to the next incomplete item', () => {
  const current = createChildMissionState({
    missionId: 'mission-2',
    childToken: 'child-token',
    status: 'SHOPPING',
    instructionCode: 'ARRIVED',
    message: '마트에 도착했어요.',
    items: [
      { itemId: 'item-1', name: '우유', brand: '서울우유', size: '1L', verdict: 'UNKNOWN', detectedLabel: null },
      { itemId: 'item-2', name: '계란', brand: null, size: '10개', verdict: 'UNKNOWN', detectedLabel: null },
    ],
  });

  const next = applyVerificationToMission(current, {
    verdict: 'MATCH',
    message: '첫 번째 물건을 찾았어요.',
    detectedLabel: '서울우유',
    status: 'SHOPPING',
  });

  assert.equal(next.session?.items[0].verdict, 'MATCH');
  assert.equal(next.selectedItem?.itemId, 'item-2');
});

test('RETURNING clears the selected item and freezes the session in returning mode', () => {
  const current = createChildMissionState({
    missionId: 'mission-3',
    childToken: 'child-token',
    status: 'SHOPPING',
    instructionCode: 'ARRIVED',
    message: '마트에 도착했어요.',
    items: [
      { itemId: 'item-1', name: '우유', brand: '서울우유', size: '1L', verdict: 'UNKNOWN', detectedLabel: null },
    ],
  });

  const verified = applyVerificationToMission(current, {
    verdict: 'MATCH',
    message: '이제 집으로 돌아가요.',
    detectedLabel: '서울우유',
    status: 'RETURNING',
  });
  const returning = startReturningMission(current);

  assert.equal(verified.selectedItem, null);
  assert.equal(verified.session?.status, 'RETURNING');
  assert.equal(returning.selectedItem, null);
  assert.equal(returning.session?.status, 'RETURNING');
});

test.after(() => rmSync(outputDirectory, { force: true, recursive: true }));
