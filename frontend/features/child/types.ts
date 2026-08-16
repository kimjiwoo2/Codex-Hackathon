export type ChildJourneyStage = 'READY' | 'RIGHT' | 'LEFT' | 'STRAIGHT' | 'STOP' | 'ARRIVED' | 'RETURNING';

export type ChildJourneyView = {
  stage: ChildJourneyStage;
  headlinePrefix?: string;
  headlineAccent?: string;
  headlineSuffix?: string;
  direction?: 'right' | 'left' | 'up';
  warning?: boolean;
};
