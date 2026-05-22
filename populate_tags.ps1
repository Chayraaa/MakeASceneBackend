$env:FLASK_ENV = "setup"
$env:TYPESENSE_API_KEY = "xyz-super-secret-key"

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