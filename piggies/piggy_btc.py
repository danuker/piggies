import json
import logging
import os
import subprocess
import urllib2
from decimal import Decimal
from time import sleep

import jsonrpclib
import pandas as pd

from lib.processing import inexact_to_decimal
from lib.utils import config_load, assert_type

logger = logging.getLogger('sys_trader_logger')

class PiggyBTC:
    def __init__(self, config_file):
        """Manage a Bitcoin wallet

        Latest supported wallet version:
        https://download.electrum.org/2.9.3/Electrum-2.9.3.tar.gz
        Extract it to wallets/.

        To run this file:
        > cd SystematicTrader/  # root directory
        > PYTHONPATH=. python piggies/piggy_btc.py
        """
        self.global_config = config_load(config_file)
        self.my_config = self.global_config['piggies']['BTC']

        self.bin_path = os.path.join(self.my_config['wallet_path'], 'electrum')
        self.datadir = os.path.abspath(self.my_config['datastore_path'])

        # Wallet encryption password (hardcoded :p )
        self.wallet_password = self.my_config['wallet_password']
        self.rpcport = self.my_config['rpcport']
        if self.rpcport > 65535:
            raise ValueError('Port too large: {}'.format(self.rpcport))
        self.server = None

    def _execute_electrum_command(self, command, stdin=None, quiet=False):
        """Run the Electrum binary, with given command arguments and/or stdin input

        :param command: List of string CLI arguments
        :param stdin: String or None; if string: pass in string as stdin to Electrum
        """

        done_str = 'Check stdout/stderr here.' if stdin else ''

        if quiet is False:
            logger.info('Executing "{}". {}'.format(command, done_str))

        p = subprocess.Popen(
            [
                self.bin_path,
            ] + command + [
                '--dir',
                self.datadir,  # Where to keep data & config

                '--wallet',
                os.path.join(self.datadir, 'wallets', 'sys_trader_keys.json')
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if stdin is not None:
            # Note: `communicate` waits for process to end
            comms = p.communicate(stdin)

            if quiet is False:
                logger.warning(
                    'Process returned {}.\n'\
                    '### STDOUT:\n{}\n### STDERR:\n{}\n'.format(p.returncode, comms[0], comms[1])
                )
        else:
            comms = []

        return p, comms

    def _connect_if_needed(self):
        if self.server is None:
            self.server = jsonrpclib.Server("http://127.0.0.1:{}".format(self.rpcport))

    def _check_payto_help(self):
        """Check that the help for `payto` has not changed since what we know"""

        _, comms = self._execute_electrum_command(['help', 'payto'], '', quiet=True)
        if comms[0] != open('piggies/help_rpc_btc_payto.txt').read():
            raise ValueError('Error! Help of payto changed on Electrum wallet update.')

    def start_server(self):
        """Start the RPC server

        Use the wallet and datastore paths specified in config.
        """

        self._execute_electrum_command(['setconfig', 'rpcport', str(self.rpcport)])
        self._execute_electrum_command(['daemon', 'start'])

        # Send password via STDIN (ARRRRGHHH)
        sleep(1)
        self._execute_electrum_command(['daemon', 'load_wallet'], '{}\n'.format(self.wallet_password))

        # Wait 1 more second to hopefully finish loading the wallet
        sleep(1)

        self._check_payto_help()

    def stop_server(self):
        self._connect_if_needed()
        self._execute_electrum_command(['daemon', 'stop'])

    def get_balance(self):
        """Return the amount we have in the wallet, confirmed by the blockchain"""
        self._connect_if_needed()

        return Decimal(str(self.server.getbalance()['confirmed']))

    def get_receive_address(self):
        """Returns an unused address where we can receive BTC

        Note: `force` can not be used on an imported keystore.
        You need to have a separate, seed-generated wallet.
        """
        self._connect_if_needed()

        address = self.server.getunusedaddress(force=True)
        if address is False:
            raise ValueError('Error: can not get unused address!')

        return address

    @staticmethod
    def suggest_miner_fee():
        """Returns miner fee to use, for typical transaction

        We should use fee estimates from Electrum, but it has no API for this.
        """
        request = urllib2.Request(
            'https://bitcoinfees.21.co/api/v1/fees/recommended',
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11'
            }
        )
        response = urllib2.urlopen(request)
        data = json.loads(response.read())

        #   The above is in Satoshis/B
        #   Multiply by 226 (typical bytes in a txn) -> Satoshis/txn
        #   Multiply by 0.00000001 (BTCs in a Sat) -> BTC/txn

        ten_min_fee_satoshi_per_byte = data['halfHourFee']
        ten_min_fee_satoshi_per_txn = ten_min_fee_satoshi_per_byte * 226
        fee = Decimal(ten_min_fee_satoshi_per_txn) * Decimal('1e-8')

        if fee > Decimal('0.001'):
            raise ValueError('Fee greater than 1 mBTC!')
        else:
            logger.warning('BTC Miner fee estimate: {}'.format(fee))

        return fee

    def transactions_since(self, since_unix_time):
        """Gets incoming transactions since specified time

        Lists all transactions of positive amount (which increased our balance)
        having the `blocktime` >= the given unix time.

        :param since_unix_time: integer or float, unix time
        :return transactions: DataFrame of transactions
            Each row in the DataFrame has amount, txid, and time of each transaction
        """
        self._connect_if_needed()

        history = pd.DataFrame(self.server.history())

        # Required as long as Electrum returns us floats via JSON
        history['value'] = inexact_to_decimal(history['value'])

        recently_received = history.loc[
            (history['timestamp'] > float(since_unix_time)) &
            (history['confirmations'] >= 1) &
            (history['value'] > 0)  # We received money (not sent, and not zero)
        ]

        # Only get the required fields
        recently_received = recently_received[['txid', 'timestamp', 'value']]

        # Name consistent with Executioner
        recently_received.columns = ['txid', 'time', 'value']

        return recently_received

    def perform_transaction(self, net_amount, miner_fee, target_address):
        """Send Bitcoins to target_address (total cost: net_amount + miner_fee)"""

        self._connect_if_needed()

        assert_type(net_amount, Decimal)
        assert_type(miner_fee, Decimal)
        self._validate_address(target_address)

        tx = self.server.payto(
            destination=str(target_address),
            amount=str(net_amount),
            tx_fee=str(miner_fee),
            password=self.wallet_password
        )

        success, txid = self.server.broadcast(tx['hex'])

        # Signed TX: {u'hex': u'0100000001718276ce6c2298bf71352fa38fb9b4d3d40f49ec592d0dae640d9f4709e11a6a000000006b483045022100a1cbbd78b0f6f3c01bac6ea0590adbe2941b2be3d08820e1adb5b42777c4bd6202201c176a5f0a25c20f856aa91c09a7581d4d1057fa4e644c65ee34d9fd113291d6012103c64230ff95961bda955ae374e90cf4d9883432731a2df0389204162b7e6dc579feffffff0107003700000000001976a91490c235fba4b7ea93106c7439703779cba6db772e88ac00000000', u'complete': True, u'final': True}
        # Broadcast TX: [True, u'f0619d982344c12169e5fbf38f83b474be7df5a009351a6b1aeb4430566fa7ba']

        if success:
            logger.warning("Signed TX: {}".format(tx))
            logger.warning("Broadcast TX id: {}".format(txid))
            return txid
        else:
            raise BaseException("Transaction broadcast fail: {}".format(txid))

    def _validate_address(self, btc_address):
        """Raises an exception if address is invalid"""
        self.server.getaddressbalance(btc_address)


def main():
    p = PiggyBTC('config.yml')
    p.start_server()

    logger.warning('#######################')
    logger.warning('Calling RPC methods now')
    logger.warning('#######################')
    logger.warning('Balance: {}'.format(p.get_balance()))
    logger.warning('Some new address: {}'.format(p.get_receive_address()))
    logger.warning("transactions_since: \n{}".format(p.transactions_since(1508496657)))

    p.stop_server()


if __name__ == '__main__':
    main()
