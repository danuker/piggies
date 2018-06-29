import unittest
from decimal import Decimal

from piggies import PiggyETH


class PiggyETHTesting(unittest.TestCase):
    def test_process_history(self):
        def _timestamp_getter(blocknumber):
            if blocknumber == 5845623:
                return 1529837662
            elif blocknumber == 5845625:
                return 1529837703
            else:
                raise ValueError('Tests should not query for block number {}'.format(repr(blocknumber)))

        raw_txns = {'recordsTotal': 10000, 'recordsFiltered': 10000, 'data': [
            {'blocknumber': '5845625', 'parenthash': 'tx_incoming_valid', 'from': 'afd8e94647a9bb953ea634cca475959f29f6c79d', 'to': '✔ ENSRegistrar (0x6090...)', 'value': '0.001 ETH', 'gasused': '93219', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'tx', 'invokescontract': True, 'failed': False, 'direction': 'IN', 'fee': '0.00382 ETH'},
            {'blocknumber': '5845625', 'parenthash': 'tx_in_wrong_direction', 'from': 'afd8e94647a9bb953ea634cca475959f29f6c79d', 'to': '✔ ENSRegistrar (0x6090...)', 'value': '0.001 ETH', 'gasused': '93219', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'tx', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00382 ETH'},
            {'blocknumber': '5845623', 'parenthash': 'tx_too_early', 'from': 'd8eee7e8d8f5eb80888588782fdb8b0e0e551495', 'to': '✔ ENSRegistrar (0x6090...)', 'value': '0.03 ETH', 'gasused': '457191', 'gasprice': '4000000000', 'time': '2 minutes ago', 'type': 'tx', 'invokescontract': True, 'failed': False, 'direction': 'IN', 'fee': '0.00183 ETH'},
            {'blocknumber': '5845623', 'parenthash': 'tx_too_early_AND_in_wrong_direction', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '314159265dd8dbb310642f98f50c066173c1259b', 'value': '0 ETH', 'gasused': '432', 'gasprice': '4000000000', 'time': '2 minutes ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '< 0.00001 ETH'},
        ]}

        expected = [
            {
                'txid': 'tx_incoming_valid',
                'time': 1529837703,
                'value': Decimal('0.001')
            }
        ]

        self.assertEqual(
            expected,
            PiggyETH._process_history(raw_txns, 1529837703, _timestamp_getter)
        )

    def test_parse_utc_time(self):
        """
        Warning: This test passes unconditionally, if you are in GMT. To
            confirm the test works, use a non-GMT time zone.
        """
        timestr = "1970-01-01T00:00:00.000Z"
        timestamp = 0
        self.assertEqual(PiggyETH._parse_utc_time(timestr), timestamp)

    def test_get_gas_price(self):
        class MockServer:
            @classmethod
            def toWei(cls, eth, unit):
                self.assertEqual(unit, 'ether')
                return eth * Decimal('1e18')

        class MockPiggyETH:
            TXN_GAS_LIMIT=PiggyETH.TXN_GAS_LIMIT
            server = MockServer

        gas_needed = PiggyETH.TXN_GAS_LIMIT
        wei_gas_price = Decimal(12345)
        wei_txn_gas = wei_gas_price * gas_needed
        eth_txn_gas = wei_txn_gas / Decimal('1e18')

        result = PiggyETH._get_gas_price(MockPiggyETH, eth_txn_gas)

        self.assertEqual(result, wei_gas_price)
        self.assertEqual(result.__class__, int)
