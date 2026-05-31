-- =============================================
-- ADIM 2: 21 isim güncellemesi (evlilik/soyadı değişikliği/yazım düzeltme)
-- DİKKAT: Bu güncellemeleri İK onayı sonrası çalıştırın!
-- Bazı satırlar büyük değişiklikler içeriyor (evlilik soyadı vb.)
-- Oluşturulma: 2026-05-31 20:12
-- =============================================
BEGIN;

UPDATE personel SET ad_soyad = 'GÜLÇİN YANPEŞ GÜZELKÖYLÜ' WHERE id = 309 AND tc_kimlik = '55036404704'; -- 'GÜLÇİN YANPEŞ' → 'GÜLÇİN YANPEŞ GÜZELKÖYLÜ'
UPDATE personel SET ad_soyad = 'BUĞSE SULTAN YÜKÜNÇ' WHERE id = 685 AND tc_kimlik = '15340915648'; -- 'BUSE SULTAN YÜKÜNÇ' → 'BUĞSE SULTAN YÜKÜNÇ'
UPDATE personel SET ad_soyad = 'NESLİHAN SÖGÜT' WHERE id = 255 AND tc_kimlik = '24815412254'; -- 'NESLİHAN SÖĞÜT' → 'NESLİHAN SÖGÜT'
UPDATE personel SET ad_soyad = 'İZEL POLAT' WHERE id = 428 AND tc_kimlik = '15865571930'; -- 'İZEL YIKILMAZ' → 'İZEL POLAT'
UPDATE personel SET ad_soyad = 'NECATİ FIRAT COŞKUN' WHERE id = 931 AND tc_kimlik = '44200762948'; -- 'NECATİ FIRAT ÇOŞKUN' → 'NECATİ FIRAT COŞKUN'
UPDATE personel SET ad_soyad = 'ÖZLEM ÇİFTÇİ' WHERE id = 437 AND tc_kimlik = '26245231634'; -- 'ÖZLEM CAN' → 'ÖZLEM ÇİFTÇİ'
UPDATE personel SET ad_soyad = 'NURSEL TURGUT TOSUN' WHERE id = 354 AND tc_kimlik = '41611844942'; -- 'NURSEL TURGUT' → 'NURSEL TURGUT TOSUN'
UPDATE personel SET ad_soyad = 'ELİF ÖZCAN' WHERE id = 31 AND tc_kimlik = '12497817368'; -- 'ELİF BAŞAL' → 'ELİF ÖZCAN'
UPDATE personel SET ad_soyad = 'FUNDA ECE BULUT' WHERE id = 734 AND tc_kimlik = '41998828986'; -- 'FUNDA ECE ÇATAK' → 'FUNDA ECE BULUT'
UPDATE personel SET ad_soyad = 'ÇOŞKUN GÖKTEPE' WHERE id = 181 AND tc_kimlik = '37210991552'; -- 'COŞKUN GÖKTEPE' → 'ÇOŞKUN GÖKTEPE'
UPDATE personel SET ad_soyad = 'TUĞBA NUR GÖKMEN' WHERE id = 261 AND tc_kimlik = '28172289504'; -- 'TUĞBANUR GÖKMEN' → 'TUĞBA NUR GÖKMEN'
UPDATE personel SET ad_soyad = 'GÜLDEMET AYDIN TANIŞ' WHERE id = 113 AND tc_kimlik = '32306161260'; -- 'GÜLDEMET AYDIN' → 'GÜLDEMET AYDIN TANIŞ'
UPDATE personel SET ad_soyad = 'ŞÜKRAN NURAL' WHERE id = 646 AND tc_kimlik = '19975415146'; -- 'ŞÜKRAN FADILLIOĞLU' → 'ŞÜKRAN NURAL'
UPDATE personel SET ad_soyad = 'İZEL BAŞAL' WHERE id = 854 AND tc_kimlik = '65590047804'; -- 'İZEL İLHAN' → 'İZEL BAŞAL'
UPDATE personel SET ad_soyad = 'ESMA SÖGÜT' WHERE id = 403 AND tc_kimlik = '24818412190'; -- 'ESMA SÖĞÜT' → 'ESMA SÖGÜT'
UPDATE personel SET ad_soyad = 'ARMAĞAN OLGUN KURKMAZ' WHERE id = 699 AND tc_kimlik = '17651645634'; -- 'ARMAĞAN OLGUN KORKMAZ' → 'ARMAĞAN OLGUN KURKMAZ'
UPDATE personel SET ad_soyad = 'FUNDA GAZAN' WHERE id = 915 AND tc_kimlik = '26312264466'; -- 'FUNDA KAZAN' → 'FUNDA GAZAN'
UPDATE personel SET ad_soyad = 'AYŞEN KULAKSIZOĞLU' WHERE id = 811 AND tc_kimlik = '52450490290'; -- 'AYŞEN BAYDOĞAN' → 'AYŞEN KULAKSIZOĞLU'
UPDATE personel SET ad_soyad = 'ZÜLCE ÇİZME' WHERE id = 765 AND tc_kimlik = '33065129874'; -- 'ZÜLCE ESKİCİ' → 'ZÜLCE ÇİZME'
UPDATE personel SET ad_soyad = 'HAKİME İŞİN ÇOBAN' WHERE id = 688 AND tc_kimlik = '13864618670'; -- 'HAKİME İŞİN' → 'HAKİME İŞİN ÇOBAN'
UPDATE personel SET ad_soyad = 'AYŞE MEMİÇOĞLU' WHERE id = 649 AND tc_kimlik = '60340215472'; -- 'AYŞE ERDOĞAN' → 'AYŞE MEMİÇOĞLU'

-- Doğrulama
SELECT id, ad_soyad, tc_kimlik FROM personel WHERE id IN (309, 685, 255, 428, 931, 437, 354, 31, 734, 181, 261, 113, 646, 854, 403, 699, 915, 811, 765, 688, 649) ORDER BY ad_soyad;

-- İK onayı verdiyse: COMMIT;
-- Tereddüt varsa: ROLLBACK;