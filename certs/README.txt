Certificates in this directory should only be used for testing in
loopback mode (using https://localhost/ for URL). For real deployment
you must generate your own certificates and have them signed
by proper certification authority.

To generate your own self-signed certificate type this:

openssl req -x509 -sha256 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 65536 -nodes

This certificate will be valid for 65536 days (about 180 years) and the private key
will not be password-protected

