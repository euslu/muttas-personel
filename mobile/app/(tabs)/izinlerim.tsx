import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  Platform,
  TouchableOpacity,
  Modal,
  ScrollView,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { api, IzinItem, DURUM_ETIKET, DURUM_RENK, IZIN_TURU_ETIKET } from "@/lib/api";

function formatTarih(tarih: string) {
  if (!tarih) return "";
  return new Date(tarih).toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

const DURUM_FILTRE = [
  { kod: "", ad: "Tümü" },
  { kod: "beklemede", ad: "Beklemede" },
  { kod: "ik_onayladi", ad: "İK Onayladı" },
  { kod: "mudur_onayladi", ad: "Müdür Onayladı" },
  { kod: "onaylandi", ad: "Onaylandı" },
  { kod: "reddedildi", ad: "Reddedildi" },
  { kod: "tamamlandi", ad: "Tamamlandı" },
];

export default function Izinlerim() {
  const insets = useSafeAreaInsets();
  const [secilenDurum, setSecilenDurum] = useState("");
  const [secilenIzin, setSecilenIzin] = useState<IzinItem | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["/izinler", secilenDurum],
    queryFn: () =>
      api.get<{ veri: IzinItem[]; toplam: number }>("/izinler", {
        durum: secilenDurum || undefined,
        per_page: 50,
      }),
    select: (d) => d.veri,
  });

  const paddingTop = Platform.OS === "web" ? 67 : insets.top;

  return (
    <View style={[styles.root, { paddingTop }]}>
      <View style={styles.header}>
        <Text style={styles.pageTitle}>İzinlerim</Text>
        <Text style={styles.pageSubTitle}>{data?.length ?? 0} kayıt</Text>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filtreScroll}
        style={styles.filtreBar}
      >
        {DURUM_FILTRE.map((f) => (
          <TouchableOpacity
            key={f.kod}
            style={[styles.filtrePill, secilenDurum === f.kod && styles.filtrePillActive]}
            onPress={() => setSecilenDurum(f.kod)}
          >
            <Text style={[styles.filtrePillText, secilenDurum === f.kod && styles.filtrePillTextActive]}>
              {f.ad}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <FlatList
        data={data ?? []}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refetch} tintColor="#1a56db" />
        }
        scrollEnabled={!!(data && data.length > 0)}
        ListEmptyComponent={
          !isLoading ? (
            <View style={styles.emptyBox}>
              <Ionicons name="calendar-outline" size={40} color="#cbd5e1" />
              <Text style={styles.emptyText}>Bu kategoride izin bulunamadı</Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.izinCard}
            onPress={() => setSecilenIzin(item)}
          >
            <View style={styles.izinCardLeft}>
              <View style={[styles.durumBar, { backgroundColor: DURUM_RENK[item.durum] }]} />
              <View style={styles.izinCardBody}>
                <Text style={styles.izinTuru}>
                  {IZIN_TURU_ETIKET[item.izin_turu] ?? item.izin_turu}
                </Text>
                <Text style={styles.izinTarih}>
                  {formatTarih(item.baslangic)} – {formatTarih(item.bitis)}
                </Text>
                <View style={styles.izinFooter}>
                  <View style={[styles.durumBadge, { backgroundColor: DURUM_RENK[item.durum] + "22" }]}>
                    <Text style={[styles.durumText, { color: DURUM_RENK[item.durum] }]}>
                      {DURUM_ETIKET[item.durum] ?? item.durum}
                    </Text>
                  </View>
                  <Text style={styles.izinGun}>{item.gun_sayisi} gün</Text>
                </View>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#cbd5e1" />
          </TouchableOpacity>
        )}
      />

      <Modal
        visible={!!secilenIzin}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setSecilenIzin(null)}
      >
        {secilenIzin && (
          <View style={styles.modal}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {IZIN_TURU_ETIKET[secilenIzin.izin_turu] ?? secilenIzin.izin_turu}
              </Text>
              <TouchableOpacity onPress={() => setSecilenIzin(null)}>
                <Ionicons name="close" size={24} color="#475569" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <View style={[styles.durumBannerFull, { backgroundColor: DURUM_RENK[secilenIzin.durum] + "15" }]}>
                <View style={[styles.durumDot, { backgroundColor: DURUM_RENK[secilenIzin.durum] }]} />
                <Text style={[styles.durumBannerText, { color: DURUM_RENK[secilenIzin.durum] }]}>
                  {DURUM_ETIKET[secilenIzin.durum] ?? secilenIzin.durum}
                </Text>
              </View>

              {[
                ["Başlangıç Tarihi", formatTarih(secilenIzin.baslangic)],
                ["Bitiş Tarihi", formatTarih(secilenIzin.bitis)],
                ["Toplam Gün", `${secilenIzin.gun_sayisi} gün`],
                ["Birim", secilenIzin.bolum],
                ["Oluşturma", formatTarih(secilenIzin.olusturuldu)],
              ].map(([key, val]) => (
                <View key={key} style={styles.detayRow}>
                  <Text style={styles.detayKey}>{key}</Text>
                  <Text style={styles.detayVal}>{val}</Text>
                </View>
              ))}

              {secilenIzin.aciklama ? (
                <View style={styles.detayRow}>
                  <Text style={styles.detayKey}>Açıklama</Text>
                  <Text style={[styles.detayVal, { flex: 1 }]}>{secilenIzin.aciklama}</Text>
                </View>
              ) : null}

              {secilenIzin.ret_nedeni ? (
                <View style={[styles.detayRow, { backgroundColor: "#fef2f2", borderRadius: 12, padding: 14, marginTop: 8 }]}>
                  <View>
                    <Text style={[styles.detayKey, { color: "#ef4444" }]}>Red Nedeni</Text>
                    <Text style={[styles.detayVal, { color: "#991b1b", marginTop: 4 }]}>{secilenIzin.ret_nedeni}</Text>
                  </View>
                </View>
              ) : null}
            </ScrollView>
          </View>
        )}
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f1f5f9" },
  header: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 8 },
  pageTitle: { fontSize: 24, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  pageSubTitle: { fontSize: 13, color: "#64748b", fontFamily: "Inter_400Regular", marginTop: 2 },
  filtreBar: { flexGrow: 0, marginBottom: 8 },
  filtreScroll: { paddingHorizontal: 20, gap: 8, paddingBottom: 8 },
  filtrePill: {
    paddingHorizontal: 14, paddingVertical: 8,
    borderRadius: 20, backgroundColor: "#fff",
    borderWidth: 1.5, borderColor: "#e2e8f0",
  },
  filtrePillActive: { backgroundColor: "#1a56db", borderColor: "#1a56db" },
  filtrePillText: { fontSize: 13, color: "#475569", fontFamily: "Inter_500Medium" },
  filtrePillTextActive: { color: "#fff", fontFamily: "Inter_600SemiBold" },
  listContent: { paddingHorizontal: 20, paddingTop: 4, paddingBottom: 32 },
  emptyBox: {
    alignItems: "center", justifyContent: "center",
    padding: 48, gap: 12,
  },
  emptyText: { fontSize: 14, color: "#94a3b8", fontFamily: "Inter_400Regular" },
  izinCard: {
    backgroundColor: "#fff", borderRadius: 16, marginBottom: 10,
    flexDirection: "row", alignItems: "center",
    shadowColor: "#000", shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 1,
    overflow: "hidden", paddingRight: 16,
  },
  izinCardLeft: { flexDirection: "row", flex: 1, alignItems: "center" },
  durumBar: { width: 4, alignSelf: "stretch" },
  izinCardBody: { flex: 1, padding: 16 },
  izinTuru: { fontSize: 15, fontWeight: "600", color: "#1e293b", fontFamily: "Inter_600SemiBold", marginBottom: 4 },
  izinTarih: { fontSize: 13, color: "#64748b", fontFamily: "Inter_400Regular", marginBottom: 8 },
  izinFooter: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  durumBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 20 },
  durumText: { fontSize: 11, fontWeight: "600", fontFamily: "Inter_600SemiBold" },
  izinGun: { fontSize: 13, color: "#475569", fontFamily: "Inter_600SemiBold" },
  modal: { flex: 1, backgroundColor: "#f8fafc" },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: "#cbd5e1", alignSelf: "center", marginTop: 12 },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  modalBody: { flex: 1, paddingHorizontal: 20 },
  durumBannerFull: {
    flexDirection: "row", alignItems: "center", gap: 8,
    padding: 14, borderRadius: 12, marginBottom: 16,
  },
  durumDot: { width: 10, height: 10, borderRadius: 5 },
  durumBannerText: { fontSize: 14, fontWeight: "600", fontFamily: "Inter_600SemiBold" },
  detayRow: {
    flexDirection: "row", justifyContent: "space-between",
    paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: "#f1f5f9",
  },
  detayKey: { fontSize: 14, color: "#64748b", fontFamily: "Inter_400Regular" },
  detayVal: { fontSize: 14, color: "#1e293b", fontFamily: "Inter_600SemiBold", textAlign: "right" },
});
