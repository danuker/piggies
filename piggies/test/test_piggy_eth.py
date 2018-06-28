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
            {'blocknumber': '5845625', 'parenthash': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c', 'from': 'afd8e94647a9bb953ea634cca475959f29f6c79d', 'to': '✔ ENSRegistrar (0x6090...)', 'value': '0.001 ETH', 'gasused': '93219', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'tx', 'invokescontract': True, 'failed': False, 'direction': 'IN', 'fee': '0.00382 ETH'},
            {'blocknumber': '5845625', 'parenthash': 'tx_in_wrong_direction', 'from': 'afd8e94647a9bb953ea634cca475959f29f6c79d', 'to': '✔ ENSRegistrar (0x6090...)', 'value': '0.001 ETH', 'gasused': '93219', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'tx', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00382 ETH'},
            {'blocknumber': '5845625', 'parenthash': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '8ba4ce173e5960fa4fd5804a729ddd5d4bd215cb', 'value': '0 ETH', 'gasused': '721', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00003 ETH'},
            {'blocknumber': '5845625', 'parenthash': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '8ba4ce173e5960fa4fd5804a729ddd5d4bd215cb', 'value': '0 ETH', 'gasused': '7633', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00031 ETH'},
            {'blocknumber': '5845625', 'parenthash': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '8ba4ce173e5960fa4fd5804a729ddd5d4bd215cb', 'value': '0 ETH', 'gasused': '721', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00003 ETH'},
            {'blocknumber': '5845625', 'parenthash': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '314159265dd8dbb310642f98f50c066173c1259b', 'value': '0 ETH', 'gasused': '432', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00002 ETH'},
            {'blocknumber': '5845625', 'parenthash': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '314159265dd8dbb310642f98f50c066173c1259b', 'value': '0 ETH', 'gasused': '22681', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00093 ETH'},
            {'blocknumber': '5845625', 'parenthash': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '8ba4ce173e5960fa4fd5804a729ddd5d4bd215cb', 'value': '0 ETH', 'gasused': '721', 'gasprice': '41000000000', 'time': 'a minute ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00003 ETH'},
            {'blocknumber': '5845623', 'parenthash': 'b23e0698b3323560c57bdba891a035ee291523ebd33bb712e7c4966067ea8948', 'from': 'd8eee7e8d8f5eb80888588782fdb8b0e0e551495', 'to': '✔ ENSRegistrar (0x6090...)', 'value': '0.03 ETH', 'gasused': '457191', 'gasprice': '4000000000', 'time': '2 minutes ago', 'type': 'tx', 'invokescontract': True, 'failed': False, 'direction': 'IN', 'fee': '0.00183 ETH'},
            {'blocknumber': '5845623', 'parenthash': 'b23e0698b3323560c57bdba891a035ee291523ebd33bb712e7c4966067ea8948', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '314159265dd8dbb310642f98f50c066173c1259b', 'value': '0 ETH', 'gasused': '432', 'gasprice': '4000000000', 'time': '2 minutes ago', 'type': 'call', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '< 0.00001 ETH'},
            {'blocknumber': '5845623', 'parenthash': 'b23e0698b3323560c57bdba891a035ee291523ebd33bb712e7c4966067ea8948', 'from': '✔ ENSRegistrar (0x6090...)', 'to': '1e198956cb24b883ea8e446cfe9ddf9208a9353e', 'value': '0.03 ETH', 'gasused': '339168', 'gasprice': '4000000000', 'time': '2 minutes ago', 'type': 'create', 'invokescontract': True, 'failed': False, 'direction': 'OUT', 'fee': '0.00136 ETH'}
        ]}

        expected = [
            {
                'txid': '9488ba5b58bc5bb9558c916ccf584ae28d689e4e864dda68aa915a06bb9c382c',
                'time': 1529837703,
                'value': Decimal('0.001')
            }
        ]

        self.assertEqual(PiggyETH._process_history(raw_txns, 1529837703, _timestamp_getter), expected)

    def test_parse_utc_time(self):
        """
        Warning: This test passes unconditionally, if you are in GMT. To
            confirm the test works, use a non-GMT time zone.
        """
        timestr = "1970-01-01T00:00:00.000Z"
        timestamp = 0
        self.assertEqual(PiggyETH._parse_utc_time(timestr), timestamp)
