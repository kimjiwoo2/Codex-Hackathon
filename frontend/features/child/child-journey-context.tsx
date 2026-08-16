import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

import type { ChildJourneyStage, ChildMissionSession } from './types';

const stageOrder: ChildJourneyStage[] = ['READY', 'RIGHT', 'LEFT', 'STRAIGHT', 'STOP', 'ARRIVED'];

type ChildJourneyContextValue = {
  stage: ChildJourneyStage;
  session: ChildMissionSession | null;
  advance: () => void;
  setSession: (session: ChildMissionSession) => void;
  setStage: (stage: ChildJourneyStage) => void;
  reset: () => void;
};

const ChildJourneyContext = createContext<ChildJourneyContextValue | null>(null);

export function ChildJourneyProvider({ children }: PropsWithChildren) {
  const [stage, setStage] = useState<ChildJourneyStage>('READY');
  const [session, setSession] = useState<ChildMissionSession | null>(null);

  const value = useMemo(
    () => ({
      stage,
      session,
      setSession,
      setStage,
      advance: () => setStage((current) => stageOrder[Math.min(stageOrder.indexOf(current) + 1, stageOrder.length - 1)]),
      reset: () => setStage('READY'),
    }),
    [session, stage],
  );

  return <ChildJourneyContext.Provider value={value}>{children}</ChildJourneyContext.Provider>;
}

export function useChildJourney() {
  const context = useContext(ChildJourneyContext);
  if (!context) throw new Error('useChildJourney must be used within ChildJourneyProvider');
  return context;
}
