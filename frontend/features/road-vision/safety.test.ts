import assert from 'node:assert/strict';
import test from 'node:test';

import { jpegByteLength, roadFailureFromStatus, roadSafetyFailureGuidance, roadSafetyGuidance } from './safety.ts';

const forbiddenCrossingPermission = /건너도 된다|건너도돼|건너세요|안전하게 건널|cross_ok|\bgo\b/i;

test('도로 판단과 모든 보수적 오류 문구는 횡단 허가를 포함하지 않는다', () => {
  const messages = [
    roadSafetyGuidance('STOP').message,
    roadSafetyGuidance('CAUTION').message,
    roadSafetyGuidance('UNKNOWN').message,
    roadSafetyFailureGuidance('busy').message,
    roadSafetyFailureGuidance('invalid-frame').message,
    roadSafetyFailureGuidance('network').message,
  ];

  for (const message of messages) assert.doesNotMatch(message, forbiddenCrossingPermission);
});

test('409 busy와 422 validation은 네트워크 실패와 구별해 보수적으로 처리한다', () => {
  assert.equal(roadFailureFromStatus(409), 'busy');
  assert.equal(roadFailureFromStatus(422), 'invalid-frame');
  assert.equal(roadFailureFromStatus(undefined), 'network');
});

test('base64 JPEG 바이트 수를 1MB 제한에 사용할 수 있다', () => {
  assert.equal(jpegByteLength('/9j/2Q=='), 4);
  assert.equal(jpegByteLength('YWJj'), 3);
});
