APP_NAME=wsgi:app
BIND_ADDRESS=0.0.0.0:5000
ACCESS_LOGFILE=./access.log
ERROR_LOGFILE=./error.log

# Command to run Gunicorn
run_gunicorn:
	@echo "Starting Gunicorn..."
	gunicorn $(APP_NAME) \
		-D \
		--bind $(BIND_ADDRESS) \
		--worker-class eventlet \
		-w 1 \
		--access-logfile $(ACCESS_LOGFILE) \
		--error-logfile $(ERROR_LOGFILE) \

# Command to kill all active Gunicorn processes
kill_gunicorn:
	@echo "Killing all Gunicorn processes..."
	pkill gunicorn || echo "No active Gunicorn processes found."

# Command to see active Gunicorn processes
status_gunicorn:
	@echo "Checking for active Gunicorn processes..."
	ps aux | grep gunicorn | grep -v grep || echo "No active Gunicorn processes found."
