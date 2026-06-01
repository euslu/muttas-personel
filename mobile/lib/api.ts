import * as SecureStore from "expo-secure-store";

const BASE_URL = "https://ik.muttas.com.tr";

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync("muttas_token");
}

export async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync("muttas_token", token);
}

export async function removeToken(): Promise<void> {
  await SecureStore.deleteItemAsync("muttas_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  withAuth = true
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (withAuth) {
    const token = await getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || err.message || msg;
    } catch {}
    throw new Error(msg);
  }

  return res.json();
}

export const api = {
  post: <T>(path: string, body: unknown, auth = true) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }, auth),

  get: <T>(path: string, params?: Record<string, string | number | undefined>) => {
    let url = path;
    if (params) {
      const qs = Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join("&");
      if (qs) url += `?${qs}`;
    }
    return request<T>(url, { method: "GET" });
  },

  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),

  delete: <T>(path: string) =>
    request<T>(path, { method: "DELETE" }),
};

export type LoginResponse = {
  token: string;
  kullanici: {
    id: number;
    ad: string;
    soyad: string;
    email: string;
    rol: string;
    unvan: string;
  };
};

export type IzinItem = {
  id: number;
  personel_id: number;
  ad_soyad: string;
  bolum: string;
  unvan: string;
  izin_turu: string;
  baslangic: string;
  bitis: string;
  gun_sayisi: number;
  durum: string;
  aciklama: string | null;
  olusturuldu: string;
  ret_nedeni: string | null;
};

export type IzinListesi = {
  toplam: number;
  sayfa: number;
  per_page: number;
  veri: IzinItem[];
};

export type PersonelBilgi = {
  id: number;
  ad_soyad: string;
  tc_kimlik: string;
  unvan: string;
  bolum: string;
  ilce: string;
  kalan_izin: number;
  toplam_izin_hak: number;
  kullanilan_izin: number;
};

export type IzinTuru = {
  id: number;
  kod: string;
  ad: string;
  aktif: boolean;
};

export const DURUM_RENK: Record<string, string> = {
  beklemede: "#f59e0b",
  ks_onayladi: "#06b6d4",
  ik_onayladi: "#3b82f6",
  mudur_onayladi: "#8b5cf6",
  onaylandi: "#10b981",
  reddedildi: "#ef4444",
  tamamlandi: "#6b7280",
};

export const DURUM_ETIKET: Record<string, string> = {
  beklemede: "Beklemede",
  ks_onayladi: "KS Onayladı",
  ik_onayladi: "İK Onayladı",
  mudur_onayladi: "Müdür Onayladı",
  onaylandi: "Onaylandı",
  reddedildi: "Reddedildi",
  tamamlandi: "Tamamlandı",
};

export const IZIN_TURU_ETIKET: Record<string, string> = {
  yillik: "Yıllık İzin",
  ucretsiz: "Ücretsiz İzin",
  hastalik: "Hastalık İzni",
  dogum: "Doğum İzni",
  evlilik: "Evlilik İzni",
  olum: "Ölüm İzni",
  babalik: "Babalık İzni",
  saatlik: "Saatlik İzin",
};

export const YONETICI_ROLLER = new Set([
  "admin",
  "ik_admin",
  "genel_mudur",
  "koordinasyon_sorumlusu",
  "mudur",
  "yk_uyesi",
]);

export function isYonetici(rol: string): boolean {
  return YONETICI_ROLLER.has(rol);
}
