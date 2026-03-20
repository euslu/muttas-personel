import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  ScrollView,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/lib/auth";

export default function LoginScreen() {
  const { login } = useAuth();
  const insets = useSafeAreaInsets();
  const [tcKimlik, setTcKimlik] = useState("");
  const [sifre, setSifre] = useState("");
  const [sifreGoster, setSifreGoster] = useState(false);
  const [yukleniyor, setYukleniyor] = useState(false);

  async function handleLogin() {
    if (!tcKimlik.trim() || !sifre) {
      Alert.alert("Hata", "Lütfen tüm alanları doldurun.");
      return;
    }
    setYukleniyor(true);
    try {
      await login(tcKimlik, sifre);
    } catch (e: any) {
      Alert.alert("Giriş Başarısız", e.message || "Kullanıcı adı veya şifre hatalı.");
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <View style={[styles.root, { paddingBottom: insets.bottom }]}>
      <View style={styles.header}>
        <View style={styles.logoContainer}>
          <Ionicons name="business" size={40} color="#fff" />
        </View>
        <Text style={styles.logoTitle}>Muttaş İK</Text>
        <Text style={styles.logoSub}>Muğla Büyükşehir Belediyesi</Text>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.formWrapper}
      >
        <ScrollView
          contentContainerStyle={styles.formContainer}
          keyboardShouldPersistTaps="handled"
        >
          <Text style={styles.formTitle}>Giriş Yap</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>TC Kimlik No</Text>
            <View style={styles.inputRow}>
              <Ionicons name="card-outline" size={20} color="#94a3b8" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="TC kimlik numaranız"
                placeholderTextColor="#94a3b8"
                value={tcKimlik}
                onChangeText={setTcKimlik}
                keyboardType="numeric"
                maxLength={11}
                autoCorrect={false}
                autoCapitalize="none"
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Şifre</Text>
            <View style={styles.inputRow}>
              <Ionicons name="lock-closed-outline" size={20} color="#94a3b8" style={styles.inputIcon} />
              <TextInput
                style={[styles.input, { flex: 1 }]}
                placeholder="Şifreniz"
                placeholderTextColor="#94a3b8"
                value={sifre}
                onChangeText={setSifre}
                secureTextEntry={!sifreGoster}
                autoCorrect={false}
                autoCapitalize="none"
                onSubmitEditing={handleLogin}
                returnKeyType="done"
              />
              <TouchableOpacity onPress={() => setSifreGoster(!sifreGoster)} style={styles.eyeBtn}>
                <Ionicons
                  name={sifreGoster ? "eye-off-outline" : "eye-outline"}
                  size={20}
                  color="#94a3b8"
                />
              </TouchableOpacity>
            </View>
          </View>

          <TouchableOpacity
            style={[styles.loginBtn, yukleniyor && styles.loginBtnDisabled]}
            onPress={handleLogin}
            disabled={yukleniyor}
          >
            {yukleniyor ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.loginBtnText}>Giriş Yap</Text>
            )}
          </TouchableOpacity>

          <Text style={styles.hint}>
            Giriş için sistem yöneticinizle iletişime geçin.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1a56db" },
  header: {
    alignItems: "center",
    paddingTop: 80,
    paddingBottom: 40,
  },
  logoContainer: {
    width: 80,
    height: 80,
    borderRadius: 24,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  logoTitle: {
    fontSize: 28,
    fontWeight: "700",
    color: "#fff",
    fontFamily: "Inter_700Bold",
  },
  logoSub: {
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
    fontFamily: "Inter_400Regular",
    marginTop: 4,
  },
  formWrapper: { flex: 1 },
  formContainer: {
    backgroundColor: "#f8fafc",
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 28,
    flexGrow: 1,
  },
  formTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#1e293b",
    fontFamily: "Inter_700Bold",
    marginBottom: 28,
  },
  inputGroup: { marginBottom: 20 },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#475569",
    fontFamily: "Inter_600SemiBold",
    marginBottom: 8,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: "#e2e8f0",
    paddingHorizontal: 14,
  },
  inputIcon: { marginRight: 10 },
  input: {
    flex: 1,
    height: 50,
    fontSize: 15,
    color: "#1e293b",
    fontFamily: "Inter_400Regular",
  },
  eyeBtn: { padding: 4 },
  loginBtn: {
    backgroundColor: "#1a56db",
    borderRadius: 14,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
    shadowColor: "#1a56db",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  loginBtnDisabled: { opacity: 0.7 },
  loginBtnText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
    fontFamily: "Inter_700Bold",
  },
  hint: {
    marginTop: 20,
    fontSize: 12,
    color: "#94a3b8",
    textAlign: "center",
    fontFamily: "Inter_400Regular",
  },
});
