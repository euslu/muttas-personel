import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  Platform,
  TouchableOpacity,
  Alert,
  Modal,
  ScrollView,
  TextInput,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/lib/auth";
import { api, IzinItem, DURUM_ETIKET, DURUM_RENK, IZIN_TURU_ETIKET } from "@/lib/api";

function formatTarih(tarih: string) {
  if (!tarih) return "";
  return new Date(tarih).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" });
}

export default function Onaylar() {
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const [secilenIzin, setSecilenIzin] = useState<IzinItem | null>(null);
  const [retNedeni, setRetNedeni] = useState("");
  const [retModal, setRetModal] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["/izinler/onay"],
    queryFn: () =>
      api.get<{ veri: IzinItem[] }>("/izinler", { durum: "beklemede", per_page: 50 }),
    select: (d) => d.veri,
  });

  const { user } = useAuth();

  function onayDurumu(): string {
    switch (user?.rol) {
      case "ik_admin":
      case "admin": return "ik_onayladi";
      case "genel_mudur": return "mudur_onayladi";
      case "yk_uyesi":
      case "yk_baskani": return "onaylandi";
      default: return "";
    }
  }

  const canApproveViaOnay = ["admin", "ik_admin", "genel_mudur", "yk_uyesi", "yk_baskani"].includes(user?.rol ?? "") && !!onayDurumu();

  const { mutate: onayla, isPending: onayPending } = useMutation({
    mutationFn: (id: number) =>
      api.put(`/izinler/${id}/onay`, { durum: onayDurumu() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/izinler/onay"] });
      queryClient.invalidateQueries({ queryKey: ["/izinler/son"] });
      setSecilenIzin(null);
      Alert.alert("Başarılı", "İzin talebi onaylandı.");
    },
    onError: (e: Error) => Alert.alert("Hata", e.message),
  });

  const { mutate: reddet, isPending: retPending } = useMutation({
    mutationFn: ({ id, neden }: { id: number; neden: string }) =>
      api.put(`/izinler/${id}/onay`, { durum: "reddedildi", notlar: neden }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/izinler/onay"] });
      queryClient.invalidateQueries({ queryKey: ["/izinler/son"] });
      setSecilenIzin(null);
      setRetModal(false);
      setRetNedeni("");
      Alert.alert("Bilgi", "İzin talebi reddedildi.");
    },
    onError: (e: Error) => Alert.alert("Hata", e.message),
  });

  const paddingTop = Platform.OS === "web" ? 67 : insets.top;

  return (
    <View style={[styles.root, { paddingTop }]}>
      <View style={styles.header}>
        <Text style={styles.pageTitle}>Bekleyen Onaylar</Text>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>{data?.length ?? 0}</Text>
        </View>
      </View>

      <FlatList
        data={data ?? []}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.listContent}
        scrollEnabled={!!(data && data.length > 0)}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refetch} tintColor="#1a56db" />
        }
        ListEmptyComponent={
          !isLoading ? (
            <View style={styles.emptyBox}>
              <Ionicons name="checkmark-done-circle-outline" size={48} color="#10b981" />
              <Text style={styles.emptyTitle}>Bekleyen talep yok</Text>
              <Text style={styles.emptyText}>Tüm izin talepleri işlendi.</Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.izinCard} onPress={() => setSecilenIzin(item)}>
            <View style={styles.cardTop}>
              <Text style={styles.personelAd}>{item.ad_soyad}</Text>
              <Text style={styles.gunText}>{item.gun_sayisi} gün</Text>
            </View>
            <Text style={styles.birimText}>{item.bolum} · {item.unvan}</Text>
            <View style={styles.cardBottom}>
              <View style={styles.tarihRow}>
                <Ionicons name="calendar-outline" size={13} color="#64748b" />
                <Text style={styles.tarihText}>
                  {formatTarih(item.baslangic)} – {formatTarih(item.bitis)}
                </Text>
              </View>
              <View style={styles.turBadge}>
                <Text style={styles.turText}>{IZIN_TURU_ETIKET[item.izin_turu] ?? item.izin_turu}</Text>
              </View>
            </View>
          </TouchableOpacity>
        )}
      />

      <Modal
        visible={!!secilenIzin && !retModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setSecilenIzin(null)}
      >
        {secilenIzin && (
          <View style={styles.modal}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>İzin Talebi</Text>
              <TouchableOpacity onPress={() => setSecilenIzin(null)}>
                <Ionicons name="close" size={24} color="#475569" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <View style={styles.personelCard}>
                <View style={styles.avatarCircle}>
                  <Text style={styles.avatarText}>
                    {secilenIzin.ad_soyad?.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                  </Text>
                </View>
                <View>
                  <Text style={styles.personelAdModal}>{secilenIzin.ad_soyad}</Text>
                  <Text style={styles.personelBirim}>{secilenIzin.bolum}</Text>
                </View>
              </View>

              {[
                ["İzin Türü", IZIN_TURU_ETIKET[secilenIzin.izin_turu] ?? secilenIzin.izin_turu],
                ["Başlangıç", formatTarih(secilenIzin.baslangic)],
                ["Bitiş", formatTarih(secilenIzin.bitis)],
                ["Toplam", `${secilenIzin.gun_sayisi} gün`],
              ].map(([k, v]) => (
                <View key={k} style={styles.detayRow}>
                  <Text style={styles.detayKey}>{k}</Text>
                  <Text style={styles.detayVal}>{v}</Text>
                </View>
              ))}

              {secilenIzin.aciklama ? (
                <View style={styles.aciklamaBox}>
                  <Text style={styles.detayKey}>Açıklama</Text>
                  <Text style={styles.aciklamaText}>{secilenIzin.aciklama}</Text>
                </View>
              ) : null}

              {canApproveViaOnay && (
              <View style={styles.actionRow}>
                <TouchableOpacity
                  style={styles.redBtn}
                  onPress={() => setRetModal(true)}
                >
                  <Ionicons name="close-circle" size={20} color="#ef4444" />
                  <Text style={styles.redBtnText}>Reddet</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.onayBtn, onayPending && { opacity: 0.6 }]}
                  onPress={() => onayla(secilenIzin.id)}
                  disabled={onayPending}
                >
                  {onayPending ? (
                    <ActivityIndicator color="#fff" size="small" />
                  ) : (
                    <>
                      <Ionicons name="checkmark-circle" size={20} color="#fff" />
                      <Text style={styles.onayBtnText}>Onayla</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
              )}
            </ScrollView>
          </View>
        )}
      </Modal>

      <Modal
        visible={retModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => { setRetModal(false); setRetNedeni(""); }}
      >
        <View style={styles.modal}>
          <View style={styles.modalHandle} />
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Red Nedeni</Text>
            <TouchableOpacity onPress={() => { setRetModal(false); setRetNedeni(""); }}>
              <Ionicons name="close" size={24} color="#475569" />
            </TouchableOpacity>
          </View>
          <View style={styles.modalBody}>
            <Text style={styles.retLabel}>Neden belirtin (opsiyonel):</Text>
            <TextInput
              style={styles.retInput}
              value={retNedeni}
              onChangeText={setRetNedeni}
              placeholder="Red nedeni yazın..."
              placeholderTextColor="#94a3b8"
              multiline
              numberOfLines={4}
              textAlignVertical="top"
            />
            <TouchableOpacity
              style={[styles.redBtnFull, retPending && { opacity: 0.6 }]}
              onPress={() => secilenIzin && reddet({ id: secilenIzin.id, neden: retNedeni })}
              disabled={retPending}
            >
              {retPending ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.redBtnFullText}>Talebi Reddet</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f1f5f9" },
  header: {
    paddingHorizontal: 20, paddingTop: 16, paddingBottom: 12,
    flexDirection: "row", alignItems: "center", gap: 12,
  },
  pageTitle: { fontSize: 24, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  countBadge: {
    backgroundColor: "#ef4444", borderRadius: 12,
    paddingHorizontal: 8, paddingVertical: 2,
  },
  countText: { fontSize: 13, fontWeight: "700", color: "#fff", fontFamily: "Inter_700Bold" },
  listContent: { paddingHorizontal: 20, paddingBottom: 32 },
  emptyBox: { alignItems: "center", padding: 60, gap: 8 },
  emptyTitle: { fontSize: 16, fontWeight: "600", color: "#475569", fontFamily: "Inter_600SemiBold" },
  emptyText: { fontSize: 13, color: "#94a3b8", fontFamily: "Inter_400Regular" },
  izinCard: {
    backgroundColor: "#fff", borderRadius: 16, padding: 16,
    marginBottom: 10,
    shadowColor: "#000", shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 1,
  },
  cardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 4 },
  personelAd: { fontSize: 15, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  gunText: { fontSize: 14, fontWeight: "700", color: "#1a56db", fontFamily: "Inter_700Bold" },
  birimText: { fontSize: 12, color: "#64748b", fontFamily: "Inter_400Regular", marginBottom: 10 },
  cardBottom: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  tarihRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  tarihText: { fontSize: 12, color: "#64748b", fontFamily: "Inter_400Regular" },
  turBadge: {
    backgroundColor: "#eff6ff", borderRadius: 8,
    paddingHorizontal: 8, paddingVertical: 3,
  },
  turText: { fontSize: 11, color: "#1a56db", fontFamily: "Inter_600SemiBold" },
  modal: { flex: 1, backgroundColor: "#f8fafc" },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: "#cbd5e1", alignSelf: "center", marginTop: 12 },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  modalBody: { flex: 1, paddingHorizontal: 20 },
  personelCard: {
    flexDirection: "row", alignItems: "center", gap: 14,
    backgroundColor: "#fff", borderRadius: 16, padding: 16, marginBottom: 20,
  },
  avatarCircle: {
    width: 48, height: 48, borderRadius: 24,
    backgroundColor: "#1a56db", alignItems: "center", justifyContent: "center",
  },
  avatarText: { color: "#fff", fontSize: 16, fontWeight: "700", fontFamily: "Inter_700Bold" },
  personelAdModal: { fontSize: 16, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  personelBirim: { fontSize: 13, color: "#64748b", fontFamily: "Inter_400Regular" },
  detayRow: {
    flexDirection: "row", justifyContent: "space-between",
    paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: "#f1f5f9",
  },
  detayKey: { fontSize: 14, color: "#64748b", fontFamily: "Inter_400Regular" },
  detayVal: { fontSize: 14, color: "#1e293b", fontFamily: "Inter_600SemiBold" },
  aciklamaBox: { paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: "#f1f5f9" },
  aciklamaText: { fontSize: 14, color: "#1e293b", fontFamily: "Inter_400Regular", marginTop: 4 },
  actionRow: { flexDirection: "row", gap: 12, marginTop: 24, marginBottom: 32 },
  redBtn: {
    flex: 1, height: 52, borderRadius: 14,
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    backgroundColor: "#fef2f2", borderWidth: 1.5, borderColor: "#fecaca",
  },
  redBtnText: { fontSize: 15, fontWeight: "700", color: "#ef4444", fontFamily: "Inter_700Bold" },
  onayBtn: {
    flex: 1, height: 52, borderRadius: 14,
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    backgroundColor: "#16a34a",
  },
  onayBtnText: { fontSize: 15, fontWeight: "700", color: "#fff", fontFamily: "Inter_700Bold" },
  retLabel: { fontSize: 14, color: "#475569", fontFamily: "Inter_500Medium", marginBottom: 10 },
  retInput: {
    backgroundColor: "#fff", borderRadius: 12, borderWidth: 1.5, borderColor: "#e2e8f0",
    padding: 14, fontSize: 14, color: "#1e293b", fontFamily: "Inter_400Regular",
    minHeight: 100, marginBottom: 16,
  },
  redBtnFull: {
    backgroundColor: "#ef4444", borderRadius: 14, height: 52,
    alignItems: "center", justifyContent: "center",
  },
  redBtnFullText: { fontSize: 15, fontWeight: "700", color: "#fff", fontFamily: "Inter_700Bold" },
});
