import { Ionicons } from '@expo/vector-icons';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';
import type { ChildJourneyStage } from '@/features/child/types';

const directionIcon = {
  RIGHT: 'arrow-forward',
  LEFT: 'arrow-back',
  STRAIGHT: 'arrow-up',
} as const;

export function ChildMissionCard({
  stage,
  onAdvance,
  onOpenCamera,
  itemDetails = '서울 우유 1L',
  itemName = '우유 1개',
}: {
  stage: ChildJourneyStage;
  onAdvance?: () => void;
  onOpenCamera?: () => void;
  itemDetails?: string;
  itemName?: string;
}) {
  const arrived = stage === 'ARRIVED';
  const returning = stage === 'RETURNING';
  const direction = stage === 'RIGHT' || stage === 'LEFT' || stage === 'STRAIGHT' ? directionIcon[stage] : null;

  return (
    <View style={styles.card}>
      <View style={styles.titleRow}>
        <Text style={styles.missionTitle}>
          {arrived ? '우유를 찾아보자!' : returning ? '심부름 물건을 찾았네\n잘했어!' : '우유를 사러\n'}
          {!arrived && !returning && <Text style={styles.greenTitle}>행복 슈퍼</Text>}
          {!arrived && !returning && '로 가자!'}
        </Text>
        <Image resizeMode="contain" source={require('../../assets/ican/child-cart.png')} style={styles.cart} />
      </View>

      <View style={styles.itemCard}>
        <Image resizeMode="contain" source={require('../../assets/ican/milk.png')} style={styles.milk} />
        <View>
          <Text style={styles.itemName}>{itemName}</Text>
          <Text style={styles.itemMeta}>{itemDetails}</Text>
        </View>
      </View>

      <Pressable
        accessibilityHint="GPS 이동에 따라 자동으로 바뀌며, 데모에서는 눌러서 다음 단계로 이동할 수 있습니다"
        accessibilityLabel="지도에서 다음 길 안내 보기"
        accessibilityRole="button"
        disabled={arrived}
        onPress={onAdvance}
        style={[styles.mapWrap, arrived && styles.arrivedMap]}>
        <Image resizeMode="cover" source={require('../../assets/ican/route-summary.png')} style={styles.map} />
        {direction && (
          <View style={styles.directionOverlay}>
            <Ionicons color="rgba(255,84,93,0.72)" name={direction} size={176} />
          </View>
        )}
        {stage === 'STOP' && (
          <View style={styles.warningOverlay}>
            <Ionicons color="rgba(255,84,93,0.76)" name="warning" size={154} />
          </View>
        )}
        {!arrived && (
          <View pointerEvents="none" style={styles.mapHint}>
            <Ionicons color={ICanColors.paper} name="navigate" size={18} />
            <Text style={styles.mapHintText}>
              {returning ? 'GPS 귀가 안내 · 눌러서 데모 완료' : 'GPS 자동 안내 · 눌러서 데모 진행'}
            </Text>
          </View>
        )}
      </Pressable>

      {arrived && (
        <Pressable accessibilityRole="button" onPress={onOpenCamera} style={styles.cameraButton}>
          <Ionicons color={ICanColors.paper} name="camera" size={21} />
          <Text style={styles.cameraButtonText}>카메라로 물건 확인하기</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: ICanColors.paper,
    borderColor: '#FDE6AD',
    borderRadius: 20,
    borderWidth: 3,
    alignSelf: 'center',
    minHeight: 528,
    padding: 18,
    width: 336,
  },
  titleRow: { height: 100, justifyContent: 'center' },
  missionTitle: { color: ICanColors.ink, fontSize: 25, fontWeight: '800', lineHeight: 35 },
  greenTitle: { color: '#50B748' },
  cart: { height: 88, position: 'absolute', right: -4, top: 0, width: 112 },
  itemCard: { alignItems: 'center', backgroundColor: ICanColors.canvas, borderRadius: 10, flexDirection: 'row', height: 114, paddingHorizontal: 22 },
  milk: { height: 86, marginRight: 10, width: 75 },
  itemName: { color: ICanColors.ink, fontSize: 18, fontWeight: '600' },
  itemMeta: { color: 'rgba(20,21,23,0.38)', fontSize: 13, marginTop: 6 },
  mapWrap: { borderRadius: 10, height: 240, marginTop: 24, overflow: 'hidden', width: '100%' },
  arrivedMap: { height: 170 },
  map: { height: '100%', width: '100%' },
  directionOverlay: { alignItems: 'center', bottom: 0, justifyContent: 'center', left: 0, position: 'absolute', right: 0, top: 0 },
  warningOverlay: { alignItems: 'center', bottom: 0, justifyContent: 'center', left: 0, position: 'absolute', right: 0, top: 0 },
  mapHint: {
    alignItems: 'center',
    alignSelf: 'center',
    backgroundColor: 'rgba(20,21,23,0.78)',
    borderRadius: 18,
    bottom: 12,
    flexDirection: 'row',
    paddingHorizontal: 14,
    paddingVertical: 8,
    position: 'absolute',
  },
  mapHintText: { color: ICanColors.paper, fontSize: 13, fontWeight: '700', marginLeft: 6 },
  cameraButton: { alignItems: 'center', backgroundColor: ICanColors.yellow, borderRadius: 8, flexDirection: 'row', height: 55, justifyContent: 'center', marginTop: 24 },
  cameraButtonText: { color: ICanColors.paper, fontSize: 18, fontWeight: '600', marginLeft: 8 },
});
