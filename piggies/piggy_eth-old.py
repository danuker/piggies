

# web3.fromWei, web3.toWei
# web3.eth.getBalance

# Using multiple addresses: only if you create multiple transactions to send.
# See: https://ethereum.stackexchange.com/questions/2918/how-to-spend-ether-from-multiple-accounts
# web3.eth.accounts

# Transactions Since:
# https://github.com/ethereum/go-ethereum/issues/1897#issuecomment-169307378 # NOT WORKING



# https://github.com/ethereum/go-ethereum/issues/2104#issuecomment-168748944
"""
var n = eth.blocknumber;

var txs = [];
for(var i = 0; i < n; i++) {
    var block = eth.getBlock(i, true);
    for(var j = 0; j < block.transactions; j++) {
        if( block.transactions[j].to == the_address )
            txs.push(block.transactions[j]);
    }
}
"""
import os
import socket
import subprocess
import time
from decimal import Decimal

import jsonrpclib
import pandas as pd

from lib.monkeypatching import monkeypatch
from lib.processing import universal_apply
from lib.utils import config_load, wait_for_success, get_block_by_timestamp, to_hex, from_hex

monkeypatch()


class PiggyETH:
    wei_per_eth = Decimal('1e18')

    def __init__(self, config_file):
        """Manage an Ethereum wallet

        We use the `geth` wallet.
        """

        self.config = config_load(config_file)['piggies']['ETH']
        # self.bin_path = os.path.join(self.config['wallet_path'], 'geth')
        self.bin_path = os.path.join(self.config['wallet_path'], 'parity')

        # Memoization
        self.server = None
        self.process = None
        self.accounts = None

    def start_server(self):
        if self._rpc_loaded():
            return

        # Command for Geth
        # command = [
        #     self.bin_path,
        #     '--cache', '1024',
        #     '--nousb',
        #     '--syncmode', 'fast',
        #     '--datadir', self.config['datastore_path'],
        #     '--rpc',
        #     '--rpcport', str(self.config['rpcport'])
        # ]

        # Command for Parity
        command = [
            self.bin_path,
            '-d', self.config['datastore_path'],
            '--jsonrpc-port', str(self.config['rpcport']),

            # https://github.com/paritytech/parity/issues/6372#issuecomment-354504127
            '--cache-size', '1024',
            '--snapshot-peers=25',
            '--ntp-servers=pool.ntp.org:123',
            '--db-compaction', 'ssd',
            '--max-peers=150',
            '--min-peers=100',
        ]

        # '-d <some-dir> --jsonrpc-port <some-port> --cache-size 1024 --snapshot-peers=25 --ntp-servers=pool.ntp.org:123 --db-compaction ssd --max-peers=150 --min-peers=100',

        logger.info('Starting ETH Wallet: {}'.format(' '.join(command)))

        outfile = os.path.join(self.config['wallet_path'], 'eth_logfile.out')
        errfile = os.path.join(self.config['wallet_path'], 'eth_logfile.err')

        self.process = subprocess.Popen(
            command,

            # Make process group leader
            # (process survives after parent dies)
            preexec_fn=os.setpgrp,

            # Redirect outputs so that process buffers don't fill
            stdout=open(outfile, 'a'),
            stderr=open(errfile, 'a'),
        )

        wait_for_success(self._rpc_loaded, 'ETH RPC')

    def stop_server(self):
        p = subprocess.Popen(
            ['/usr/bin/pkill', '-f', self.bin_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate()

        if err:
            raise ValueError('Error pkilling ETH:\n{}'.format(err))

    def get_receive_address(self):
        self._connect_if_needed()
        accounts = self._get_accounts()

        # We can only handle 1 account/address;
        # In order to support multiple accounts you need to also alter:
        # `get_balance`, `transactions_since`, `perform_transaction`
        assert len(accounts) == 1

        return accounts[0]

    def get_balance(self):
        self._connect_if_needed()
        hexwei = self.server.eth_getBalance(self.get_receive_address(), 'latest')
        return self._decode_hexwei(hexwei)

    def suggest_miner_fee(self):
        """Return the total amount of gas needed for a transaction"""

        # delay = self._sync_delay()
        # if delay > 120:
        #     raise ValueError(
        #         'Can not suggest miner fee yet; still syncing! We are {:0.2f} hours behind.'
        #         .format(delay / 3600.)
        #     )

        # Get the gas used by a transaction
        hex_gas_needed = self.server.eth_estimateGas(
            {
                'from': '0x969e875686e0d4fa32927ca25a3f6402814276de',
                'to': '0x969e875686e0d4fa32927ca25a3f6402814276de',
                'gas': '0x1000000000',
                'value': '0x1'
            }
        )
        gas_needed = Decimal(from_hex(hex_gas_needed))

        # Get the gas price in the latest unconfirmed block
        hex_wei_gasprice = self.server.eth_gasPrice()
        eth_gas_price = self._decode_hexwei(hex_wei_gasprice)

        return eth_gas_price * gas_needed

    def transactions_since(self, since_unix_time, check_range_size=True):
        """Find incoming transactions since specified time"""

        self._connect_if_needed()

        def fetch_timestamp(block_index):
            print('checking', block_index)
            block = self.server.eth_getBlockByNumber('0x'+to_hex(block_index), False)
            return from_hex(block['timestamp'])

        at_block = from_hex(self.server.eth_blockNumber())
        print('at block:', at_block)
        start_looking = get_block_by_timestamp(since_unix_time, fetch_timestamp, at_block)

        if check_range_size:
            self._check_range_size(at_block, start_looking)

        txns = self._parse_blocks_incoming_txns(at_block, start_looking)

        txns = txns[['hash', 'time', 'value']]
        txns.columns = ['txid', 'time', 'value']
        txns['time'] = universal_apply(from_hex, txns['time'])
        txns['value'] = universal_apply(self._decode_hexwei, txns['value'])

        return txns

    @staticmethod
    def _check_range_size(at_block, start_looking):
        if (at_block - start_looking) > 8562:
            # Benchmark: 0.0700710841588s per block (for 84 blocks)
            # This means ~213x real time (assuming 15s/block mining)
            # Biggest outage tolerated: ~35.6 hours
            raise ValueError('Transaction too old! '
                             'Checking blocks would take longer than 10 minutes.')

    def _parse_blocks_incoming_txns(self, at_block, start_looking):
        """
        Look at each block of the blockchain from `start_looking` to `at_block`,
        and return all transactions sending ether to self._get_accounts.
        """

        incoming_txns = []

        for blocknum in range(start_looking, at_block + 1):
            print('Checking txns in {}'.format(blocknum))
            relevant_txns = self._get_incoming_txns(blocknum)

            incoming_txns += relevant_txns

        if incoming_txns:
            return pd.DataFrame(incoming_txns)
        else:
            return pd.DataFrame(columns=['hash', 'time', 'value'])

    def _get_incoming_txns(self, blocknum):
        """Return all transactions in a given block that send ether to self._get_account"""

        block = self.server.eth_getBlockByNumber('0x' + to_hex(blocknum), True)

        relevant_txns = []
        for txn in block['transactions']:
            if txn['to'] is not None:
                # Sometimes transactions do not have a recipient (i.e. contract creation)
                if txn['to'].lower() in self._get_accounts():
                    txn['time'] = block['timestamp']
                    relevant_txns.append(txn)
            else:
                if txn['value'] != '0x0':
                    print(('Value transfer to unrecognized recipient! {}'.format(txn)))

        if relevant_txns:
            print('found incoming:', relevant_txns)
        return relevant_txns

    def _rpc_loaded(self):
        """Attempt a connection to the RPC"""
        self._connect_if_needed()
        try:
            self.server.eth_syncing()
            return True
        except socket.error:
            return False

    def _connect_if_needed(self):
        if self.server is None:
            self.server = jsonrpclib.Server(
                "http://127.0.0.1:{}".format(self.config['rpcport'])
            )

    @classmethod
    def _decode_hexwei(cls, hexwei):
        """Transform (`wei` in base 16) to a Decimal of the Ether equivalent"""

        if not isinstance(hexwei, str):
            raise ValueError(
                'Require hexwei as string; got {} ({}) instead.'.format(hexwei, type(hexwei))
            )
        return from_hex(hexwei) / cls.wei_per_eth

    @classmethod
    def _encode_hexwei(cls, decimal_eth):
        """Convert ETH (decimal) to wei (hexadecimal integer)"""

        if not isinstance(decimal_eth, Decimal):
            raise ValueError(
                'Require decima_eth as Decimal; got {} ({}) instead.'.format(
                    decimal_eth, type(decimal_eth)
                )
            )

        if decimal_eth < 0:
            raise ValueError('Do not support negative numbers for hex encoding')

        decimal_wei = decimal_eth * cls.wei_per_eth

        # Make sure it's an integer value
        assert int(decimal_wei) == decimal_wei

        return '0x' + to_hex(decimal_wei)

    def _get_accounts(self):
        if self.accounts is None:
            self.accounts = [addr.lower() for addr in self.server.eth_accounts()]

        return self.accounts

    def _sync_delay(self):
        last_block = self.server.eth_getBlockByNumber('latest', False)
        current_time = time.time()

        return current_time - from_hex(last_block['timestamp'])

# TODO: https://ethereum.stackexchange.com/questions/33205/how-to-send-a-transaction-to-myetherapi-com-with-web3-py

def main():
    p = PiggyETH('config.yml')

    # p.stop_server()
    # return

    p.start_server()
    print("addr: ", p.get_receive_address())
    print("balance: ", p.get_balance())
    print("fee: ", p.suggest_miner_fee())
    # TODO: Check out fast and light mode for Ethereum wallets
    if True:
        # we are checking:
        #  txid 0x75f4bdf6d1277b8ab546ad33da4d97f1f6d19ba4f64639227897b900c45725ec
        #  destination: 		0x6d91b3B949B53D30c956d19E7Ed06466732Fc4C0
        # from:	        	0x0fD081e3Bb178dc45c0cb23202069ddA57064258
        timestamp = 1513754931
        p.accounts = ['0x6d91b3b949b53d30c956d19e7ed06466732fc4c0']
        print('Block at {}: {}'.format(timestamp, p.transactions_since(timestamp, True)))
        p.accounts = None


if __name__ == '__main__':
    main()
