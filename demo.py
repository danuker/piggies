#!/usr/bin/env python3

# Before you can use Piggies, you need actual wallets.
# To fetch and extract the wallet clients, and create wallet files:

# mkdir wallets && cd wallets
#
# wget https://download.electrum.org/3.1.3/Electrum-3.1.3.tar.gz
# tar xvzf Electrum-3.1.3.tar.gz
# cd Electrum-3.1.3/
# mkdir -p ../../datastores/BTC/wallets/
# ./electrum create -w ../../datastores/BTC/wallets/your_BTC_wallet_name_here.dat
# cd ..
#
# wget https://dlsrc.getmonero.org/cli/monero-linux-x64-v0.12.2.0.tar.bz2
# tar xvjf monero-linux-x64-v0.12.2.0.tar.bz2
# cd monero-v0.12.2.0/
# mkdir -p ../../datastores/XMR/wallets/
# ./monero-wallet-cli --generate-new-wallet=../../datastores/XMR/wallets/your_XMR_wallet_name_here.dat
# cd ../..
#
# # The next command will sync the Monero blockchain.
# # It took about 48h (+/- 24h) on an SSD, on 2018-06-06.
# # An HDD (not SSD) would take about 4.7 times longer!!!
# # Also, make sure you are using a wired network connection, not Wi-Fi (which is slower)!
#
# # Required disk space: Multiply the last reported size here by 1.3:
# # https://moneroblocks.info/stats/blockchain-growth
# # Right now, that results in 52932.49 MB (51.69 GB)
# wallets/monero-v0.12.2.0/monerod --data-dir datastores/XMR --rpc-bind-port=37779
# cd ..

# wget https://releases.parity.io/v1.11.4/x86_64-unknown-debian-gnu/parity_1.11.4_debian_amd64.deb
# sudo dpkg -i parity_1.11.4_debian_amd64.deb
# parity account new -d datastores/ETH/
#
# # The Parity wallet also takes a while to sync (around 12h or so, as of 2018-06-28).
# # Using the CLI options in PiggyETH, the blockchain without ancient blocks only takes up ~24GB.
# # Check
# ./demo

import logging
from decimal import Decimal

from piggies import MasterPiggy

logger = logging.getLogger('piggy_logs')

# Requested piggy settings
piggy_settings = {
    'BTC': {
        'wallet_bin_path': 'wallets/Electrum-3.1.3/electrum',
        'datastore_path': 'datastores/BTC',
        'wallet_filename': 'your_BTC_wallet_name_here.dat',
        'wallet_password': 'your_BTC_password_here',
        'rpcuser':'your_BTC_RPC_username',
        'rpcpassword': 'your_BTC_RPC_password',
        'rpcport': 37778
    },

    'XMR': {
        'daemon_bin_path': 'wallets/monero-v0.12.2.0/monerod',
        'wallet_bin_path': 'wallets/monero-v0.12.2.0/monero-wallet-rpc',
        'datastore_path': 'datastores/XMR',
        'wallet_filename': 'your_XMR_wallet_name_here.dat',
        'wallet_password': 'your_XMR_password_here',
        'daemon_port': 37779,  # For the default Monero client, the wallet has a separate server daemon
        'rpcport': 37780
    },

    'ETH': {
        'wallet_bin_path': '/usr/bin/parity',
        'datastore_path': 'datastores/ETH',
        'wallet_password': 'your_ETH_wallet_password_here'
    }
}


def main():
    mp = MasterPiggy(piggy_settings)
    mp.start_servers()

    logger.warning('#######################')
    logger.warning('Calling RPC methods now')
    logger.warning('#######################')

    logger.warning('Balance: {}'.format(mp.get_balances()))
    logger.warning('BTC Receive address: {}'.format(mp.get_receive_address('BTC')))
    logger.warning("BTC transactions_since: \n{}".format(mp.transactions_since('BTC')))
    logger.warning("BTC suggest_miner_fee: \n{}".format(mp.suggest_miner_fee('BTC')))

    logger.warning('XMR Receive address: {}'.format(mp.get_receive_address('XMR')))
    logger.warning("XMR transactions_since: \n{}".format(mp.transactions_since('XMR')))
    logger.warning("XMR suggest_miner_fee: \n{}".format(mp.suggest_miner_fee('XMR')))

    logger.warning('ETH Receive address: {}'.format(mp.get_receive_address('ETH')))
    logger.warning("ETH transactions_since: \n{}".format(mp.transactions_since('ETH')))
    logger.warning("ETH suggest_miner_fee: \n{}".format(mp.suggest_miner_fee('ETH')))

    mp.stop_servers()


if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    main()
