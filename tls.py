import ssl


class LazyHandshakeContext(ssl.SSLContext):
	# Flask's dev server would otherwise do the TLS handshake inside its single accept loop,
	# so one idle browser connection blocks everyone. This defers it to each request thread.
	def wrap_socket(self, sock, **kwargs):
		kwargs['do_handshake_on_connect'] = False
		return super().wrap_socket(sock, **kwargs)


def context(cert='studio-cert.pem', key='studio-key.pem'):
	ctx = LazyHandshakeContext(ssl.PROTOCOL_TLS_SERVER)
	ctx.load_cert_chain(cert, key)
	return ctx
