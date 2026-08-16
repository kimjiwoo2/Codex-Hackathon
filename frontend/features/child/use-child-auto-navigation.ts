import type * as Location from 'expo-location';
import { useEffect, useRef } from 'react';

import type { ChildJourneyStage } from './types';

type Coordinate = { latitude: number; longitude: number };
type Checkpoint = { eastMeters: number; northMeters: number; stage: ChildJourneyStage };

const checkpointRadiusMeters = 15;
const checkpoints: Checkpoint[] = [
  { eastMeters: 20, northMeters: 0, stage: 'RIGHT' },
  { eastMeters: 20, northMeters: 20, stage: 'LEFT' },
  { eastMeters: 0, northMeters: 20, stage: 'STRAIGHT' },
  { eastMeters: 0, northMeters: 40, stage: 'STOP' },
  { eastMeters: 0, northMeters: 60, stage: 'ARRIVED' },
];

const stageCheckpointIndex: Partial<Record<ChildJourneyStage, number>> = {
  READY: 0,
  RIGHT: 1,
  LEFT: 2,
  STRAIGHT: 3,
  STOP: 4,
};

function offsetCoordinate(origin: Coordinate, checkpoint: Checkpoint): Coordinate {
  const latitudeRadians = origin.latitude * (Math.PI / 180);
  return {
    latitude: origin.latitude + checkpoint.northMeters / 111_320,
    longitude: origin.longitude + checkpoint.eastMeters / (111_320 * Math.cos(latitudeRadians)),
  };
}

function distanceMeters(from: Coordinate, to: Coordinate) {
  const earthRadiusMeters = 6_371_000;
  const toRadians = (degrees: number) => degrees * (Math.PI / 180);
  const latitudeDelta = toRadians(to.latitude - from.latitude);
  const longitudeDelta = toRadians(to.longitude - from.longitude);
  const fromLatitude = toRadians(from.latitude);
  const toLatitude = toRadians(to.latitude);
  const a =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(fromLatitude) * Math.cos(toLatitude) * Math.sin(longitudeDelta / 2) ** 2;
  return 2 * earthRadiusMeters * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function useChildAutoNavigation({
  location,
  stage,
  setStage,
}: {
  location: Location.LocationObject | null;
  stage: ChildJourneyStage;
  setStage: (stage: ChildJourneyStage) => void;
}) {
  const originRef = useRef<Coordinate | null>(null);

  useEffect(() => {
    if (!location) return;

    const accuracy = location.coords.accuracy ?? Number.POSITIVE_INFINITY;
    if (accuracy > 50) return;

    const current = { latitude: location.coords.latitude, longitude: location.coords.longitude };
    if (!originRef.current) {
      originRef.current = current;
      return;
    }

    const checkpointIndex = stageCheckpointIndex[stage];
    if (checkpointIndex === undefined) return;

    const checkpoint = checkpoints[checkpointIndex];
    const target = offsetCoordinate(originRef.current, checkpoint);
    if (distanceMeters(current, target) <= checkpointRadiusMeters) setStage(checkpoint.stage);
  }, [location, setStage, stage]);
}
