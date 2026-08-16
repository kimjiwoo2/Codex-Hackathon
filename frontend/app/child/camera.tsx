import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Speech from 'expo-speech';
import { router } from 'expo-router';
import { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';
import { useChildJourney } from '@/features/child/child-journey-context';
import { useChildMission } from '@/features/child/child-mission-context';
import type { ItemVerificationResult } from '@/features/mission/types';
import { childMissionApi, MissionAdapterError } from '@/services/mission-adapter';

const verdictCopy: Record<ItemVerificationResult['verdict'], string> = {
  MATCH: '찾았어요! 이제 집으로 돌아가요.',
  SIMILAR: '비슷한 상품이에요. 이름과 용량을 다시 보고 다시 찍어 주세요.',
  MISMATCH: '다른 상품이에요. 찾는 물건을 다시 찍어 주세요.',
  UNKNOWN: '잘 보이지 않아요. 밝은 곳에서 다시 찍어 주세요.',
};

export default function ChildCameraScreen() {
  const camera = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [result, setResult] = useState<ItemVerificationResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setStage } = useChildJourney();
  const { applyVerification, selectedItem, session, startReturning } = useChildMission();

  if (!session || !selectedItem) {
    router.replace('/child/join');
    return null;
  }

  const capture = async () => {
    let image = await camera.current?.takePictureAsync({ exif: false, quality: 0.35 });
    if (!image) return;
    setUploading(true);
    setError(null);
    try {
      let verification: ItemVerificationResult;
      try {
        verification = await childMissionApi.verifyItem(
          session.missionId,
          selectedItem.itemId,
          session.childToken,
          image.uri,
        );
      } catch (reason) {
        if (!(reason instanceof MissionAdapterError) || reason.code !== 'INVALID_ITEM_IMAGE') throw reason;
        image = await camera.current?.takePictureAsync({ exif: false, quality: 0.05 });
        if (!image) throw reason;
        verification = await childMissionApi.verifyItem(
          session.missionId,
          selectedItem.itemId,
          session.childToken,
          image.uri,
        );
      }
      applyVerification(verification);
      Speech.stop();
      Speech.speak(verification.message, { language: 'ko-KR', rate: 0.92 });
      setResult(verification);
    } catch (reason) {
      if (reason instanceof MissionAdapterError && reason.status === 409) {
        startReturning();
        finishReturning();
        return;
      }
      setError(reason instanceof Error ? reason.message : '상품 확인에 실패했어요. 다시 시도해 주세요.');
    } finally {
      setUploading(false);
    }
  };

  const finishReturning = () => {
    setStage('RETURNING');
    router.replace('/child');
  };

  if (!permission) return <View style={styles.permissionScreen} />;

  if (!permission.granted) {
    return (
      <View style={styles.permissionScreen}>
        <View style={styles.permissionCard}>
          <Ionicons color={ICanColors.greenDark} name="camera" size={54} />
          <Text style={styles.permissionTitle}>{selectedItem.name}을 카메라로 확인해요</Text>
          <Text style={styles.permissionCopy}>심부름 물건을 비추려면 카메라 권한이 필요해요.</Text>
          <Pressable accessibilityRole="button" onPress={requestPermission} style={styles.permissionButton}>
            <Text style={styles.permissionButtonText}>카메라 허용하기</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  if (result) {
    const matches = result.verdict === 'MATCH' && result.status === 'RETURNING';
    const matchedButMoreRemain = result.verdict === 'MATCH' && result.status === 'SHOPPING';
    return (
      <View style={styles.permissionScreen}>
        <View style={styles.permissionCard}>
          <Text style={styles.permissionTitle}>{verdictCopy[result.verdict]}</Text>
          <Text style={styles.permissionCopy}>{result.message}</Text>
          {result.detectedLabel && <Text style={styles.detected}>{result.detectedLabel}</Text>}
          <Pressable
            accessibilityRole="button"
            onPress={() => {
              if (matches) {
                finishReturning();
                return;
              }
              if (matchedButMoreRemain) {
                router.replace('/child');
                return;
              }
              setResult(null);
            }}
            style={styles.permissionButton}>
            <Text style={styles.permissionButtonText}>
              {matches ? '귀가 안내 보기' : matchedButMoreRemain ? '다음 물건 보기' : '다시 촬영하기'}
            </Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.cameraScreen}>
      <CameraView facing="back" ref={camera} style={StyleSheet.absoluteFillObject} />
      <View style={styles.cameraHeader}>
        <Pressable accessibilityLabel="뒤로 가기" hitSlop={10} onPress={() => router.back()}>
          <Ionicons color={ICanColors.paper} name="chevron-back" size={30} />
        </Pressable>
        <Text style={styles.cameraTitle}>{selectedItem.name}을 화면 안에 맞춰주세요</Text>
        <View style={styles.headerSpacer} />
      </View>
      <View style={styles.guideFrame} />
      <View style={styles.cameraFooter}>
        <Text style={styles.cameraHint}>사진으로 물건이 맞는지 확인할게요.</Text>
        {error && <Text accessibilityLiveRegion="polite" style={styles.error}>{error}</Text>}
        <Pressable accessibilityLabel="물건 촬영하기" disabled={uploading} onPress={capture} style={styles.shutter}>
          <View style={styles.shutterInner} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  cameraScreen: { backgroundColor: '#111', flex: 1 },
  cameraHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 54 },
  cameraTitle: { color: ICanColors.paper, fontSize: 17, fontWeight: '700' },
  headerSpacer: { width: 30 },
  guideFrame: { borderColor: ICanColors.yellow, borderRadius: 20, borderWidth: 4, height: 330, left: 42, position: 'absolute', right: 42, top: 190 },
  cameraFooter: { alignItems: 'center', bottom: 52, left: 0, position: 'absolute', right: 0 },
  cameraHint: { color: ICanColors.paper, fontSize: 15, marginBottom: 22 },
  shutter: { alignItems: 'center', borderColor: ICanColors.paper, borderRadius: 38, borderWidth: 4, height: 76, justifyContent: 'center', width: 76 },
  shutterInner: { backgroundColor: ICanColors.yellow, borderRadius: 29, height: 58, width: 58 },
  permissionScreen: { alignItems: 'center', backgroundColor: '#FFF9E9', flex: 1, justifyContent: 'center', padding: 28 },
  permissionCard: { alignItems: 'center', backgroundColor: ICanColors.paper, borderColor: '#FDE6AD', borderRadius: 20, borderWidth: 3, padding: 28, width: '100%' },
  permissionTitle: { color: ICanColors.ink, fontSize: 22, fontWeight: '800', marginTop: 18 },
  permissionCopy: { color: ICanColors.muted, fontSize: 14, lineHeight: 21, marginTop: 8, textAlign: 'center' },
  permissionButton: { alignItems: 'center', backgroundColor: ICanColors.yellow, borderRadius: 8, height: 52, justifyContent: 'center', marginTop: 24, width: '100%' },
  permissionButtonText: { color: ICanColors.paper, fontSize: 17, fontWeight: '700' },
  detected: { color: ICanColors.greenDark, fontSize: 14, fontWeight: '700', marginTop: 12 },
  error: { color: ICanColors.paper, fontSize: 14, marginBottom: 12, textAlign: 'center' },
});
