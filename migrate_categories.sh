#!/bin/bash
# Run this on the server after git pull + docker-compose up -d --build

# Fix nginx port conflict if needed
docker-compose down && docker-compose up -d

# Migrate category codes in DB
docker-compose exec app python3 -c "
import db
conn = db.get_db()
for old in ('1B','1C','1D','1E'):
    conn.execute('UPDATE mistakes SET category=? WHERE category=?', ('1A', old))
for old, new in [('5B','6B'),('5A','6A'),('4B','5B'),('4A','5A'),('3C','4C'),('3B','4B'),('3A','4A'),('2C','3C'),('2B','3B'),('2A','3A'),('1V','2A')]:
    conn.execute('UPDATE mistakes SET category=? WHERE category=?', (new, old))
conn.commit()
conn.close()
print('Categories migrated')
"

# Recompute stats for all games
docker-compose exec app python3 -c "
import db
conn = db.get_db()
for g in conn.execute('SELECT id FROM games').fetchall():
    db.compute_summary_for_game(conn, g['id'])
conn.close()
print('Stats recomputed')
"
