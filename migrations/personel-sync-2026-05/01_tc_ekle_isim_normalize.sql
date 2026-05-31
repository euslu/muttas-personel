-- =============================================
-- ADIM 1: TC'siz 6 kayda TC ekleme + isim normalize
-- Oluşturulma: 2026-05-31 20:12
-- =============================================
BEGIN;

-- Önce mevcut hali görelim (DRY RUN kontrol için)
SELECT id, ad_soyad, tc_kimlik FROM personel WHERE id IN (952, 953, 789, 869, 939, 954);

-- TC ekleme ve isim düzeltmeleri
UPDATE personel SET tc_kimlik = '23900138826' WHERE id = 952; -- ATİYE DİKER
UPDATE personel SET tc_kimlik = '46051704412' WHERE id = 953; -- HÜSEYİN USLU
UPDATE personel SET tc_kimlik = '21130126118' WHERE id = 789; -- MEHMET REFİK PARLAK
UPDATE personel SET tc_kimlik = '52270484608', ad_soyad = 'MELİH DEVECİ' WHERE id = 869; -- 'MELİH  DEVECİ' → 'MELİH DEVECİ'
UPDATE personel SET tc_kimlik = '26219358916', ad_soyad = 'SÜLEYMAN KORTUN' WHERE id = 939; -- 'SÜLEYMAN  KORTUN' → 'SÜLEYMAN KORTUN'
UPDATE personel SET tc_kimlik = '11612840250' WHERE id = 954; -- ZEHRA ÇAMOĞLU

-- Doğrulama
SELECT id, ad_soyad, tc_kimlik FROM personel WHERE id IN (952, 953, 789, 869, 939, 954);

-- Her şey iyi görünüyorsa: COMMIT;
-- Sorun varsa: ROLLBACK;