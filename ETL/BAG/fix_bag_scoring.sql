-- Fix missing scoring rules for BAG indicators (Kompas crash fix)
-- Oorzaak: v_kompas_hierarchie haalt score_type uit kompas_indicator_scoring_regels, 
-- maar deze records waren niet aangemaakt voor de BAG indicatoren.

-- 1. Maak scoring regels aan voor de 15 BAG indicatoren (config_id = 1)
-- Score type: 'threshold_based' (omdat we thresholds kunnen gebruiken, of 'positive_ascending'?)
-- Eerder zagen we: CHECK (((score_type)::text = ANY ((ARRAY['positive_ascending'::character varying, 'positive_descending'::character varying, 'threshold_based'::character varying, 'custom'::character varying])::text[])))
-- Laten we 'positive_ascending' gebruiken voor "meer is beter/meer", of 'threshold_based' met dummy thresholds.
-- Voor 'Aantal' indicatoren is 'positive_ascending' logisch.

INSERT INTO kompas_indicator_scoring_regels (indicator_uuid, config_id, score_type, eenheid, created_at, updated_at)
SELECT 
    i.uuid, 
    1, 
    'positive_ascending', -- Meer woningen/functies = hogere balk/taartpunt? Of gewoon 'informatief'. 
    i.eenheid,
    NOW(),
    NOW()
FROM indicatoren i
WHERE i.code IN (
    -- Bouwperiodes
    'bag_bouwjaar_voor_1915', 'bag_bouwjaar_1915_1945', 'bag_bouwjaar_1945_1984', 'bag_bouwjaar_vanaf_1985',
    -- Functies
    'bag_functie_woon', 'bag_functie_bijeenkomst', 'bag_functie_cel', 'bag_functie_gezondheid',
    'bag_functie_industrie', 'bag_functie_kantoor', 'bag_functie_logies', 'bag_functie_onderwijs',
    'bag_functie_sport', 'bag_functie_winkel', 'bag_functie_overige'
)
ON CONFLICT (indicator_uuid, config_id) 
DO UPDATE SET score_type = 'positive_ascending', updated_at = NOW();

-- Check of we ook thresholds moeten invullen (JSON)? 
-- Voor 'positive_ascending' is dat misschien niet verplicht.
-- Maar voor 'threshold_based' wel.

-- Laten we verifiëren wat er nu in zit.
-- Voor de zekerheid zetten we ook de 'indicatoren' tabel score_type (hoewel de view die negeert, maar voor consistentie)
UPDATE indicatoren SET score_type = '+/+' WHERE code IN (
    'bag_bouwjaar_voor_1915', 'bag_bouwjaar_1915_1945', 'bag_bouwjaar_1945_1984', 'bag_bouwjaar_vanaf_1985',
    'bag_functie_woon', 'bag_functie_bijeenkomst', 'bag_functie_cel', 'bag_functie_gezondheid',
    'bag_functie_industrie', 'bag_functie_kantoor', 'bag_functie_logies', 'bag_functie_onderwijs',
    'bag_functie_sport', 'bag_functie_winkel', 'bag_functie_overige'
);
