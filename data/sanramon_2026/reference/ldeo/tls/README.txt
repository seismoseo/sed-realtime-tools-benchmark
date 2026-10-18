TLS helper files for https://nocaldd.ldeo.columbia.edu (2026-10-17)

The server sends only its leaf certificate (CN=*.ldeo.columbia.edu, issuer "InCommon Intermediate
CA - OVG2C") and omits the intermediate, so curl/python fail with "unable to get local issuer
certificate". Browsers fetch the missing intermediate from the URL in the certificate's Authority
Information Access field. We did the same (logged in logs/sanramon_requests.tsv):
  EEEMIncommonOVG2C.crt  <- http://repository.emsign.com/certs/EEEMIncommonOVG2C.crt (AIA of the leaf)
  EMIncommonOVG2C.p7c    <- http://repository.emsign.com/certs/EMIncommonOVG2C.p7c (AIA of the intermediate;
                            contains "emSign Root TLS CA - G1" cross-signed by the Mozilla-trusted
                            "emSign Root CA - G1")
ca_bundle_certifi_plus_incommon_ovg2c.pem = certifi bundle + these two, so the chain ends at a
trusted root; certificate verification stays ON (openssl verify of the leaf: OK).
