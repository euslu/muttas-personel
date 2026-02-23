--
-- PostgreSQL database dump
--

-- Dumped from database version 16.10
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: baglamalar; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.baglamalar (
    id integer NOT NULL,
    liman_id integer,
    tekne_id integer,
    kullanici_id integer,
    giris_tarihi timestamp with time zone NOT NULL,
    cikis_tarihi timestamp with time zone,
    iskele_no character varying(50),
    durum character varying(50) DEFAULT 'aktif'::character varying,
    notlar text,
    olusturuldu timestamp with time zone DEFAULT now(),
    ref_no character varying(20),
    basvuru_sahibi character varying(150),
    telefon character varying(20),
    odeme_linki character varying(255),
    odeme_linki_tarihi timestamp without time zone,
    sigorta_bitis date,
    basvuru_token character varying(36),
    eposta character varying(255),
    tc_kimlik character varying(20)
);


--
-- Name: baglamalar_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.baglamalar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: baglamalar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.baglamalar_id_seq OWNED BY public.baglamalar.id;


--
-- Name: belgeler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.belgeler (
    id integer NOT NULL,
    basvuru_id integer NOT NULL,
    dosya_tipi character varying(50) NOT NULL,
    dosya_adi character varying(255),
    dosya_yolu text,
    yuklendi_at timestamp with time zone DEFAULT now()
);


--
-- Name: belgeler_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.belgeler_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: belgeler_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.belgeler_id_seq OWNED BY public.belgeler.id;


--
-- Name: faturalar; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.faturalar (
    id integer NOT NULL,
    baglama_id integer,
    kullanici_id integer,
    fatura_no character varying(100) NOT NULL,
    tutar numeric(12,2) NOT NULL,
    kdv_orani numeric(5,2) DEFAULT 20,
    toplam_tutar numeric(12,2) NOT NULL,
    durum character varying(50) DEFAULT 'beklemede'::character varying,
    odeme_tarihi timestamp with time zone,
    son_odeme_tarihi date,
    notlar text,
    olusturuldu timestamp with time zone DEFAULT now(),
    odeme_turu character varying(50),
    banka character varying(50),
    tahsil_eden character varying(200),
    hizmetler jsonb DEFAULT '{}'::jsonb,
    damga_vergisi numeric(12,2) DEFAULT 0,
    kdv_tutari numeric(12,2)
);


--
-- Name: faturalar_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.faturalar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: faturalar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.faturalar_id_seq OWNED BY public.faturalar.id;


--
-- Name: gunluk_kayitlar; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gunluk_kayitlar (
    id integer NOT NULL,
    liman_id integer,
    tekne_id integer,
    tekne_adi character varying(255) NOT NULL,
    kullanici_id integer,
    bolge character varying(100),
    hareket_tipi character varying(10) NOT NULL,
    tarih date DEFAULT CURRENT_DATE NOT NULL,
    saat time without time zone DEFAULT CURRENT_TIME NOT NULL,
    yolcu_sayisi integer DEFAULT 0,
    bilgi_notu text,
    olusturuldu timestamp with time zone DEFAULT now(),
    CONSTRAINT gunluk_kayitlar_hareket_tipi_check CHECK (((hareket_tipi)::text = ANY ((ARRAY['giris'::character varying, 'cikis'::character varying])::text[])))
);


--
-- Name: gunluk_kayitlar_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gunluk_kayitlar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gunluk_kayitlar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gunluk_kayitlar_id_seq OWNED BY public.gunluk_kayitlar.id;


--
-- Name: gunluk_ozet; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gunluk_ozet (
    id integer NOT NULL,
    liman_id integer,
    tarih date NOT NULL,
    toplam_tekne integer DEFAULT 0,
    giris_sayisi integer DEFAULT 0,
    cikis_sayisi integer DEFAULT 0,
    toplam_gelir numeric(12,2) DEFAULT 0,
    notlar text,
    olusturuldu timestamp with time zone DEFAULT now()
);


--
-- Name: gunluk_ozet_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gunluk_ozet_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gunluk_ozet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gunluk_ozet_id_seq OWNED BY public.gunluk_ozet.id;


--
-- Name: izinler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.izinler (
    id integer NOT NULL,
    personel_id integer NOT NULL,
    talep_tarihi date DEFAULT CURRENT_DATE NOT NULL,
    izin_turu character varying(50) NOT NULL,
    baslangic date NOT NULL,
    bitis date NOT NULL,
    gun_sayisi integer NOT NULL,
    kullanilabilir_gun integer,
    vekil_ad_soyad character varying(200),
    izin_adresi text,
    durum character varying(30) DEFAULT 'beklemede'::character varying,
    ik_onay_tarihi date,
    ik_onaylayan character varying(200),
    mudur_onay_tarihi date,
    yk_onay_tarihi date,
    gorev_baslama date,
    notlar text,
    olusturuldu timestamp with time zone DEFAULT now(),
    imza text
);


