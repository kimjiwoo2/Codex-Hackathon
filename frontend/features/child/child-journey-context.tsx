import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

import type { ChildJourneyStage } from './types';

const stageOrder: ChildJourneyStage[] = ['READY', 'RIGHT', 'LEFT', 'STRAIGHT', 'STOP', 'ARRIVED'];

type ChildJourneyContextValue = {
  stage: ChildJourneyStage;
  advance: () => void;
  setStage: (stage: ChildJourneyStage) => void;
  reset: () => void;
};

const ChildJourneyContext = createContext<ChildJourneyContextValue | null>(null);

export function ChildJourneyProvider({ children }: PropsWithChildren) {
  const [stage, setStage] = useState<ChildJourneyStage>('READY');

  const value = useMemo(
    () => ({
      stage,
      setStage,
      advance: () => setStage((current) => stageOrder[Math.min(stageOrder.indexOf(current) + 1, stageOrder.length - 1)]),
      reset: () => setStage('READY'),
    }),
    [stage],
  );

  return <ChildJourneyContext.Provider value={value}>{children}</ChildJourneyContext.Provider>;
}

export function useChildJourney() {
  const context = useContext(ChildJourneyContext);
  if (!context) throw new Error('useChildJourney must be used within ChildJourneyProvider');
  return context;
}
