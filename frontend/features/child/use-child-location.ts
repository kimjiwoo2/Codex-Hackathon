import * as Location from 'expo-location';
import { useCallback, useEffect, useState } from 'react';

export type ChildLocationStatus = 'CHECKING' | 'TRACKING' | 'DENIED' | 'UNAVAILABLE' | 'ERROR';

export function useChildLocation() {
  const [status, setStatus] = useState<ChildLocationStatus>('CHECKING');
  const [location, setLocation] = useState<Location.LocationObject | null>(null);
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => setAttempt((current) => current + 1), []);

  useEffect(() => {
    let active = true;
    let subscription: Location.LocationSubscription | undefined;

    const startTracking = async () => {
      setStatus('CHECKING');

      const servicesEnabled = await Location.hasServicesEnabledAsync();
      if (!servicesEnabled) {
        if (active) setStatus('UNAVAILABLE');
        return;
      }

      let permission = await Location.getForegroundPermissionsAsync();
      if (!permission.granted && permission.canAskAgain) {
        permission = await Location.requestForegroundPermissionsAsync();
      }

      if (!permission.granted) {
        if (active) setStatus('DENIED');
        return;
      }

      subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.Balanced,
          distanceInterval: 10,
          timeInterval: 3000,
        },
        (nextLocation) => {
          if (!active) return;
          setLocation(nextLocation);
          setStatus('TRACKING');
        },
      );
    };

    startTracking().catch(() => {
      if (active) setStatus('ERROR');
    });

    return () => {
      active = false;
      subscription?.remove();
    };
  }, [attempt]);

  return { location, retry, status };
}
