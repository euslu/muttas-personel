import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Platform,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/lib/auth";
import { api, IzinTuru, PersonelBilgi } from "@/lib/api";

function formatDateInput(val: string): string {
  const digits = val.replace(/\D/g, "").substring(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return digits.slice(0, 2) + "." + digits.slice(2);
  return digits.slice(0, 2) + "." + digits.slice(2, 4) + "." + digits.slice(4);
}

function parseDate(val: string): string | null {
  const parts = val.split(".");
  if (parts.length !== 3 || parts[2].length !== 4) return null;
  const [d, m, y] = parts;
  const date = new Date(`${y}-${m}-${d}`);
  if (isNaN(date.getTime())) return null;
  return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
}

function calcGunSayisi(baslangic: string, bitis: string, calismaGunu: number = 6): number {
  const b = new Date(baslangic);
  const e = new Date(bitis);
  if (isNaN(b.getTime()) || isNaN(e.getTime()) || e < b) return 0;
  let gun = 0;
  const cur = new Date(b);
  while (cur <= e) {
    const dow = cur.getDay(); // 0=Pazar, 6=Cumartesi
    if (calismaGunu === 6) {
      if (dow !== 0) gun++; // Pazar hariç
    } else {
      if (dow !== 0 && dow !== 6) gun++; // Pazar ve Cumartesi hariç
    }
    cur.setDate(cur.getDate() + 1);
  }
  return gun || 1;
}

export default function IzinTalebi() {
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();

  const [seciliTur, setSeciliTur] = useState("");
  const [baslangicStr, setBaslangicStr] = useState("");
  const [bitisStr, setBitisStr] = useState("");
  const [aciklama, setAciklama] = useState("");
  const [adim, setAdim] = useState<"tur" | "tarih" | "ozet">("tur");

  const { data: izinTurleri } = useQuery<{ kod: string; ad: string }[]>({
    queryKey: ["/ayarlar/izin-turleri"],
    queryFn: () => api.get<{ kod: string; ad: string }[]>("/ayarlar/izin-turleri"),
    staleTime: 1000 * 60 * 30,
  });

  const { data: mePersonel } = useQuery<PersonelBilgi | null>({
    queryKey: ["/personel/me/talebi", user?.tcKimlik],
    queryFn: () =>
      api.get<{ veri: PersonelBilgi[] }>("/personel", {
        q: user?.tcKimlik,
        per_page: 1,
      }),
    enabled: !!user?.tcKimlik,
    select: (d: any) => d.veri?.[0] ?? null,
  });

  const { data: calismaGunleri } = useQuery<Record<string, number>>({
    queryKey: ["/public/calisma-gunleri"],
    queryFn: () => api.get<Record<string, number>>("/public/calisma-gunleri", {}, false),
    staleTime: 1000 * 60 * 60,
  });

  const personelCalismaGunu = calismaGunleri && mePersonel?.unvan
    ? (calismaGunleri[(mePersonel.unvan || "").toUpperCase()] ?? 6)
    : 6;

  const baslangicISO = parseDate(baslangicStr);
  const bitisISO = parseDate(bitisStr);
  const gunSayisi = baslangicISO && bitisISO ? calcGunSayisi(baslangicISO, bitisISO, personelCalismaGunu) : 0;

  const { mutate: izinGonder, isPending } = useMutation({
    mutationFn: () =>
      api.post("/izinler", {
        personel_id: mePersonel!.id,
        izin_turu: seciliTur,
        baslangic: baslangicISO,
        bitis: bitisISO,
        gun_sayisi: gunSayisi,
        aciklama: aciklama || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/izinler/son"] });
      queryClient.invalidateQueries({ queryKey: ["/izinler"] });
      Alert.alert("Başarılı", "İzin talebiniz oluşturuldu.", [
        {
          text: "Tamam",
          onPress: () => {
            setAdim("tur");
            setSeciliTur("");
            setBaslangicStr("");
            setBitisStr("");
            setAciklama("");
          },
        },
      ]);
    },
    onError: (e: Error) => {
      Alert.alert("Hata", e.message);
    },
  });

  function handleGonder() {
    if (!mePersonel) {
      Alert.alert("Hata", "Personel bilgisi bulunamadı.");
      return;
    }
    if (!baslangicISO || !bitisISO) {
      Alert.alert("Hata", "Geçerli tarihler girin (GG.AA.YYYY).");
      return;
    }
    if (gunSayisi <= 0) {
      Alert.alert("Hata", "Bitiş tarihi başlangıçtan önce olamaz.");
      return;
    }
    izinGonder();
  }

  const paddingTop = Platform.OS === "web" ? 67 : insets.top;
  const selectedTurAd = (izinTurleri ?? []).find((t) => t.kod === seciliTur)?.ad ?? "";

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[styles.container, { paddingTop: paddingTop + 16 }]}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.pageTitle}>İzin Talebi</Text>
      <Text style={styles.pageSubTitle}>Yeni izin talebi oluşturun</Text>

      <View style={styles.stepRow}>
        {(["tur", "tarih", "ozet"] as const).map((s, i) => (
          <View key={s} style={styles.stepItem}>
            <View style={[styles.stepCircle, adim === s || (i < ["tur","tarih","ozet"].indexOf(adim)) ? styles.stepDone : {}]}>
              <Text style={styles.stepNum}>{i + 1}</Text>
            </View>
            {i < 2 && <View style={styles.stepLine} />}
          </View>
        ))}
      </View>

      {adim === "tur" && (
        <View>
          <Text style={styles.sectionLabel}>İzin Türü Seçin</Text>
          {(izinTurleri ?? []).map((tur) => (
            <TouchableOpacity
              key={tur.kod}
              style={[styles.turItem, seciliTur === tur.kod && styles.turItemActive]}
              onPress={() => setSeciliTur(tur.kod)}
            >
              <View style={[styles.turRadio, seciliTur === tur.kod && styles.turRadioActive]}>
                {seciliTur === tur.kod && <View style={styles.turRadioDot} />}
              </View>
              <Text style={[styles.turText, seciliTur === tur.kod && styles.turTextActive]}>
                {tur.ad}
              </Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity
            style={[styles.nextBtn, !seciliTur && styles.nextBtnDisabled]}
            onPress={() => seciliTur && setAdim("tarih")}
            disabled={!seciliTur}
          >
            <Text style={styles.nextBtnText}>İleri</Text>
            <Ionicons name="arrow-forward" size={18} color="#fff" />
          </TouchableOpacity>
        </View>
      )}

      {adim === "tarih" && (
        <View>
          <Text style={styles.sectionLabel}>Tarih Aralığı</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Başlangıç Tarihi</Text>
            <View style={styles.inputRow}>
              <Ionicons name="calendar-outline" size={18} color="#94a3b8" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="GG.AA.YYYY"
                placeholderTextColor="#94a3b8"
                value={baslangicStr}
                onChangeText={(v) => setBaslangicStr(formatDateInput(v))}
                keyboardType="numeric"
                maxLength={10}
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Bitiş Tarihi</Text>
            <View style={styles.inputRow}>
              <Ionicons name="calendar-outline" size={18} color="#94a3b8" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="GG.AA.YYYY"
                placeholderTextColor="#94a3b8"
                value={bitisStr}
                onChangeText={(v) => setBitisStr(formatDateInput(v))}
                keyboardType="numeric"
                maxLength={10}
              />
            </View>
          </View>

          {gunSayisi > 0 && (
            <View style={styles.gunBadge}>
              <Ionicons name="time-outline" size={16} color="#1a56db" />
              <Text style={styles.gunBadgeText}>{gunSayisi} takvim günü</Text>
            </View>
          )}

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Açıklama (opsiyonel)</Text>
            <TextInput
              style={[styles.inputRow, styles.textArea]}
              placeholder="İzin nedeninizi yazabilirsiniz..."
              placeholderTextColor="#94a3b8"
              value={aciklama}
              onChangeText={setAciklama}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
          </View>

          <View style={styles.btnRow}>
            <TouchableOpacity style={styles.backBtn} onPress={() => setAdim("tur")}>
              <Ionicons name="arrow-back" size={18} color="#475569" />
              <Text style={styles.backBtnText}>Geri</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.nextBtn, { flex: 1 }, (!baslangicISO || !bitisISO || gunSayisi <= 0) && styles.nextBtnDisabled]}
              onPress={() => baslangicISO && bitisISO && gunSayisi > 0 && setAdim("ozet")}
              disabled={!baslangicISO || !bitisISO || gunSayisi <= 0}
            >
              <Text style={styles.nextBtnText}>İleri</Text>
              <Ionicons name="arrow-forward" size={18} color="#fff" />
            </TouchableOpacity>
          </View>
        </View>
      )}

      {adim === "ozet" && (
        <View>
          <Text style={styles.sectionLabel}>Özet & Onay</Text>

          <View style={styles.ozetCard}>
            <View style={styles.ozetRow}>
              <Text style={styles.ozetKey}>İzin Türü</Text>
              <Text style={styles.ozetVal}>{selectedTurAd}</Text>
            </View>
            <View style={styles.ozetDivider} />
            <View style={styles.ozetRow}>
              <Text style={styles.ozetKey}>Başlangıç</Text>
              <Text style={styles.ozetVal}>{baslangicStr}</Text>
            </View>
            <View style={styles.ozetDivider} />
            <View style={styles.ozetRow}>
              <Text style={styles.ozetKey}>Bitiş</Text>
              <Text style={styles.ozetVal}>{bitisStr}</Text>
            </View>
            <View style={styles.ozetDivider} />
            <View style={styles.ozetRow}>
              <Text style={styles.ozetKey}>Toplam</Text>
              <Text style={[styles.ozetVal, { color: "#1a56db", fontFamily: "Inter_700Bold" }]}>
                {gunSayisi} gün
              </Text>
            </View>
            {aciklama ? (
              <>
                <View style={styles.ozetDivider} />
                <View style={styles.ozetRow}>
                  <Text style={styles.ozetKey}>Açıklama</Text>
                  <Text style={[styles.ozetVal, { flex: 1 }]}>{aciklama}</Text>
                </View>
              </>
            ) : null}
          </View>

          <View style={styles.btnRow}>
            <TouchableOpacity style={styles.backBtn} onPress={() => setAdim("tarih")}>
              <Ionicons name="arrow-back" size={18} color="#475569" />
              <Text style={styles.backBtnText}>Geri</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.nextBtn, { flex: 1, backgroundColor: "#16a34a" }, isPending && styles.nextBtnDisabled]}
              onPress={handleGonder}
              disabled={isPending}
            >
              {isPending ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="checkmark" size={18} color="#fff" />
                  <Text style={styles.nextBtnText}>Talebi Gönder</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f1f5f9" },
  container: { paddingHorizontal: 20 },
  pageTitle: { fontSize: 24, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  pageSubTitle: { fontSize: 14, color: "#64748b", fontFamily: "Inter_400Regular", marginTop: 2, marginBottom: 24 },
  stepRow: { flexDirection: "row", alignItems: "center", marginBottom: 28 },
  stepItem: { flexDirection: "row", alignItems: "center", flex: 1 },
  stepCircle: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: "#e2e8f0", alignItems: "center", justifyContent: "center",
  },
  stepDone: { backgroundColor: "#1a56db" },
  stepNum: { fontSize: 13, fontWeight: "700", color: "#fff", fontFamily: "Inter_700Bold" },
  stepLine: { flex: 1, height: 2, backgroundColor: "#e2e8f0", marginHorizontal: 4 },
  sectionLabel: { fontSize: 16, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold", marginBottom: 16 },
  turItem: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "#fff", borderRadius: 14, padding: 16,
    marginBottom: 10, borderWidth: 2, borderColor: "transparent",
    shadowColor: "#000", shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 3, elevation: 1,
  },
  turItemActive: { borderColor: "#1a56db", backgroundColor: "#eff6ff" },
  turRadio: {
    width: 20, height: 20, borderRadius: 10,
    borderWidth: 2, borderColor: "#cbd5e1",
    alignItems: "center", justifyContent: "center", marginRight: 12,
  },
  turRadioActive: { borderColor: "#1a56db" },
  turRadioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: "#1a56db" },
  turText: { fontSize: 15, color: "#475569", fontFamily: "Inter_500Medium" },
  turTextActive: { color: "#1a56db", fontFamily: "Inter_600SemiBold" },
  nextBtn: {
    backgroundColor: "#1a56db", borderRadius: 14, height: 52,
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, marginTop: 16,
  },
  nextBtnDisabled: { opacity: 0.5 },
  nextBtnText: { color: "#fff", fontSize: 15, fontWeight: "700", fontFamily: "Inter_700Bold" },
  btnRow: { flexDirection: "row", gap: 12, marginTop: 16 },
  backBtn: {
    flexDirection: "row", alignItems: "center", gap: 6,
    backgroundColor: "#fff", borderRadius: 14, paddingHorizontal: 16, height: 52,
    borderWidth: 1.5, borderColor: "#e2e8f0",
  },
  backBtnText: { fontSize: 14, color: "#475569", fontFamily: "Inter_600SemiBold" },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 13, fontWeight: "600", color: "#475569", fontFamily: "Inter_600SemiBold", marginBottom: 8 },
  inputRow: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "#fff", borderRadius: 12, borderWidth: 1.5,
    borderColor: "#e2e8f0", paddingHorizontal: 14,
  },
  inputIcon: { marginRight: 8 },
  input: { flex: 1, height: 48, fontSize: 15, color: "#1e293b", fontFamily: "Inter_400Regular" },
  textArea: {
    paddingTop: 12, paddingBottom: 12, minHeight: 90,
    flexDirection: "column", alignItems: "flex-start",
  },
  gunBadge: {
    flexDirection: "row", alignItems: "center", gap: 6,
    backgroundColor: "#eff6ff", borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 10, marginBottom: 16,
  },
  gunBadgeText: { fontSize: 14, color: "#1a56db", fontFamily: "Inter_600SemiBold" },
  ozetCard: {
    backgroundColor: "#fff", borderRadius: 16, padding: 20,
    shadowColor: "#000", shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 6, elevation: 2,
  },
  ozetRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 12 },
  ozetKey: { fontSize: 14, color: "#64748b", fontFamily: "Inter_400Regular" },
  ozetVal: { fontSize: 14, color: "#1e293b", fontFamily: "Inter_600SemiBold" },
  ozetDivider: { height: 1, backgroundColor: "#f1f5f9" },
});
