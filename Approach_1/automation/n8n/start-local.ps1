$env:N8N_SECURE_COOKIE = "false"
$env:N8N_DIAGNOSTICS_ENABLED = "false"
$env:N8N_VERSION_NOTIFICATIONS_ENABLED = "false"
$env:N8N_RUNNERS_ENABLED = "true"
$env:DB_SQLITE_POOL_SIZE = "1"
$env:GENERIC_TIMEZONE = "Asia/Kolkata"
$env:TZ = "Asia/Kolkata"

npx --yes n8n@1.114.4
