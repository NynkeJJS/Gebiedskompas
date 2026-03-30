-- Clean up deprecated Kompas mappings
-- We used to have empty placeholders (Weging 1.0) which interfere with new real data.

DELETE FROM kompas_indicator_mapping
WHERE onderdeel_id IN (26, 27) 
AND weging = 1.0
AND indicator_uuid NOT IN (
    SELECT uuid FROM indicatoren WHERE code LIKE 'bag_%'
);
