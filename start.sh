#!bin/sh

echo "running migrations"
python3 -m manage migrate --noinput
echo "starting server..."
gunicorn near_cash.wsgi:application --bind 0.0.0.0:3000 --workers 4 \
    --worker-class gevent --timeout 120 --keep-alive 5 \
    --log-level info --access-logfile - --error-logfile -