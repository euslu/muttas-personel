import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Platform,
  Alert,
  TextInput,
  Modal,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useMutation } from "@tanstack/react-query";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const ROL_ETIKET: Record<string, string> = {
  admin: "Sistem Yöneticisi",
  ik_admin: "İK Yöneticisi",
  genel_mudur: "Genel Müdür",
  koordinasyon_sorumlusu: "Koordinasyon Sorumlusu",
  mudur: "Müdür",
  yk_uyesi: "YK Üyesi",
  liman_viewer: "Personel",
};

export default function Profil() {
  const { user, logout } = useAuth();
  const insets = useSafeAreaInsets();
  const [sifreModal, setSifreModal] = useState(false);
  const [mevcutSifre, setMevcutSifre] = useState("");
  const [yeniSifre, setYeniSifre] = useState("");
  const [yeniSifreTekrar, setYeniSifreTekrar] = useState("");

  const { mutate: sifreDegistir, isPending } = useMutation({
    mutationFn: () =>
      api.put("/auth/sifre-degistir", {
        mevcut_sifre: mevcutSifre,
        yeni_sifre: yeniSifre,
      }),
    onSuccess: () => {
      setSifreModal(false);
      setMevcutSifre(""); setYeniSifre(""); setYeniSifreTekrar("");
      Alert.alert("Başarılı", "Şifreniz güncellendi.");
    },
    onError: (e: Error) => Alert.alert("Hata", e.message),
  });

  function handleSifreDegistir() {
    if (!mevcutSifre || !yeniSifre || !yeniSifreTekrar) {
      Alert.alert("Hata", "Tüm alanları doldurun."); return;
    }
    if (yeniSifre !== yeniSifreTekrar) {
      Alert.alert("Hata", "Yeni şifreler eşleşmiyor."); return;
    }
    if (yeniSifre.length < 8) {
      Alert.alert("Hata", "Şifre en az 8 karakter olmalı."); return;
    }
    sifreDegistir();
  }

  function handleCikis() {
    Alert.alert("Çıkış Yap", "Uygulamadan çıkmak istediğinize emin misiniz?", [
      { text: "İptal", style: "cancel" },
      { text: "Çıkış Yap", style: "destructive", onPress: logout },
    ]);
  }

  const paddingTop = Platform.OS === "web" ? 67 : insets.top;

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[styles.container, { paddingTop: paddingTop + 16 }]}
    >
      <Text style={styles.pageTitle}>Profil</Text>

      <View style={styles.profilCard}>
        <View style={styles.avatarBig}>
          <Text style={styles.avatarBigText}>
            {(user?.ad?.[0] ?? "") + (user?.soyad?.[0] ?? "")}
          </Text>
        </View>
        <Text style={styles.adSoyad}>{user?.ad} {user?.soyad}</Text>
        <Text style={styles.unvan}>{user?.unvan || ROL_ETIKET[user?.rol ?? ""] || user?.rol}</Text>
        <View style={styles.rolBadge}>
          <Text style={styles.rolText}>{ROL_ETIKET[user?.rol ?? ""] ?? user?.rol}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Hesap</Text>

        <TouchableOpacity style={styles.menuItem} onPress={() => setSifreModal(true)}>
          <View style={[styles.menuIcon, { backgroundColor: "#eff6ff" }]}>
            <Ionicons name="lock-closed-outline" size={20} color="#1a56db" />
          </View>
          <View style={styles.menuContent}>
            <Text style={styles.menuLabel}>Şifre Değiştir</Text>
            <Text style={styles.menuSub}>Hesap şifrenizi güncelleyin</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color="#cbd5e1" />
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Uygulama</Text>

        <View style={styles.menuItem}>
          <View style={[styles.menuIcon, { backgroundColor: "#f0fdf4" }]}>
            <Ionicons name="information-circle-outline" size={20} color="#16a34a" />
          </View>
          <View style={styles.menuContent}>
            <Text style={styles.menuLabel}>Versiyon</Text>
            <Text style={styles.menuSub}>Muttaş İK v1.0.0</Text>
          </View>
        </View>

        <View style={styles.menuItem}>
          <View style={[styles.menuIcon, { backgroundColor: "#fef9c3" }]}>
            <Ionicons name="globe-outline" size={20} color="#ca8a04" />
          </View>
          <View style={styles.menuContent}>
            <Text style={styles.menuLabel}>Sunucu</Text>
            <Text style={styles.menuSub}>ik.muttas.com.tr</Text>
          </View>
        </View>
      </View>

      <TouchableOpacity style={styles.cikisBtn} onPress={handleCikis}>
        <Ionicons name="log-out-outline" size={20} color="#ef4444" />
        <Text style={styles.cikisBtnText}>Çıkış Yap</Text>
      </TouchableOpacity>

      <View style={{ height: 40 }} />

      <Modal
        visible={sifreModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setSifreModal(false)}
      >
        <View style={styles.modal}>
          <View style={styles.modalHandle} />
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Şifre Değiştir</Text>
            <TouchableOpacity onPress={() => setSifreModal(false)}>
              <Ionicons name="close" size={24} color="#475569" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalBody} keyboardShouldPersistTaps="handled">
            {[
              { label: "Mevcut Şifre", val: mevcutSifre, set: setMevcutSifre },
              { label: "Yeni Şifre", val: yeniSifre, set: setYeniSifre },
              { label: "Yeni Şifre (Tekrar)", val: yeniSifreTekrar, set: setYeniSifreTekrar },
            ].map(({ label, val, set }) => (
              <View key={label} style={styles.inputGroup}>
                <Text style={styles.label}>{label}</Text>
                <TextInput
                  style={styles.inputField}
                  value={val}
                  onChangeText={set}
                  secureTextEntry
                  placeholder="••••••"
                  placeholderTextColor="#94a3b8"
                  autoCapitalize="none"
                />
              </View>
            ))}

            <TouchableOpacity
              style={[styles.kaydetBtn, isPending && { opacity: 0.6 }]}
              onPress={handleSifreDegistir}
              disabled={isPending}
            >
              {isPending ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.kaydetBtnText}>Kaydet</Text>
              )}
            </TouchableOpacity>
          </ScrollView>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f1f5f9" },
  container: { paddingHorizontal: 20 },
  pageTitle: { fontSize: 24, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold", marginBottom: 20 },
  profilCard: {
    backgroundColor: "#fff", borderRadius: 20, padding: 24,
    alignItems: "center", marginBottom: 24,
    shadowColor: "#000", shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 8, elevation: 3,
  },
  avatarBig: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: "#1a56db", alignItems: "center", justifyContent: "center",
    marginBottom: 12,
  },
  avatarBigText: { fontSize: 28, fontWeight: "700", color: "#fff", fontFamily: "Inter_700Bold" },
  adSoyad: { fontSize: 20, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  unvan: { fontSize: 14, color: "#64748b", fontFamily: "Inter_400Regular", marginTop: 4, marginBottom: 10 },
  rolBadge: {
    backgroundColor: "#eff6ff", borderRadius: 20,
    paddingHorizontal: 14, paddingVertical: 5,
  },
  rolText: { fontSize: 12, color: "#1a56db", fontWeight: "600", fontFamily: "Inter_600SemiBold" },
  section: { marginBottom: 20 },
  sectionTitle: {
    fontSize: 13, fontWeight: "600", color: "#94a3b8",
    fontFamily: "Inter_600SemiBold", marginBottom: 8,
    textTransform: "uppercase", letterSpacing: 0.5,
  },
  menuItem: {
    backgroundColor: "#fff", borderRadius: 16, padding: 16,
    flexDirection: "row", alignItems: "center", gap: 14, marginBottom: 8,
    shadowColor: "#000", shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04, shadowRadius: 3, elevation: 1,
  },
  menuIcon: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  menuContent: { flex: 1 },
  menuLabel: { fontSize: 15, fontWeight: "600", color: "#1e293b", fontFamily: "Inter_600SemiBold" },
  menuSub: { fontSize: 12, color: "#94a3b8", fontFamily: "Inter_400Regular", marginTop: 1 },
  cikisBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10,
    backgroundColor: "#fef2f2", borderRadius: 16, padding: 16,
    borderWidth: 1.5, borderColor: "#fecaca",
  },
  cikisBtnText: { fontSize: 16, fontWeight: "700", color: "#ef4444", fontFamily: "Inter_700Bold" },
  modal: { flex: 1, backgroundColor: "#f8fafc" },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: "#cbd5e1", alignSelf: "center", marginTop: 12 },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: "700", color: "#1e293b", fontFamily: "Inter_700Bold" },
  modalBody: { flex: 1, paddingHorizontal: 20 },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 13, fontWeight: "600", color: "#475569", fontFamily: "Inter_600SemiBold", marginBottom: 8 },
  inputField: {
    backgroundColor: "#fff", borderRadius: 12, borderWidth: 1.5,
    borderColor: "#e2e8f0", paddingHorizontal: 14, height: 50,
    fontSize: 15, color: "#1e293b", fontFamily: "Inter_400Regular",
  },
  kaydetBtn: {
    backgroundColor: "#1a56db", borderRadius: 14, height: 52,
    alignItems: "center", justifyContent: "center", marginTop: 8,
  },
  kaydetBtnText: { fontSize: 15, fontWeight: "700", color: "#fff", fontFamily: "Inter_700Bold" },
});
