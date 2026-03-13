"""CLI entry point for probe37."""
import asyncio
import logging
import threading
import click
import uvicorn
from probe37.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("probe37")


@click.group()
def main():
    """probe37 — pentest suite for humans and LLMs."""
    pass


@main.command()
@click.option("--proxy-port", default=8080, help="Proxy listen port")
@click.option("--api-port", default=8037, help="API/dashboard port")
@click.option("--host", default="0.0.0.0", help="Listen host")
def start(proxy_port: int, api_port: int, host: str):
    """Start probe37 (proxy + API server)."""
    from probe37.proxy.engine import ProxyEngine
    from probe37.api.server import app, proxy_listener

    init_db()
    logger.info("probe37 v0.1.0 starting up...")
    logger.info(f"  Proxy:     http://{host}:{proxy_port}")
    logger.info(f"  Dashboard: http://{host}:{api_port}")
    logger.info(f"  API:       http://{host}:{api_port}/api/")
    logger.info(f"  WebSocket: ws://{host}:{api_port}/ws")

    # Start proxy in background thread
    proxy = ProxyEngine(listen_host=host, listen_port=proxy_port)
    proxy.addon.add_listener(proxy_listener)

    def run_proxy():
        asyncio.run(proxy.start())

    proxy_thread = threading.Thread(target=run_proxy, daemon=True)
    proxy_thread.start()

    # Run API server in main thread
    uvicorn.run(app, host=host, port=api_port, log_level="info")


@main.command()
@click.option("--port", default=8037, help="API port")
@click.option("--host", default="0.0.0.0", help="Listen host")
def api_only(port: int, host: str):
    """Start only the API server (no proxy)."""
    from probe37.api.server import app
    init_db()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
