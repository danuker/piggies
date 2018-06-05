#!/usr/bin/env python

# Before you can use Piggies, you need actual wallets.
# To fetch and extract the wallet clients, and create wallet files:

# mkdir wallets && cd wallets
# wget https://download.electrum.org/3.1.3/Electrum-3.1.3.tar.gz
# tar xvzf Electrum-3.1.3.tar.gz
# cd Electrum-3.1.3/
# mkdir -p ../../datastores/BTC/wallets/
# ./electrum create -w ../../datastores/BTC/wallets/your_BTC_wallet_name_here.dat
#
# wget https://dlsrc.getmonero.org/cli/monero-linux-x64-v0.12.0.0.tar.bz2
# tar xvjf monero-linux-x64-v0.12.0.0.tar.bz2

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

#    'XMR': {
#        'wallet_bin_path': 'wallets/monero-v0.12.0.0',
#        'wallet_password': 'your_XMR_password_here',
#        'datastore_path': 'datastores/XMR',
#        'daemon_port': 37779,  # For the default Monero client, the wallet has a separate server daemon
#        'rpcport': 37780
#    }
}


def main():
    mp = MasterPiggy(piggy_settings)
    mp.start_servers()

    logger.warning('#######################')
    logger.warning('Calling RPC methods now')
    logger.warning('#######################')

    logger.warning('Balance: {}'.format(mp.get_balances()))
    logger.warning('BTC receive address: {}'.format(mp.get_receive_address('BTC')))
    logger.warning("transactions_since: \n{}".format(mp.transactions_since('BTC')))

    mp.stop_servers()


if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    main()
