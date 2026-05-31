-- =============================================
-- ADIM 3: Yeni personel ekleme (Mayıs 2026'da var, DB'de yok)
-- ÖNEMLİ: Bu SQL'i Adım 1'den SONRA çalıştırın.
-- Adım 1'de TC'si eklenmiş kayıtlar bu listeden ÇIKARILDI.
-- Oluşturulma: 2026-05-31 20:14
-- Toplam: 46 yeni kayıt
-- =============================================
BEGIN;

-- Önce TC'lerin DB'de olmadığını doğrula (boş dönmeli)
SELECT tc_kimlik, ad_soyad FROM personel WHERE tc_kimlik IN (
  '51364514818', '28685273090', '22061161650', '58711269964', '25397188766', '30392213610', '28034299344', '60712214812', '48769603148', '61243192266', '13588956904', '52306489546', '39616908776', '25252025182', '36227045302', '58735201056', '60499210304', '57331318472', '41791439266', '20351554724', '33854100756', '10714091058', '53197455740', '64729076326', '33329118460', '10205890016', '46987663302', '43537782728', '46981667658', '27497321982', '47662643558', '24860404952', '35288057514', '47584649782', '56941409198', '42226826170', '14381754452', '43948774220', '21749198438', '24569414870', '17959505630', '40828873066', '51130762252', '40069900514', '42013833688', '18196866140'
);

-- Eklemeler
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ALİ KONYA', '51364514818', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ASİYE BİNİCİ', '28685273090', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('BERNA TARHAN', '22061161650', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-04-29', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('CENKER YÖNDEM', '58711269964', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('DİCLESU ŞİMŞEK', '25397188766', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-05-12', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('FERDİ TANER', '30392213610', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-04-01', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('GÖRKEM BARUT', '28034299344', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('GÜLCAN TAŞ', '60712214812', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('SELMAN DEMİRCİ', '48769603148', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('SONAY GÜNÜÇ', '61243192266', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('UMUT ENGEL', '13588956904', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('YASİN MEHMET ŞAHİN', '52306489546', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ÖMER ÖZENÇ', '39616908776', 'BEDEN İŞÇİSİ (TEMİZLİK)', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ALİ BEDİRHAN TOPAN', '25252025182', 'BÜRO MEMURU', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('MİRAY BEYZA ÜNSAL', '36227045302', 'BÜRO MEMURU', 'TOPLU TAŞIMA', '2026-02-19', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('TUĞÇE MERVE AYDIN', '58735201056', 'BÜRO MEMURU', 'TOPLU TAŞIMA', '2026-04-01', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ÖZGE TÜRK', '60499210304', 'BÜRO MEMURU', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('BETÜL KURT', '57331318472', 'MİSAFİR İLİŞKİLERİ GÖREVLİSİ', 'DENİZ KIYI', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ERHAN SIRSAT', '41791439266', 'MİSAFİR İLİŞKİLERİ GÖREVLİSİ', 'DENİZ KIYI', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('HAMDİ YAVUZ', '20351554724', 'PALAMARCI', 'DENİZ KIYI', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('HASAN KÜÇÜK', '33854100756', 'PALAMARCI', 'DENİZ KIYI', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('MERTCAN OSMAN ÖZTEKİN', '10714091058', 'PALAMARCI', 'DENİZ KIYI', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ARİFE GÜL HASTA', '53197455740', 'PARKOMAT GÖREVLİSİ', 'PARKOMAT', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('MEHMET DEMİRTAŞ', '64729076326', 'PARKOMAT GÖREVLİSİ', 'PARKOMAT', '2024-07-09', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ONUR ERDOĞAN', '33329118460', 'PARKOMAT GÖREVLİSİ', 'PARKOMAT', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('SAHRA ÇATAL', '10205890016', 'PARKOMAT GÖREVLİSİ', 'PARKOMAT', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('SEMİH YİĞİT', '46987663302', 'PARKOMAT GÖREVLİSİ', 'PARKOMAT', '2026-04-01', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('AHMET ERCAN', '43537782728', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('AHMET KILINÇ', '46981667658', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('ALİ GÖKÇE', '27497321982', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('BAHATTİN HASAN TÜRKÖZ', '47662643558', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('BEKİR ERDİNÇ', '24860404952', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('BİLAL URHAN', '35288057514', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-04-01', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('DURMUŞ ALİ AKÇA', '47584649782', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('EMRE CEYLAN', '56941409198', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('EMRE KAYA', '42226826170', 'ŞOFÖR', 'TOPLU TAŞIMA', '2020-11-03', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('GÜLİZ İLHAN', '14381754452', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('HAKAN KAHRAMAN', '43948774220', 'ŞOFÖR', 'TOPLU TAŞIMA', '2020-10-20', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('KUBİLAY HAN YENİSOY', '21749198438', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-04-01', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('KUDRET DEMİRTAŞ', '24569414870', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-04-01', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('MURAT ÖZTEKİN', '17959505630', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('SERBÜLENT KAYA', '40828873066', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('UMUTCAN ÇETİN', '51130762252', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('YUSUF YAPICI', '40069900514', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('İBRAHİM KARAKAYA', '42013833688', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-11', TRUE);
INSERT INTO personel (ad_soyad, tc_kimlik, unvan, bolum, ise_giris, aktif) VALUES ('İDRİS ASLAN', '18196866140', 'ŞOFÖR', 'TOPLU TAŞIMA', '2026-03-12', TRUE);

-- Doğrulama (sonuç eklenen kayıt sayısı kadar olmalı)
SELECT COUNT(*) AS eklenen FROM personel WHERE tc_kimlik IN (
  '51364514818', '28685273090', '22061161650', '58711269964', '25397188766', '30392213610', '28034299344', '60712214812', '48769603148', '61243192266', '13588956904', '52306489546', '39616908776', '25252025182', '36227045302', '58735201056', '60499210304', '57331318472', '41791439266', '20351554724', '33854100756', '10714091058', '53197455740', '64729076326', '33329118460', '10205890016', '46987663302', '43537782728', '46981667658', '27497321982', '47662643558', '24860404952', '35288057514', '47584649782', '56941409198', '42226826170', '14381754452', '43948774220', '21749198438', '24569414870', '17959505630', '40828873066', '51130762252', '40069900514', '42013833688', '18196866140'
);  -- Beklenen: 46

-- Her şey iyi görünüyorsa: COMMIT;
-- Aksi: ROLLBACK;