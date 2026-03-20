import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Platform,
  TouchableOpacity,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useAuth } from "@/lib/auth";
import { api, DURUM_ETIKET, DURUM_RENK, IZIN_TURU_ETIKET, IzinItem, PersonelBilgi } from "@/lib/api";

function formatTarih(tarih: string) {
  if (!tarih) return "";
  return new Date(tarih).toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function AnaSayfa() {
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const { data: personelData, isLoading: personelYukleniyor, refetch: personelYenile } = useQuery({
    queryKey: ["/personel/me", user?.tcKimlik],
    queryFn: () =>
      api.get<{ veri: PersonelBilgi[] }>("/personel", {
        q: user?.tcKimlik,
        per_page: 1,
      }),
    enabled: !!user?.tcKimlik,
    select: (d) => d.veri?.[0] ?? null,
  });

  const mePersonel = personelData;

  const { data: sonIzinler, isLoading: izinYukleniyor, refetch: izinYenile } = useQuery({
    queryKey: ["/izinler/son"],
    queryFn: () => api.get<{ veri: IzinItem[] }>("/izinler", { per_page: 5, page: 1 }),
    select: (d) => d.veri,
  });

  const yukleniyor = personelYukleniyor || izinYukleniyor;

  async function yenile() {
    await Promise.all([personelYenile(), izinYenile()]);
  }

  const paddingTop = Platform.OS === "web" ? 67 : insets.top;

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[styles.container, { paddingTop: paddingTop + 16 }]}
      refreshControl={
        <RefreshControl refreshing={yukleniyor} onRefresh={yenile} tintColor="#1a56db" />
      }
    >
      <View style={styles.welcomeRow}>
        <View>
          <Text style={styles.welcomeSmall}>Hoş geldiniz</Text>
          <Text style={styles.welcomeName}>
            {user?.ad} {user?.soyad}
          </Text>
          {user?.unvan ? <Text style={styles.welcomeUnvan}>{user.unvan}</Text> : null}
        </View>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>
            {(user?.ad?.[0] ?? "") + (user?.soyad?.[0] ?? "")}
          </Text>
        </View>
      </View>

      <View style={styles.bakiyeCard}>
        <View style={styles.bakiyeRow}>
          <View style={styles.bakiyeItem}>
            <Text style={styles.bakiyeValue}>{mePersonel?.kalan_izin ?? "—"}</Text>
            <Text style={styles.bakiyeLabel}>Kalan İzin</Text>
          </View>
          <View style={styles.bakiyeDivider} />
          <View style={styles.bakiyeItem}>
            <Text style={styles.bakiyeValue}>{mePersonel?.toplam_izin_hak ?? "—"}</Text>
            <Text style={styles.bakiyeLabel}>Toplam Hak</Text>
          </View>
          <View style={styles.bakiyeDivider} />
          <View style={styles.bakiyeItem}>
            <Text style={styles.bakiyeValue}>{mePersonel?.kullanilan_izin ?? "—"}</Text>
            <Text style={styles.bakiyeLabel}>Kullanılan</Text>
          </View>
        </View>
        {mePersonel && (
          <View style={styles.progressBarBg}>
            <View
              style={[
                styles.progressBar,
                {
                  width: `${Math.min(
                    100,
                    Math.round(
                      ((mePersonel.kullanilan_izin ?? 0) / (mePersonel.toplam_izin_hak || 1)) * 100
                    )
                  )}%`,
                },
              ]}
            />
          </View>
        )}
      </View>

      <View style={styles.hizliActions}>
        <TouchableOpacity
          style={styles.hizliBtn}
          onPress={() => router.push("/(tabs)/izin-talebi")}
        >
          <View style={[styles.hizliIcon, { backgroundColor: "#eff6ff" }]}>
            <Ionicons name="add-circle" size={26} color="#1a56db" />
          </View>
          <Text style={styles.hizliText}>Yeni İzin</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.hizliBtn}
          onPress={() => router.push("/(tabs)/izinlerim")}
        >
          <View style={[styles.hizliIcon, { backgroundColor: "#f0fdf4" }]}>
            <Ionicons name="calendar" size={26} color="#16a34a" />
          </View>
          <Text style={styles.hizliText}>İzinlerim</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.hizliBtn}
          onPress={() => router.push("/(tabs)/profil")}
        >
          <View style={[styles.hizliIcon, { backgroundColor: "#fef9c3" }]}>
            <Ionicons name="person" size={26} color="#ca8a04" />
          </View>
          <Text style={styles.hizliText}>Profilim</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.sectionTitle}>Son İzin Talepleri</Text>

      {sonIzinler && sonIzinler.length === 0 && (
        <View style={styles.emptyBox}>
          <Ionicons name="calendar-outline" size={32} color="#cbd5e1" />
          <Text style={styles.emptyText}>Henüz izin talebi yok</Text>
        </View>
      )}

      {sonIzinler?.map((izin) => (
        <View key={izin.id} style={styles.izinCard}>
          <View style={styles.izinCardTop}>
            <Text style={styles.izinTuru}>
              {IZIN_TURU_ETIKET[izin.izin_turu] ?? izin.izin_turu}
            </Text>
            <View style={[styles.durumBadge, { backgroundColor: DURUM_RENK[izin.durum] + "22" }]}>
              <View style={[styles.durumDot, { backgroundColor: DURUM_RENK[izin.durum] }]} />
              <Text style={[styles.durumText, { color: DURUM_RENK[izin.durum] }]}>
                {DURUM_ETIKET[izin.durum] ?? izin.durum}
              </Text>
            </View>
          </View>
          <View style={styles.izinCardBottom}>
            <Ionicons name="calendar-outline" size={14} color="#64748b" />
            <Text style={styles.izinTarih}>
              {formatTarih(izin.baslangic)} – {formatTarih(izin.bitis)}
            </Text>
            <Text style={styles.izinGun}>{izin.gun_sayisi} gün</Text>
          </View>
        </View>
      ))}

      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f1f5f9" },
  container: { paddingHorizontal: 20 },
  welcomeRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  welcomeSmall: {
    fontSize: 13,
    color: "#64748b",
    fontFamily: "Inter_400Regular",
  },
  welcomeName: {
    fontSize: 22,
    fontWeight: "700",
    color: "#1e293b",
    fontFamily: "Inter_700Bold",
  },
  welcomeUnvan: {
    fontSize: 13,
    color: "#64748b",
    fontFamily: "Inter_400Regular",
    marginTop: 2,
  },
  avatarCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#1a56db",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
    fontFamily: "Inter_700Bold",
  },
  bakiyeCard: {
    backgroundColor: "#1a56db",
    borderRadius: 20,
    padding: 20,
    marginBottom: 20,
    shadowColor: "#1a56db",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  bakiyeRow: { flexDirection: "row", justifyContent: "space-around", marginBottom: 16 },
  bakiyeItem: { alignItems: "center" },
  bakiyeValue: {
    fontSize: 28,
    fontWeight: "700",
    color: "#fff",
    fontFamily: "Inter_700Bold",
  },
  bakiyeLabel: {
    fontSize: 11,
    color: "rgba(255,255,255,0.75)",
    fontFamily: "Inter_400Regular",
    marginTop: 2,
  },
  bakiyeDivider: {
    width: 1,
    backgroundColor: "rgba(255,255,255,0.3)",
    alignSelf: "stretch",
    marginVertical: 4,
  },
  progressBarBg: {
    height: 6,
    backgroundColor: "rgba(255,255,255,0.25)",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressBar: {
    height: "100%",
    backgroundColor: "#fff",
    borderRadius: 3,
  },
  hizliActions: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 24,
    gap: 12,
  },
  hizliBtn: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  hizliIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  hizliText: {
    fontSize: 12,
    color: "#1e293b",
    fontFamily: "Inter_600SemiBold",
    textAlign: "center",
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: "#1e293b",
    fontFamily: "Inter_700Bold",
    marginBottom: 12,
  },
  emptyBox: {
    alignItems: "center",
    padding: 32,
    backgroundColor: "#fff",
    borderRadius: 16,
    gap: 8,
  },
  emptyText: { fontSize: 14, color: "#94a3b8", fontFamily: "Inter_400Regular" },
  izinCard: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 16,
    marginBottom: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  izinCardTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  izinTuru: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1e293b",
    fontFamily: "Inter_600SemiBold",
  },
  durumBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
  },
  durumDot: { width: 6, height: 6, borderRadius: 3 },
  durumText: { fontSize: 11, fontWeight: "600", fontFamily: "Inter_600SemiBold" },
  izinCardBottom: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  izinTarih: { fontSize: 13, color: "#64748b", fontFamily: "Inter_400Regular", flex: 1 },
  izinGun: { fontSize: 13, color: "#475569", fontFamily: "Inter_600SemiBold" },
});
