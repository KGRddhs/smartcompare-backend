web: exec env UV_THREADPOOL_SIZE="${UV_THREADPOOL_SIZE:-64}" uvicorn app.main:app --host 0.0.0.0 --port $PORT --timeout-graceful-shutdown 20 --limit-concurrency "${UVICORN_LIMIT_CONCURRENCY:-512}"
