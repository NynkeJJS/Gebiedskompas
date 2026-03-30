#!/bin/bash
# Backup script voor Kompas v3 tabellen
# Voor migratie naar v4

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="data/backups"
BACKUP_FILE="$BACKUP_DIR/backup_kompas_v3_$TIMESTAMP.sql"

echo "🔄 Creating backup of Kompas v3 tables..."
echo "Backup location: $BACKUP_FILE"

# Maak backup directory als die niet bestaat
mkdir -p "$BACKUP_DIR"

# Backup alleen kompas tabellen (zonder wachtwoord prompt in script)
# LET OP: Gebruik ~/.pgpass of PGPASSWORD omgevingsvariabele
pg_dump -U omnitwin_user -h localhost -d omnitwin_db \
  -t kompas_titels \
  -t kompas_themas \
  -t kompas_onderdelen \
  -t kompas_extra_onderdelen \
  -t kompas_indicator_mapping \
  -t kompas_indicator_extra_tags \
  --no-owner --no-acl \
  > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup succesvol: $BACKUP_FILE"
    ls -lh "$BACKUP_FILE"
else
    echo "❌ Backup gefaald!"
    exit 1
fi
