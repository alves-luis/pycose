from typing import Optional, Union

from pycose.algorithms import AlgorithmIDs
from pycose.cosebase import CoseBase
from pycose.keys.ec import EC2
from pycose.keys.okp import OKP


class CoseSignature(CoseBase):
    context = "Signature"

    @classmethod
    def from_signature_obj(cls, cose_signature_obj: list):
        msg = super().from_cose_obj(cose_signature_obj)
        msg.signature = cose_signature_obj.pop()
        return msg

    def __init__(self,
                 phdr: Optional[dict],
                 uhdr: Optional[dict],
                 signature: Optional[bytes] = b'',
                 external_aad: Optional[bytes] = b'',
                 private_key: Optional[Union[EC2, OKP]] = None,
                 public_key: Optional[Union[EC2, OKP]] = None):
        super().__init__(phdr=phdr, uhdr=uhdr)

        self.external_aad = external_aad
        self.private_key = private_key
        self.public_key = public_key
        self.signature = signature

    def compute_signature(self,
                          to_sign: bytes,
                          alg: Optional[AlgorithmIDs] = None):
        pass


    def encode(self, signature: Optional[bytes]) -> list:

        if signature:
            message = [self.encode_phdr(), self.encode_uhdr(), signature]
        else:
            message = [self.encode_phdr(), self.encode_uhdr()]

        return message

    def __repr__(self) -> str:
        pass


class CounterSignature(CoseSignature):
    context = "CounterSignature"

    @classmethod
    def decode(cls, cose_signature_obj: list):
        return super().from_signature_obj(cose_signature_obj)


class CounterSignature0(CoseSignature):
    context = "CounterSignature0"

    @classmethod
    def decode(cls, cose_signature_obj: list):
        return super().from_signature_obj(cose_signature_obj)