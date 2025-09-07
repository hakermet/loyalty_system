#!/bin/bash

# Exit on any error
set -e

echo "Starting Django application..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --settings=loyalty_system.settings_production

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=loyalty_system.settings_production

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell --settings=loyalty_system.settings_production << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
EOF

echo "Starting Gunicorn server..."
# Start Gunicorn
exec gunicorn loyalty_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -