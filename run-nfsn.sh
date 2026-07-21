cd /home/protected/rungoal/api/

# Create/upgrade the database
mkdir -p ../data
.venv/bin/alembic upgrade head

# Start uvicorn (requests to [domain]/rungoal are proxied to port 8400 in the NFSN console)
exec .venv/bin/uvicorn \
	rungoal.main:app \
	--host 127.0.0.1 \
	--port 8400 \
	--proxy-headers \
	--no-access-log \
	--forwarded-allow-ips='*' \
	--root-path='/rungoal'
