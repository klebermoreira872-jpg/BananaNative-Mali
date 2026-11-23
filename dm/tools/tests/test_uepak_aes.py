"""uepak.py's AES-256 ECB decryption off the Mac: the Python cipher (the Linux packer's) and the system's (CNG on Windows, CommonCrypto on the Mac) on FIPS-197's AES-256
example, and the two against each other on random data; no game files or keys."""
from pathlib import Path
import os
import sys
import unittest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/gfx/tools'))
import uepak

KEY = bytes(range(32))
CIPHER = bytes.fromhex('8ea2b7ca516745bfeafc49904b496089')   # FIPS-197 appendix C.3
PLAIN = bytes.fromhex('00112233445566778899aabbccddeeff')


class Aes(unittest.TestCase):
    def test_python_fips197(self):
        self.assertEqual(uepak.aes_decrypt_py(KEY, CIPHER), PLAIN)
        self.assertEqual(uepak.aes_decrypt_py(KEY, CIPHER * 3), PLAIN * 3)

    def test_system_fips197(self):
        self.assertEqual(uepak.aes_decrypt(KEY, CIPHER * 2), PLAIN * 2)

    def test_python_equals_system(self):
        if sys.platform not in ('win32', 'darwin'): self.skipTest('the Python cipher is the system one here')
        for _ in range(4):
            key, data = os.urandom(32), os.urandom(16 * 37)
            self.assertEqual(uepak.aes_decrypt_py(key, data), uepak.aes_decrypt(key, data))

    def test_bad_lengths(self):
        with self.assertRaises(ValueError): uepak.aes_decrypt_py(KEY, CIPHER[:15])
        with self.assertRaises(ValueError): uepak.aes_decrypt_py(KEY[:16], CIPHER)


if __name__ == '__main__':
    unittest.main()
