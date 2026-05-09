import http.server

class MockAzureHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        print(f"\nRECEIVED_PATH: {self.path}")
        print(f"RECEIVED_HEADERS: {dict(self.headers)}")
        print(f"RECEIVED_PAYLOAD: {body.decode('utf-8')[:200]}...")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "captured"}')

http.server.HTTPServer(('127.0.0.1', 8080), MockAzureHandler).handle_request()