--
-- Name: izinler_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.izinler_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: izinler_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.izinler_id_seq OWNED BY public.izinler.id;


--
-- Name: kullanicilar; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kullanicilar (
    id integer NOT NULL,
    ad character varying(100) NOT NULL,
    soyad character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    telefon character varying(30),
    rol character varying(50) DEFAULT 'kullanici'::character varying,
    aktif boolean DEFAULT true,
    olusturuldu timestamp with time zone DEFAULT now(),
    password_hash character varying(255)
);


--
-- Name: kullanicilar_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.kullanicilar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: kullanicilar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.kullanicilar_id_seq OWNED BY public.kullanicilar.id;


--
-- Name: liman_gunlugu; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.liman_gunlugu (
    id integer NOT NULL,
    liman_id integer,
    baglama_id integer,
    tarih timestamp with time zone DEFAULT now(),
    olay_turu character varying(100) NOT NULL,
    aciklama text,
    kullanici_id integer,
    olusturuldu timestamp with time zone DEFAULT now()
);


--
-- Name: liman_gunlugu_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.liman_gunlugu_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: liman_gunlugu_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.liman_gunlugu_id_seq OWNED BY public.liman_gunlugu.id;


--
-- Name: limanlar; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.limanlar (
    id integer NOT NULL,
    ad character varying(255) NOT NULL,
    sehir character varying(255),
    ulke character varying(100) DEFAULT 'TR'::character varying,
    kapasite integer,
    aktif boolean DEFAULT true,
    olusturuldu timestamp with time zone DEFAULT now()
);


--
-- Name: limanlar_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.limanlar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: limanlar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.limanlar_id_seq OWNED BY public.limanlar.id;


--
-- Name: personel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.personel (
    id integer NOT NULL,
    tc_kimlik character varying(11),
    sgk_sicil character varying(50),
    maliyet_merkezi character varying(100),
    ilce character varying(100),
    hizmet_noktasi character varying(200),
    ad_soyad character varying(200) NOT NULL,
    cinsiyet character varying(10),
    bolum character varying(100),
    unvan character varying(150),
    ise_giris date,
    isten_cikis date,
    cikis_kodu character varying(200),
    guvenlik_belge_tarih date,
    sigortalilik_baslama date,
    hizmet_gun integer,
    ogrenim character varying(50),
    mezun_bolum character varying(150),
    brut_ucret numeric(12,2),
    dogum_yeri character varying(100),
    dogum_tarihi date,
    sendika_uyesi character varying(50),
    kan_grubu character varying(10),
    medeni_hal character varying(20),
    cocuk_sayisi integer DEFAULT 0,
    engelli boolean DEFAULT false,
    adres text,
    telefon character varying(30),
    meslek_kodu character varying(20),
    meslek_adi character varying(150),
    notlar text,
    aktif boolean DEFAULT true,
    olusturuldu timestamp with time zone DEFAULT now()
);


--
-- Name: personel_evraklari; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.personel_evraklari (
    id integer NOT NULL,
    personel_id integer NOT NULL,
    evrak_adi character varying(255) NOT NULL,
    dosya_adi character varying(255) NOT NULL,
    dosya_yolu text NOT NULL,
    dosya_boyut bigint,
    mime_type character varying(100),
    yuklendi_at timestamp with time zone DEFAULT now()
);


--
-- Name: personel_evraklari_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.personel_evraklari_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: personel_evraklari_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.personel_evraklari_id_seq OWNED BY public.personel_evraklari.id;


--
-- Name: personel_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.personel_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: personel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.personel_id_seq OWNED BY public.personel.id;


--
-- Name: tekne_evraklari; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tekne_evraklari (
    id integer NOT NULL,
    tekne_id integer,
    evrak_turu character varying(100) NOT NULL,
    evrak_no character varying(100),
    duzenleme_tarihi date,
    gecerlilik_tarihi date,
    dosya_yolu text,
    notlar text,
    olusturuldu timestamp with time zone DEFAULT now()
);


--
-- Name: tekne_evraklari_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tekne_evraklari_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tekne_evraklari_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tekne_evraklari_id_seq OWNED BY public.tekne_evraklari.id;


--
-- Name: tekneler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tekneler (
    id integer NOT NULL,
    sahip_id integer,
    ad character varying(255) NOT NULL,
    tip character varying(100),
    uzunluk_m numeric(6,2),
    genislik_m numeric(6,2),
    sicil_no character varying(100),
    bayrak_ulke character varying(100) DEFAULT 'TR'::character varying,
    aktif boolean DEFAULT true,
    olusturuldu timestamp with time zone DEFAULT now()
);


