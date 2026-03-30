-- Calculate Percentage Energy Labels based on Households
-- Formula: (Aantal energielabels / Huishoudens totaal) * 100

-- 1. Create Indicator if not exists
DO $$
DECLARE
    ind_uuid UUID;
BEGIN
    SELECT uuid INTO ind_uuid FROM indicatoren WHERE naam = 'Percentage met energielabel';
    
    IF ind_uuid IS NULL THEN
        INSERT INTO indicatoren (naam, code, eenheid, omschrijving, bron, interpretatie_logica)
        VALUES (
            'Percentage met energielabel', 
            'percentage_energielabel',
            '%',
            'Percentage woningen met een geregistreerd energielabel (t.o.v. aantal huishoudens)',
            'RVO EP-Online / CBS',
            '+/+'
        ) RETURNING uuid INTO ind_uuid;
        RAISE NOTICE 'Created indicator Percentage met energielabel: %', ind_uuid;
    END IF;
END $$;

-- Delete existing records for this indicator and year
DELETE FROM gebied_data 
WHERE indicator_uuid = (SELECT uuid FROM indicatoren WHERE naam = 'Percentage met energielabel')
  AND jaar = 2025;

-- Insert new calculations
WITH label_counts AS (
    SELECT 
        gd.gebied_id, 
        gd.waarde as aantal_labels
    FROM gebied_data gd
    JOIN indicatoren i ON gd.indicator_uuid = i.uuid
    WHERE i.naam = 'Aantal energielabels' AND gd.jaar = 2025
),
households AS (
    SELECT 
        gd.gebied_id, 
        gd.waarde as aantal_huishoudens
    FROM gebied_data gd
    JOIN indicatoren i ON gd.indicator_uuid = i.uuid
    WHERE i.naam = 'Huishoudens totaal'
    -- Note: Household data might be from older years (e.g. 2024), we take the most recent
    AND gd.jaar = (SELECT MAX(jaar) FROM gebied_data WHERE indicator_uuid = i.uuid)
),
percentage_calc AS (
    SELECT 
        l.gebied_id,
        l.aantal_labels,
        h.aantal_huishoudens,
        CASE 
            WHEN h.aantal_huishoudens > 0 THEN (l.aantal_labels / h.aantal_huishoudens) * 100
            ELSE 0 
        END as percentage
    FROM label_counts l
    JOIN households h ON l.gebied_id = h.gebied_id
)
INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron)
SELECT 
    pc.gebied_id, 
    (SELECT uuid FROM indicatoren WHERE naam = 'Percentage met energielabel'),
    pc.percentage,
    2025,
    'Berekening (RVO/CBS)'
FROM percentage_calc pc;

-- 3. Verification Output
SELECT 
    COUNT(*) as total_calculated,
    AVG(waarde) as avg_percentage,
    MIN(waarde) as min_percentage,
    MAX(waarde) as max_percentage
FROM gebied_data 
WHERE indicator_uuid = (SELECT uuid FROM indicatoren WHERE naam = 'Percentage met energielabel');
