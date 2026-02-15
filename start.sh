#!bin/sh

echo "running migrations"
python3 -m manage migrate --noinput
python3 -m manage collectstatic --noinput --clear --link
echo "starting server..."
daphne near_cash.asgi:application --bind 0.0.0.0:3000 --workers 4 \
    --worker-class gevent --timeout 120 --keep-alive 5 \
    --log-level info --access-logfile - --error-logfile -