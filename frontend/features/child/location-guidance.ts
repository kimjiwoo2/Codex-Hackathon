import type { ChildJourneyStage } from './types';

export type ChildInstructionCode =
  | 'CONTINUE'
  | 'TURN_LEFT'
  | 'TURN_RIGHT'
  | 'CROSSWALK_STOP'
  | 'OFF_ROUTE'
  | 'WRONG_WAY'
  | 'LOCATION_UNCERTAIN'
  | 'ARRIVED';

export type ChildLocationStatus = 'WAITING' | 'GOING' | 'SHOPPING' | 'RETURNING' | 'COMPLETED';

export function stageFromGuidance(
  instructionCode: ChildInstructionCode,
  status: ChildLocationStatus,
): ChildJourneyStage {
  if (status === 'SHOPPING') {
    return 'ARRIVED';
  }
  if (status === 'RETURNING' || status === 'COMPLETED') {
    return 'RETURNING';
  }

  switch (instructionCode) {
    case 'TURN_LEFT':
      return 'LEFT';
    case 'TURN_RIGHT':
      return 'RIGHT';
    case 'CROSSWALK_STOP':
    case 'OFF_ROUTE':
    case 'WRONG_WAY':
    case 'LOCATION_UNCERTAIN':
      return 'STOP';
    case 'ARRIVED':
      return 'ARRIVED';
    case 'CONTINUE':
    default:
      return 'STRAIGHT';
  }
}
