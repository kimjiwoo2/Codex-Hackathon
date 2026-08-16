import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

import type { ItemVerificationResult, JoinMissionResult, MissionItemDto, MissionStatus } from '@/features/mission/types';

import { applyVerificationToMission, createChildMissionState, startReturningMission } from './child-mission-state';

type ChildMissionContextValue = {
  session: JoinMissionResult | null;
  selectedItem: MissionItemDto | null;
  applyVerification: (result: ItemVerificationResult) => void;
  startReturning: () => void;
  join: (session: JoinMissionResult) => void;
  updateStatus: (status: MissionStatus) => void;
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
      const nextState = createChildMissionState(nextSession);
      setSession(nextState.session);
      setSelectedItem(nextState.selectedItem);
    },
    applyVerification: (result) => {
      setSession((currentSession) => {
        const nextState = applyVerificationToMission(
          { session: currentSession, selectedItem },
          result,
        );
        setSelectedItem(nextState.selectedItem);
        return nextState.session;
      });
    },
    startReturning: () => {
      setSession((currentSession) => {
        const nextState = startReturningMission({ session: currentSession, selectedItem });
        setSelectedItem(nextState.selectedItem);
        return nextState.session;
      });
    },
    updateStatus: (status) => setSession((current) => (current ? { ...current, status } : current)),
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