--
-- Name: tekneler_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tekneler_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tekneler_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tekneler_id_seq OWNED BY public.tekneler.id;


--
-- Name: baglamalar id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baglamalar ALTER COLUMN id SET DEFAULT nextval('public.baglamalar_id_seq'::regclass);


--
-- Name: belgeler id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.belgeler ALTER COLUMN id SET DEFAULT nextval('public.belgeler_id_seq'::regclass);


--
-- Name: faturalar id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faturalar ALTER COLUMN id SET DEFAULT nextval('public.faturalar_id_seq'::regclass);


--
-- Name: gunluk_kayitlar id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_kayitlar ALTER COLUMN id SET DEFAULT nextval('public.gunluk_kayitlar_id_seq'::regclass);


--
-- Name: gunluk_ozet id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_ozet ALTER COLUMN id SET DEFAULT nextval('public.gunluk_ozet_id_seq'::regclass);


--
-- Name: izinler id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.izinler ALTER COLUMN id SET DEFAULT nextval('public.izinler_id_seq'::regclass);


--
-- Name: kullanicilar id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kullanicilar ALTER COLUMN id SET DEFAULT nextval('public.kullanicilar_id_seq'::regclass);


--
-- Name: liman_gunlugu id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.liman_gunlugu ALTER COLUMN id SET DEFAULT nextval('public.liman_gunlugu_id_seq'::regclass);


--
-- Name: limanlar id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.limanlar ALTER COLUMN id SET DEFAULT nextval('public.limanlar_id_seq'::regclass);


--
-- Name: personel id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personel ALTER COLUMN id SET DEFAULT nextval('public.personel_id_seq'::regclass);


--
-- Name: personel_evraklari id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personel_evraklari ALTER COLUMN id SET DEFAULT nextval('public.personel_evraklari_id_seq'::regclass);


--
-- Name: tekne_evraklari id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tekne_evraklari ALTER COLUMN id SET DEFAULT nextval('public.tekne_evraklari_id_seq'::regclass);


--
-- Name: tekneler id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tekneler ALTER COLUMN id SET DEFAULT nextval('public.tekneler_id_seq'::regclass);


--
-- Name: baglamalar baglamalar_basvuru_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baglamalar
    ADD CONSTRAINT baglamalar_basvuru_token_key UNIQUE (basvuru_token);


--
-- Name: baglamalar baglamalar_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baglamalar
    ADD CONSTRAINT baglamalar_pkey PRIMARY KEY (id);


--
-- Name: baglamalar baglamalar_ref_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baglamalar
    ADD CONSTRAINT baglamalar_ref_no_key UNIQUE (ref_no);


--
-- Name: belgeler belgeler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.belgeler
    ADD CONSTRAINT belgeler_pkey PRIMARY KEY (id);


--
-- Name: faturalar faturalar_fatura_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faturalar
    ADD CONSTRAINT faturalar_fatura_no_key UNIQUE (fatura_no);


--
-- Name: faturalar faturalar_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faturalar
    ADD CONSTRAINT faturalar_pkey PRIMARY KEY (id);


--
-- Name: gunluk_kayitlar gunluk_kayitlar_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_kayitlar
    ADD CONSTRAINT gunluk_kayitlar_pkey PRIMARY KEY (id);


--
-- Name: gunluk_ozet gunluk_ozet_liman_id_tarih_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_ozet
    ADD CONSTRAINT gunluk_ozet_liman_id_tarih_key UNIQUE (liman_id, tarih);


--
-- Name: gunluk_ozet gunluk_ozet_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_ozet
    ADD CONSTRAINT gunluk_ozet_pkey PRIMARY KEY (id);


--
-- Name: izinler izinler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.izinler
    ADD CONSTRAINT izinler_pkey PRIMARY KEY (id);


--
-- Name: kullanicilar kullanicilar_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kullanicilar
    ADD CONSTRAINT kullanicilar_email_key UNIQUE (email);


--
-- Name: kullanicilar kullanicilar_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kullanicilar
    ADD CONSTRAINT kullanicilar_pkey PRIMARY KEY (id);


--
-- Name: liman_gunlugu liman_gunlugu_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.liman_gunlugu
    ADD CONSTRAINT liman_gunlugu_pkey PRIMARY KEY (id);


--
-- Name: limanlar limanlar_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.limanlar
    ADD CONSTRAINT limanlar_pkey PRIMARY KEY (id);


--
-- Name: personel_evraklari personel_evraklari_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personel_evraklari
    ADD CONSTRAINT personel_evraklari_pkey PRIMARY KEY (id);


--
-- Name: personel personel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personel
    ADD CONSTRAINT personel_pkey PRIMARY KEY (id);


--
-- Name: tekne_evraklari tekne_evraklari_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tekne_evraklari
    ADD CONSTRAINT tekne_evraklari_pkey PRIMARY KEY (id);


