import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

import type { CreateMissionResult, JoinMissionResult, MissionDraft } from './types';

const initialDraft: MissionDraft = {
  home: { latitude: 37.5662952, longitude: 126.9779451 },
  store: { latitude: 37.567197, longitude: 126.979167 },
  destination: { name: '행복 슈퍼', distance: '420m', duration: '도보 약 6분' },
  item: {
    id: 'milk-1l',
    name: '우유',
    brand: '서울우유',
    quantity: 1,
    unit: '개',
    size: '1L',
    verified: false,
  },
  shareLocation: true,
  notifyOffRoute: true,
};

type MissionDraftContextValue = {
  draft: MissionDraft;
  createResult: CreateMissionResult | null;
  joinResult: JoinMissionResult | null;
  setQuantity: (quantity: number) => void;
  toggleShareLocation: () => void;
  toggleNotifyOffRoute: () => void;
  setCreateResult: (result: CreateMissionResult | null) => void;
  setJoinResult: (result: JoinMissionResult | null) => void;
  reset: () => void;
};

const MissionDraftContext = createContext<MissionDraftContextValue | null>(null);

export function MissionDraftProvider({ children }: PropsWithChildren) {
  const [draft, setDraft] = useState(initialDraft);
  const [createResult, setCreateResult] = useState<CreateMissionResult | null>(null);
  const [joinResult, setJoinResult] = useState<JoinMissionResult | null>(null);

  const value = useMemo<MissionDraftContextValue>(
    () => ({
      draft,
      createResult,
      joinResult,
      setQuantity: (quantity) =>
        setDraft((current) => ({ ...current, item: { ...current.item, quantity: Math.max(1, quantity) } })),
      toggleShareLocation: () => setDraft((current) => ({ ...current, shareLocation: !current.shareLocation })),
      toggleNotifyOffRoute: () =>
        setDraft((current) => ({ ...current, notifyOffRoute: !current.notifyOffRoute })),
      setCreateResult,
      setJoinResult,
      reset: () => {
        setDraft(initialDraft);
        setCreateResult(null);
        setJoinResult(null);
      },
    }),
    [createResult, draft, joinResult],
  );

  return <MissionDraftContext.Provider value={value}>{children}</MissionDraftContext.Provider>;
}

export function useMissionDraft() {
  const context = useContext(MissionDraftContext);
  if (!context) throw new Error('useMissionDraft must be used within MissionDraftProvider');
  return context;
}
