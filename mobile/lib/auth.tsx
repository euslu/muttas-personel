import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import * as SecureStore from "expo-secure-store";
import { api, saveToken, removeToken, LoginResponse } from "./api";

type AuthUser = {
  token: string;
  rol: string;
  ad: string;
  soyad: string;
  unvan: string;
  kullanici_id: number;
  tcKimlik: string;
};

type AuthContextType = {
  user: AuthUser | null;
  loading: boolean;
  login: (tcKimlik: string, sifre: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const stored = await SecureStore.getItemAsync("muttas_user");
        if (stored) {
          setUser(JSON.parse(stored));
        }
      } catch {}
      setLoading(false);
    })();
  }, []);

  const login = useCallback(async (tcKimlik: string, sifre: string) => {
    const data = await api.post<LoginResponse>("/auth/login", {
      email: tcKimlik.trim(),
      password: sifre,
    }, false);

    if (data.sifre_degistir_gerekli) {
      throw new Error("Şifrenizi değiştirmeniz gerekmektedir. Lütfen web panelinden (ik.muttas.com.tr) giriş yaparak şifrenizi güncelleyin.");
    }

    const authUser: AuthUser = {
      token: data.token,
      rol: data.kullanici.rol,
      ad: data.kullanici.ad,
      soyad: data.kullanici.soyad,
      unvan: data.kullanici.unvan,
      kullanici_id: data.kullanici.id,
      tcKimlik: data.kullanici.email,
    };

    await saveToken(data.token);
    await SecureStore.setItemAsync("muttas_user", JSON.stringify(authUser));
    setUser(authUser);
  }, []);

  const logout = useCallback(async () => {
    await removeToken();
    await SecureStore.deleteItemAsync("muttas_user");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
