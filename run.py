from app import create_app
from config import Config
from urllib.parse import urlparse

app = create_app()

if __name__ == '__main__':
    parsed_url = urlparse(Config.LOCAL_URL)
    host = parsed_url.hostname or "127.0.0.1"
    port = parsed_url.port or 5000

    print(f"Server running at: {Config.LOCAL_URL}")
    app.run(host=host, port=port, debug=True,use_reloader=True)
