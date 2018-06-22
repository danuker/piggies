import unittest
from decimal import Decimal

from piggies import PiggyBTC


class PiggyBTCTesting(unittest.TestCase):
    def test_process_history(self):
        """ Make sure only the transactions we're interested in get returned """

        txn_history = [
            {
                # Valid transaction
                'txid': 1,
                'timestamp': 100,
                'confirmations': 1,
                'value': '3.14 BTC',
            },
            {
                # Txn too old
                'txid': 2,
                'timestamp': 99,
                'confirmations': 1,
                'value': '3.14 BTC',
            },
            {
                # Txn unconfirmed
                'txid': 3,
                'timestamp': 100,
                'confirmations': 0,
                'value': '3.14 BTC',
            },
            {
                # Txn sending money, not receiving
                'txid': 4,
                'timestamp': 100,
                'confirmations': 1,
                'value': '-3.14 BTC',
            },
            {
                # Txn not affecting balance
                'txid': 5,
                'timestamp': 100,
                'confirmations': 1,
                'value': '-0.0 BTC',
            },
            {
                # Txn not affecting balance
                'txid': 6,
                'timestamp': 100,
                'confirmations': 1,
                'value': '0.0 BTC',
            },
        ]

        expected = [{
            'txid': 1,
            'time': 100,
            'value': Decimal('3.14'),
        }]

        processed = PiggyBTC._process_history(txn_history, 100)
        self.assertEqual(expected, processed)
