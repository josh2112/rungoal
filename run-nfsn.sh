exec /home/protected/rungoal/api/.venv/bin/uvicorn \
	rungoal.main:app \
	--host 127.0.0.1 \
	--port 8400 \
	--proxy-headers \
	--forwarded-allow-ips='*' \
	--root-path /rungoal
