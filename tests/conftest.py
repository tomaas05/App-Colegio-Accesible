import os

# Playwright (síncrono) y el servidor de pruebas de Django comparten hilo en
# las pruebas e2e; sin esto Django protesta con SynchronousOnlyOperation.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
