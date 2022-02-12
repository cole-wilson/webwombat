from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from .config import get_config
import ssl
import datetime
import os
from pathlib import Path
from functools import lru_cache

def generate_root_certificate():
    """given a set of options and an expiration date, create a root certificate and private key to sign secondary certs"""
    config = get_config()
    options = {
        "COMMON_NAME": config.ca_name,
        "COUNTRY_NAME": config.cert_country,
        "EMAIL_ADDRESS": config.cert_email,
        "DN_QUALIFIER": "."
    }
    
    # setup output directory
    outputdir = Path(config.cacertdir).expanduser()
    if not outputdir.exists():
        os.makedirs(outputdir)

    # generate keys
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # make certificate
    builder = x509.CertificateBuilder()
    metadata = [x509.NameAttribute(getattr(NameOID, k.upper()), v) for k, v in options.items()]
    builder = builder.subject_name(x509.Name(metadata))
    builder = builder.issuer_name(x509.Name(metadata))
    builder = builder.not_valid_before(datetime.datetime.now())
    builder = builder.not_valid_after(datetime.datetime.now() + datetime.timedelta(10*365))
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(public_key)
    builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None),critical=True)

    # self sign the certificate
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
def get_root_certificate():
    config = get_config()
    outputdir = Path(config.cacertdir).expanduser()

    # check if we already have them
    if outputdir.exists() and (outputdir / "ca_key.pem").is_file() and (outputdir / "ca_cert.pem").is_file():
        with open(outputdir / "ca_key.pem", 'rb') as pemfile:
            private_key = serialization.load_pem_private_key(pemfile.read(), None)
        with open(outputdir / "ca_cert.pem", 'rb') as pemfile:
            cert = x509.load_pem_x509_certificate(pemfile.read())
        return private_key, cert

    # otherwise we make them
    else:
        return generate_root_certificate()


def new_cert(domain):
    global certificates

    config = get_config()
    options = {
        "COMMON_NAME": config.ca_name,
        "COUNTRY_NAME": config.cert_country,
        "EMAIL_ADDRESS": config.cert_email,
        "DN_QUALIFIER": "."
    }

    private_key, ca_certificate = get_root_certificate()

    certdir = Path(config.certdir).expanduser()
    service_private_key = rsa.generate_private_key(public_exponent=65537,key_size=2048,)
    service_public_key = service_private_key.public_key()
    builder = x509.CertificateBuilder()
    metadata = [x509.NameAttribute(getattr(NameOID, k.upper()), v) for k, v in options.items()] 
    builder = builder.subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
    builder = builder.issuer_name(x509.Name(metadata))
    builder = builder.not_valid_before(datetime.datetime(1997, 5, 26))
    builder = builder.not_valid_after(datetime.datetime.now() + datetime.timedelta(10*365))
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
    config = get_config()
    certdir = Path(config.certdir).expanduser()
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    if not (certdir / f"{hostname}.pem").is_file():
        new_cert(hostname)
    context.load_cert_chain(
        certfile=certdir / f"{hostname}.pem",
        keyfile=certdir / f"{hostname}.key",
    )
    print(certdir/f"{hostname}.pem")
    sock.context = context
