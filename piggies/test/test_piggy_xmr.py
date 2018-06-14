import unittest
from decimal import Decimal

from piggies import PiggyXMR


class PiggyXMRTesting(unittest.TestCase):
    def test_process_history(self):
        """ Make sure only the XMR transactions we're interested in get returned """

        txn_history = {
            'in': [
                {
                    # Valid transaction
                    'txid': '1',
                    'amount': 3140000000000,
                    'timestamp': 100,
                    'type': 'in'
                },
                {
                    # Txn too old
                    'txid': '2',
                    'timestamp': 99,
                    'amount': 3140000000000,
                    'type': 'in'
                },
                {
                    # Txn unconfirmed
                    'txid': '3',
                    'timestamp': 100,
                    'amount': 3140000000000,
                    'type': 'pending'
                },
                {
                    # Txn going out (should ignore)
                    'txid': '4',
                    'timestamp': 100,
                    'amount': 3140000000000,
                    'type': 'out'
                },
                {
                    # Txn going out not affecting balance
                    'txid': '5',
                    'timestamp': 100,
                    'amount': 0,
                    'type': 'out'
                },
                {
                    # Txn coming in not affecting balance
                    'txid': '6',
                    'timestamp': 100,
                    'amount': 0,
                    'type': 'in'
                }
            ],
            'out': [
                    {
                    # Proper txn going out
                    'txid': '5',
                    'timestamp': 100,
                    'amount': 3140000000000,
                    'type': 'out'
                },
            ]
        }

        expected = [{
            'txid': '1',
            'time': 100,
            'value': Decimal('3.14'),
        }]

        processed = PiggyXMR._process_history(txn_history, 100)
        self.assertEquals(expected, processed)

    def test_empty_history(self):
        """No incoming txns -> Monero returns empty JSON"""
        processed = PiggyXMR._process_history({}, 100)

        self.assertEquals([], processed)

