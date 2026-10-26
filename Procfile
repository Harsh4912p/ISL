web: gunicorn wsgi:app -k gthread --threads 4 --workers 1 --timeout 120 --access-logfile - --error-logfile -
release: python init_db.py
