import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

import type { CreateMissionResult, MissionDraft } from './types';

const initialDraft: MissionDraft = {
  destination: { name: '행복 슈퍼', distance: '420m', duration: '도보 약 6분' },
  item: { id: 'milk-1l', name: '우유', brand: '서울 우유 1L', quantity: 1, unit: '개', verified: false },
  shareLocation: true,
  notifyOffRoute: true,
};

type MissionDraftContextValue = {
  draft: MissionDraft;
  result: CreateMissionResult | null;
  setQuantity: (quantity: number) => void;
  toggleShareLocation: () => void;
  toggleNotifyOffRoute: () => void;
  setResult: (result: CreateMissionResult) => void;
  reset: () => void;
};

const MissionDraftContext = createContext<MissionDraftContextValue | null>(null);

export function MissionDraftProvider({ children }: PropsWithChildren) {
  const [draft, setDraft] = useState(initialDraft);
  const [result, setResult] = useState<CreateMissionResult | null>(null);

  const value = useMemo<MissionDraftContextValue>(
    () => ({
      draft,
      result,
      setQuantity: (quantity) =>
        setDraft((current) => ({ ...current, item: { ...current.item, quantity: Math.max(1, quantity) } })),
      toggleShareLocation: () => setDraft((current) => ({ ...current, shareLocation: !current.shareLocation })),
      toggleNotifyOffRoute: () =>
        setDraft((current) => ({ ...current, notifyOffRoute: !current.notifyOffRoute })),
      setResult,
      reset: () => {
        setDraft(initialDraft);
        setResult(null);
      },
    }),
    [draft, result],
  );

  return <MissionDraftContext.Provider value={value}>{children}</MissionDraftContext.Provider>;
}

export function useMissionDraft() {
  const context = useContext(MissionDraftContext);
  if (!context) throw new Error('useMissionDraft must be used within MissionDraftProvider');
  return context;
}
