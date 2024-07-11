# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import os
import ssl
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv

from pythreads.threads import Threads

load_dotenv()

THREADS_HOST = os.getenv("THREADS_HOST")


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        requested_url = f"https://{THREADS_HOST}/{self.path}"

        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/":
            auth_link, state = Threads.authorization_url()
            # Serve the form
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Set-Cookie", f"threads_state={state}; Path=/")
            self.end_headers()
            html_form = f"""
                <html>
                <body>
                    <a href="{auth_link}">Authenticate</a>
                </body>
                </html>
            """
            self.wfile.write(html_form.encode("utf-8"))
        elif parsed_path.path == "/favicon.ico":
            self.send_response(404)
            self.end_headers()
        else:
            state = None
            cookie_header = self.headers.get("Cookie")
            if cookie_header:
                cookies = dict(
                    cookie.strip().split("=") for cookie in cookie_header.split(";")
                )
                state = cookies.get("threads_state")
            else:
                raise RuntimeError("No cookies found")

            if state is None:
                raise RuntimeError("No threads_state cookie found")
            credentials = Threads.complete_authorization(requested_url, state=state)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            response = f"""
                <html>
                <body>
                    <h1>Authorization</h1>
                    <p>Successfully completed authorization. Save the following environment variables to reuse this session for the life of the long-lived token:</p>
                    <pre>
THREADS_SMOKE_TEST_USER_ID={credentials.user_id}
THREADS_SMOKE_TEST_TOKEN={credentials.access_token}
                    </pre>
                    <p>This token will be good until: {credentials.expiration.strftime("%Y-%m-%d")}</p>
                </body>
                </html>
            """
            self.wfile.write(response.encode("utf-8"))


def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    certfile = os.getenv("THREADS_SSL_CERT_FILEPATH")
    keyfile = os.getenv("THREADS_SSL_KEY_FILEPATH")

    if certfile is None or keyfile is None:
        raise RuntimeError(
            "You must provide both a THREADS_SSL_CERT_FILEPATH and THREADS_SSL_KEY_FILEPATH. The OAuth flow must be run in an SSL context."
        )

    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"Starting httpd server on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
