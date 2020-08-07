from binascii import hexlify
from functools import singledispatch, update_wrapper
from typing import Union, List, Optional

from cryptography.hazmat.backends import openssl
from cryptography.hazmat.primitives.asymmetric import ec

from pycose.attributes import CoseHeaderParam, CoseAlgorithm
from pycose.basicstructure import BasicCoseStructure
from pycose.cosekey import SymmetricKey, EC2, OKP
from pycose.crypto import key_wrap, CoseKDFContext, KEY_DERIVATION_CURVES, ecdh_key_derivation


def method_dispatch(func):
    dispatcher = singledispatch(func)

    def wrapper(*args, **kw):
        try:
            return dispatcher.dispatch(args[1].__class__)(*args, **kw)
        except IndexError:
            return dispatcher.dispatch(kw['private_key'].__class__)(*args, **kw)

    wrapper.register = dispatcher.register
    update_wrapper(wrapper, func)
    return wrapper


class CoseRecipient(BasicCoseStructure):

    def __init__(self, phdr: Union[dict, None] = None,
                 uhdr: Union[dict, None] = None,
                 payload: bytes = b'',
                 key: SymmetricKey = None,
                 recipients: Union[List, None] = None):
        super().__init__(phdr=phdr, uhdr=uhdr, payload=payload)

        self.key = key
        self.recipients = [] if recipients is None else recipients

    @property
    def key_bytes(self) -> bytes:
        if self.key is None:
            raise AttributeError('COSE_Key is not set')
        else:
            return self.key.key_bytes

    def encode(self, encrypt: bool = True, alg: Optional[int] = None, key: Optional[SymmetricKey] = None):

        if encrypt:
            recipient = [self.encode_phdr(), self.encode_uhdr(), self.encrypt(alg, key)]
        else:
            recipient = [self.encode_phdr(), self.encode_uhdr(), self.payload]

        if len(self.recipients) > 0:
            res = [recipient, [r.encode() for r in self.recipients]]
        else:
            res = recipient

        return res

    def encrypt(self, alg: Optional[CoseAlgorithm] = None, key: Optional[SymmetricKey] = None) -> bytes:
        """ Do key wrapping. """
        _alg = alg if alg is not None else self.phdr.get(CoseHeaderParam.ALG)
        _alg = _alg if _alg is not None else self.uhdr.get(CoseHeaderParam.ALG)

        if _alg is None:
            raise AttributeError('No algorithm specified.')

        if CoseAlgorithm.ECDH_SS_HKDF_512 <= _alg <= CoseAlgorithm.ECDH_ES_HKDF_256 or _alg == CoseAlgorithm.DIRECT:
            return b''

        try:
            _key = key.key_bytes if key is not None else self.key_bytes
        except AttributeError:
            raise AttributeError("No key specified.")

        return key_wrap(_key, self.payload)

    @method_dispatch
    def derive_kek(self, private_key, public_key: Optional[Union[EC2, OKP]] = None, context: CoseKDFContext = None,
                   salt: bytes = None):
        raise NotImplementedError()

    @derive_kek.register(EC2)
    def _(self, private_key: EC2, public_key: EC2 = None, context: CoseKDFContext = None, salt: bytes = None):
        _ = salt

        try:
            crv = KEY_DERIVATION_CURVES[public_key.CRV]()
        except KeyError:
            raise ValueError(f'Invalid curve: {public_key.CRV}')

        d = ec.derive_private_key(int(hexlify(private_key.private_bytes), 16), crv, openssl.backend)
        p = ec.EllipticCurvePublicNumbers(
            int(hexlify(public_key.X), 16), int(hexlify(public_key.Y), 16), crv).public_key(openssl.backend)

        return ecdh_key_derivation(d, p, int(context.supp_pub_info.key_data_length / 8), context.encode())

    @derive_kek.register(SymmetricKey)
    def _(self, private_key: SymmetricKey, public_key=None, context: CoseKDFContext = None, salt: bytes = None):
        raise NotImplementedError()

    @derive_kek.register(OKP)
    def _(self, private_key: OKP, public_key: OKP = None, context: CoseKDFContext = None,
          salt: bytes = None):
        raise NotImplementedError()

    def __repr__(self) -> str:
        return f'<COSE_Recipient:\n' \
               f'\t phdr={self._phdr}\n' \
               f'\t uhdr={self._uhdr}\n' \
               f'\t payload={self._payload}\n' \
               f'\t recipients={self.recipients}>'