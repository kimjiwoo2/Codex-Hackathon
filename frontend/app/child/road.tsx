import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Speech from 'expo-speech';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, type AppStateStatus, Pressable, StyleSheet, Text, View } from 'react-native';

import { PrimaryButton } from '@/components/ican/primary-button';
import { Screen } from '@/components/ican/screen';
import { ICanColors } from '@/constants/ican-theme';
import { useChildMission } from '@/features/mission/child-mission-context';
import { jpegByteLength, roadFailureFromStatus, roadSafetyFailureGuidance, roadSafetyGuidance, type RoadSafetyGuidance } from '@/features/road-vision/safety';
import { ChildApiError, uploadRoadFrame } from '@/services/child-mission-api';

const CADENCE_MS = 4_000;
const MAX_JPEG_BYTES = 1_000_000;

export default function ChildRoadScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraReady, setCameraReady] = useState(false);
  const [guidance, setGuidance] = useState<RoadSafetyGuidance>(() => roadSafetyFailureGuidance('unknown'));
  const camera = useRef<CameraView>(null);
  const inFlight = useRef(false);
  const lastUploadAt = useRef(0);
  const appState = useRef<AppStateStatus>(AppState.currentState);
  const { session } = useChildMission();

  const announce = useCallback((next: RoadSafetyGuidance) => {
    setGuidance(next);
    Speech.stop();
    Speech.speak(next.message, { language: 'ko-KR', rate: 0.92 });
  }, []);

  const captureAndUpload = useCallback(async (force = false) => {
    if (!session || !camera.current || !cameraReady || inFlight.current || appState.current !== 'active') return;
    if (!force && Date.now() - lastUploadAt.current < CADENCE_MS) return;
    inFlight.current = true;
    lastUploadAt.current = Date.now();
    try {
      let frame = await camera.current.takePictureAsync({ base64: true, quality: 0.2 });
      if (!frame.base64 || jpegByteLength(frame.base64) > MAX_JPEG_BYTES) {
        frame = await camera.current.takePictureAsync({ base64: true, quality: 0.05 });
      }
      if (!frame.base64 || jpegByteLength(frame.base64) > MAX_JPEG_BYTES) {
        announce(roadSafetyFailureGuidance('invalid-frame'));
        return;
      }
      if (appState.current !== 'active') return;
      const result = await uploadRoadFrame(session, { base64: frame.base64, capturedAt: new Date().toISOString(), uri: frame.uri });
      announce(roadSafetyGuidance(result));
    } catch (cause) {
      announce(roadSafetyFailureGuidance(cause instanceof ChildApiError ? roadFailureFromStatus(cause.status) : 'network'));
    } finally { inFlight.current = false; }
  }, [announce, cameraReady, session]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextState) => { appState.current = nextState; });
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    if (!permission?.granted || !session) return;
    const interval = setInterval(() => { void captureAndUpload(); }, 500);
    void captureAndUpload();
    return () => clearInterval(interval);
  }, [captureAndUpload, permission?.granted, session]);

  if (!session) {
    return <Screen contentStyle={styles.center}><Text style={styles.title}>참여 코드부터 입력해요</Text><PrimaryButton label="참여 코드 입력" onPress={() => router.replace('/child')} /></Screen>;
  }
  if (!permission) return <Screen contentStyle={styles.center}><Text style={styles.message}>카메라를 준비하고 있어요.</Text></Screen>;
  if (!permission.granted) {
    return <Screen contentStyle={styles.center}><Text style={styles.title}>카메라 권한이 필요해요</Text><Text style={styles.message}>권한을 허용할 수 없으면 멈춰서 주변을 살피고 보호자와 함께 직접 확인하세요.</Text><PrimaryButton label="카메라 권한 허용" onPress={() => void requestPermission()} /></Screen>;
  }

  return (
    <View style={styles.cameraScreen}>
      <CameraView facing="back" onCameraReady={() => setCameraReady(true)} ref={camera} style={StyleSheet.absoluteFill} />
      <View style={styles.overlay}>
        <Text style={styles.eyebrow}>이동 중 안전 확인</Text>
        <Text style={styles.safetyTitle}>{guidance.title}</Text>
        <Text accessibilityLiveRegion="polite" style={styles.safetyMessage}>{guidance.message}</Text>
        <Text style={styles.notice}>카메라는 4초마다 JPEG 한 장만 확인해요.</Text>
        <Pressable accessibilityRole="button" onPress={() => void captureAndUpload(true)} style={styles.checkButton}><Text style={styles.checkText}>지금 다시 확인</Text></Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  cameraScreen: { backgroundColor: ICanColors.ink, flex: 1 },
  overlay: { backgroundColor: 'rgba(20, 21, 23, 0.84)', bottom: 0, padding: 24, paddingBottom: 38, position: 'absolute', width: '100%' },
  eyebrow: { color: ICanColors.lime, fontSize: 14, fontWeight: '700' },
  safetyTitle: { color: ICanColors.paper, fontSize: 27, fontWeight: '700', marginTop: 8 },
  safetyMessage: { color: ICanColors.paper, fontSize: 17, lineHeight: 25, marginTop: 9 },
  notice: { color: '#D2D4D6', fontSize: 13, marginTop: 14 },
  checkButton: { alignItems: 'center', backgroundColor: ICanColors.yellow, borderRadius: 12, marginTop: 20, padding: 15 },
  checkText: { color: ICanColors.ink, fontSize: 16, fontWeight: '700' },
  center: { alignItems: 'center', flex: 1, gap: 18, justifyContent: 'center', padding: 24 },
  title: { color: ICanColors.ink, fontSize: 24, fontWeight: '700', textAlign: 'center' },
  message: { color: ICanColors.muted, fontSize: 16, lineHeight: 24, textAlign: 'center' },
});
