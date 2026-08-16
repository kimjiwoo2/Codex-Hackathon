import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

import type { ItemVerificationResult, JoinMissionResult, MissionItemDto } from '@/features/mission/types';

type ChildMissionContextValue = {
  session: JoinMissionResult | null;
  selectedItem: MissionItemDto | null;
  applyVerification: (result: ItemVerificationResult) => void;
  startReturning: () => void;
  join: (session: JoinMissionResult) => void;
  reset: () => void;
};

const ChildMissionContext = createContext<ChildMissionContextValue | null>(null);

export function ChildMissionProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<JoinMissionResult | null>(null);
  const [selectedItem, setSelectedItem] = useState<MissionItemDto | null>(null);
  const value = useMemo<ChildMissionContextValue>(() => ({
    session,
    selectedItem,
    join: (nextSession) => {
      setSession(nextSession);
      setSelectedItem(nextSession.items[0] ?? null);
    },
    applyVerification: (result) => {
      setSelectedItem((item) => item && { ...item, verdict: result.verdict, detectedLabel: result.detectedLabel });
      setSession((current) => current && { ...current, status: result.status });
    },
    startReturning: () => setSession((current) => current && { ...current, status: 'RETURNING' }),
    reset: () => {
      setSession(null);
      setSelectedItem(null);
    },
  }), [selectedItem, session]);
  return <ChildMissionContext.Provider value={value}>{children}</ChildMissionContext.Provider>;
}

export function useChildMission() {
  const context = useContext(ChildMissionContext);
  if (!context) throw new Error('useChildMission must be used within ChildMissionProvider');
  return context;
}
