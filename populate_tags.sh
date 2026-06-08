#!/bin/sh

export FLASK_ENV="setup"
export TYPESENSE_API_KEY="asdfg"

python -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/makeascene')
cur = conn.cursor()
cur.execute('TRUNCATE TABLE tags RESTART IDENTITY CASCADE;')
conn.commit()
cur.close()
conn.close()
print('Tags table cleared.')
"

flask run