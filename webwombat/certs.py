from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import ssl
import datetime
import os
import code
from pathlib import Path
from functools import lru_cache

certificates = {}
OPTIONS = {
        "common_name": "Hogwart's Muggle Root Authority",
        # "business_category": "nunya",
        "country_name": "UK",
        # "domain_component": ".",
        # "email_address": "arthur.weasely@hogwarts.edu",
        # "locality_name": "Hogwarts",
        # "postal_address": "<unplottable>",
        # "street_address": "<unplottable>",
        # "given_name": "Arthur",
        # "surname": "Weasely",
        # "title": "Department Head",
}

# def load_cached_certs():
#     global certificates
#     certdir = Path("~/.cache/wombat/").expanduser()
#     if not certdir.exists(): os.mkdir(certdir)
#     for filename in certdir.glob("*.pem"):
#         custom_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#         keyfilename = str(filename).rstrip(".pem") + ".key"
#         custom_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
#         certificates[filename.name.rstrip(".pem")] = custom_context

#     print('loaded certificates from cache', list(certificates.keys()))

def gen_root_CA(options, expiry, serial_number):
    outputdir = Path("~/.config/wombat/").expanduser()
    if not outputdir.exists(): os.mkdir(outputdir)

    # generate keys
    private_key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public_key = private_key.public_key()

    # make certificate
    builder = x509.CertificateBuilder()
    metadata = [x509.NameAttribute(getattr(NameOID, k.upper()), v) for k, v in options.items()]
    builder = builder.subject_name(x509.Name(metadata))
    builder = builder.issuer_name(x509.Name(metadata))
    builder = builder.not_valid_before(datetime.datetime(1997, 5, 26))
    builder = builder.not_valid_after(datetime.datetime(*expiry))
    builder = builder.serial_number(serial_number)
    builder = builder.public_key(public_key)
    builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None),critical=True)

    # self sign
    certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256())

    # export private key and cert
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    cert_bytes = certificate.public_bytes(encoding=serialization.Encoding.PEM,)
    with open(outputdir / "ca_key.pem", "wb") as fout:
        fout.write(private_key_bytes)
    with open(outputdir / "ca_cert.pem", "wb") as fout:
        fout.write(cert_bytes)

    # return the provate key and certificate
    return private_key, certificate

@lru_cache(maxsize=None)
def get_CA():
    outputdir = Path("~/.config/wombat/").expanduser()
    if outputdir.exists() and (outputdir / "ca_key.pem").is_file() and (outputdir / "ca_cert.pem").is_file():
        with open(outputdir / "ca_key.pem", 'rb') as pemfile:
            private_key = serialization.load_pem_private_key(pemfile.read(), None)
        with open(outputdir / "ca_cert.pem", 'rb') as pemfile:
            cert = x509.load_pem_x509_certificate(pemfile.read())
        return private_key, cert
    else:
        return gen_root_CA(OPTIONS, (2030, 1, 1), 62442)


def new_cert(domain, expiry=(2030, 1, 1)):
    global certificates

    private_key, ca_certificate = get_CA()

    certdir = Path("~/.cache/wombat/").expanduser()
    service_private_key = rsa.generate_private_key(public_exponent=65537,key_size=2048,)
    service_public_key = service_private_key.public_key()
    builder = x509.CertificateBuilder()
    metadata = [x509.NameAttribute(getattr(NameOID, k.upper()), v) for k, v in OPTIONS.items()] 
    builder = builder.subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
    builder = builder.issuer_name(x509.Name(metadata))
    builder = builder.not_valid_before(datetime.datetime(1997, 5, 26))
    builder = builder.not_valid_after(datetime.datetime(*expiry))
    builder = builder.public_key(service_public_key)
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]),critical=False)
    certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256(),)
    private_bytes = service_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    cert_bytes = certificate.public_bytes(encoding=serialization.Encoding.PEM)
    with open(certdir / f"{domain}.pem", "wb") as fout:
        ca_cert_bytes = ca_certificate.public_bytes(encoding=serialization.Encoding.PEM)
        fout.write(cert_bytes + ca_cert_bytes)
    with open(certdir / f"{domain}.key", "wb") as fout:
        fout.write(private_bytes)

def handle_ssl(sock, hostname, _):
    certdir = Path("~/.cache/wombat/").expanduser()
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    if not (certdir / f"{hostname}.pem").is_file():
        new_cert(hostname)
    context.load_cert_chain(
        certfile=certdir / f"{hostname}.pem",
        keyfile=certdir / f"{hostname}.key",
    )
    sock.context = context
