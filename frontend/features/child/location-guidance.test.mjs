import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

const outputDirectory = mkdtempSync(join(tmpdir(), 'ican-location-guidance-'));
execFileSync('./node_modules/.bin/tsc', [
  'features/child/location-guidance.ts',
  'features/child/types.ts',
  '--module',
  'commonjs',
  '--outDir',
  outputDirectory,
  '--target',
  'es2022',
  '--rootDir',
  '.',
], { stdio: 'inherit' });
const { stageFromGuidance } = await import(join(outputDirectory, 'features/child/location-guidance.js'));

test('arrival and returning statuses override individual instruction codes', () => {
  assert.equal(stageFromGuidance('CONTINUE', 'SHOPPING'), 'ARRIVED');
  assert.equal(stageFromGuidance('TURN_LEFT', 'RETURNING'), 'RETURNING');
  assert.equal(stageFromGuidance('ARRIVED', 'COMPLETED'), 'RETURNING');
});

test('going instructions map to the expected child journey stages', () => {
  assert.equal(stageFromGuidance('TURN_LEFT', 'GOING'), 'LEFT');
  assert.equal(stageFromGuidance('TURN_RIGHT', 'GOING'), 'RIGHT');
  assert.equal(stageFromGuidance('CROSSWALK_STOP', 'GOING'), 'STOP');
  assert.equal(stageFromGuidance('CONTINUE', 'GOING'), 'STRAIGHT');
});

test.after(() => rmSync(outputDirectory, { force: true, recursive: true }));