--
-- Name: tekneler tekneler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tekneler
    ADD CONSTRAINT tekneler_pkey PRIMARY KEY (id);


--
-- Name: tekneler tekneler_sicil_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tekneler
    ADD CONSTRAINT tekneler_sicil_no_key UNIQUE (sicil_no);


--
-- Name: baglamalar baglamalar_kullanici_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baglamalar
    ADD CONSTRAINT baglamalar_kullanici_id_fkey FOREIGN KEY (kullanici_id) REFERENCES public.kullanicilar(id) ON DELETE SET NULL;


--
-- Name: baglamalar baglamalar_liman_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baglamalar
    ADD CONSTRAINT baglamalar_liman_id_fkey FOREIGN KEY (liman_id) REFERENCES public.limanlar(id) ON DELETE CASCADE;


--
-- Name: baglamalar baglamalar_tekne_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baglamalar
    ADD CONSTRAINT baglamalar_tekne_id_fkey FOREIGN KEY (tekne_id) REFERENCES public.tekneler(id) ON DELETE CASCADE;


--
-- Name: belgeler belgeler_basvuru_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.belgeler
    ADD CONSTRAINT belgeler_basvuru_id_fkey FOREIGN KEY (basvuru_id) REFERENCES public.baglamalar(id) ON DELETE CASCADE;


--
-- Name: faturalar faturalar_baglama_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faturalar
    ADD CONSTRAINT faturalar_baglama_id_fkey FOREIGN KEY (baglama_id) REFERENCES public.baglamalar(id) ON DELETE SET NULL;


--
-- Name: faturalar faturalar_kullanici_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.faturalar
    ADD CONSTRAINT faturalar_kullanici_id_fkey FOREIGN KEY (kullanici_id) REFERENCES public.kullanicilar(id) ON DELETE SET NULL;


--
-- Name: gunluk_kayitlar gunluk_kayitlar_kullanici_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_kayitlar
    ADD CONSTRAINT gunluk_kayitlar_kullanici_id_fkey FOREIGN KEY (kullanici_id) REFERENCES public.kullanicilar(id) ON DELETE SET NULL;


--
-- Name: gunluk_kayitlar gunluk_kayitlar_liman_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_kayitlar
    ADD CONSTRAINT gunluk_kayitlar_liman_id_fkey FOREIGN KEY (liman_id) REFERENCES public.limanlar(id) ON DELETE CASCADE;


--
-- Name: gunluk_kayitlar gunluk_kayitlar_tekne_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_kayitlar
    ADD CONSTRAINT gunluk_kayitlar_tekne_id_fkey FOREIGN KEY (tekne_id) REFERENCES public.tekneler(id) ON DELETE SET NULL;


--
-- Name: gunluk_ozet gunluk_ozet_liman_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gunluk_ozet
    ADD CONSTRAINT gunluk_ozet_liman_id_fkey FOREIGN KEY (liman_id) REFERENCES public.limanlar(id) ON DELETE CASCADE;


--
-- Name: izinler izinler_personel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.izinler
    ADD CONSTRAINT izinler_personel_id_fkey FOREIGN KEY (personel_id) REFERENCES public.personel(id) ON DELETE CASCADE;


--
-- Name: liman_gunlugu liman_gunlugu_baglama_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.liman_gunlugu
    ADD CONSTRAINT liman_gunlugu_baglama_id_fkey FOREIGN KEY (baglama_id) REFERENCES public.baglamalar(id) ON DELETE SET NULL;


--
-- Name: liman_gunlugu liman_gunlugu_kullanici_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.liman_gunlugu
    ADD CONSTRAINT liman_gunlugu_kullanici_id_fkey FOREIGN KEY (kullanici_id) REFERENCES public.kullanicilar(id) ON DELETE SET NULL;


--
-- Name: liman_gunlugu liman_gunlugu_liman_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.liman_gunlugu
    ADD CONSTRAINT liman_gunlugu_liman_id_fkey FOREIGN KEY (liman_id) REFERENCES public.limanlar(id) ON DELETE CASCADE;


--
-- Name: personel_evraklari personel_evraklari_personel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personel_evraklari
    ADD CONSTRAINT personel_evraklari_personel_id_fkey FOREIGN KEY (personel_id) REFERENCES public.personel(id) ON DELETE CASCADE;


--
-- Name: tekne_evraklari tekne_evraklari_tekne_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tekne_evraklari
    ADD CONSTRAINT tekne_evraklari_tekne_id_fkey FOREIGN KEY (tekne_id) REFERENCES public.tekneler(id) ON DELETE CASCADE;


--
-- Name: tekneler tekneler_sahip_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tekneler
    ADD CONSTRAINT tekneler_sahip_id_fkey FOREIGN KEY (sahip_id) REFERENCES public.kullanicilar(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

