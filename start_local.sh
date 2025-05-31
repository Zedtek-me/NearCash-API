#!bin/sh

echo "running migrations"
python3 -m manage makemigrations --noinput
python3 -m manage migrate --noinput
echo "starting server..."
python3 -m manage runserver 3000