import { createContext, type PropsWithChildren, useContext, useMemo, useState } from 'react';

import type { ChildMissionSession } from '@/services/child-mission-api';

interface ChildMissionContextValue { session: ChildMissionSession | null; setSession: (session: ChildMissionSession | null) => void; }
const ChildMissionContext = createContext<ChildMissionContextValue | null>(null);

export function ChildMissionProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<ChildMissionSession | null>(null);
  const value = useMemo(() => ({ session, setSession }), [session]);
  return <ChildMissionContext.Provider value={value}>{children}</ChildMissionContext.Provider>;
}

export function useChildMission(): ChildMissionContextValue {
  const context = useContext(ChildMissionContext);
  if (!context) throw new Error('ChildMissionProvider 내부에서 사용해야 합니다.');
  return context;
}
