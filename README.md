# Piggies

![Piggies Logo (a piggybank)](https://raw.githubusercontent.com/danuker/piggies/master/piggies.svg?sanitize=true)

## What is Piggies?

Piggies is a package to automatically manage your cryptocurrency [hot wallets](https://en.bitcoin.it/wiki/Hot_wallet) using Python.

It works by launching the wallets using `pexpect`, and communicating with them via RPC.

The requirement to be automatic:
* eliminates hardware wallets (you would need to check the addresses and push the button)
* makes it more dangerous, because there might be security vulnerabilities in the software

I'm doing this because some people (including myself) still want automatic wallets (i.e. for their exchange websites accepting coins and withdrawals); however:
* one [should not hold their cryptocurrencies on an exchange](https://www.youtube.com/watch?v=5mcYQpHDgXc)
* one should not trust [any closed-source multiwallet](https://vxlabs.com/2017/06/10/extracting-the-jaxx-12-word-wallet-backup-phrase/)
* one should not even trust [an open source web wallet](https://www.coindesk.com/150k-stolen-myetherwallet-users-dns-server-hijacking/).

Hence this tool to help you live in the plumbing age of crypto :)

## Security risks

* Make sure not to [expose the RPC ports you're using to attackers](https://github.com/spesmilo/electrum/issues/3374#issuecomment-355726294).
* Do your own security research (and please share findings!)
* Practice [OPSEC](https://en.wikipedia.org/wiki/Operations_security).
* I am not responsible if you lose your money.

## Installing

Piggies is available on PyPI. You can install it via:

`pip3 install piggies`

or via:

`python3 -m pip install piggies`

## Running

This is a basic demo for Ethereum: it starts `/usr/bin/parity` on the configured `datastore_path`.

```python
#!/usr/bin/env python3

import logging

from piggies import PiggyETH

logger = logging.getLogger('piggy_logs')

def main():
    piggy = PiggyETH(
        wallet_bin_path='/usr/bin/parity',
        datastore_path='datastores/ETH',
        wallet_password='your_ETH_wallet_password_here'
    )

    piggy.start_server()

    print("Balance:", piggy.get_balance())
    print("Suggested miner fee:", piggy.suggest_miner_fee())

    piggy.stop_server()


if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    main()

```

For a more advanced demo, including `MasterPiggy`, check out [`demo.py`](https://github.com/danuker/piggies/blob/master/demo.py).

## Supported operations

I wanted a consistent way to use various cryptocurrencies. The supported operations are:
* Starting and stopping the wallet RPC servers
* Retrieving the balance
* Retrieving an address to receive funds
* Retrieving recent incoming transactions
* Suggesting a miner fee
* Performing a transaction with specified amount to send, and specified miner fee

The operations are available for both `MasterPiggy` and for the wallets individually (`PiggyBTC`, `PiggyETH`...)

## Supported wallets

### Electrum (BTC)
For Bitcoin, I decided to use [Electrum](https://electrum.org/#download) instead of the official Bitcoin client. This is because of two reasons:
* it seems impossible to precisely specify the amount and fee to send, with the official client
* Electrum lets you offload computation to Electrum Servers (albeit at a risk of centralizing the Bitcoin network).

### Monero (XMR)
Monero is supported via its [official client](https://getmonero.org/downloads/) (requires you to sync the blockchain).
Note: In case something goes wrong when executing commands, and the calls hang or timeout, check the following:
- Make sure you have the latest blockchain.
  - Time: since you start the daemon for the first time, it takes two days or so
  - Space: takes around ~55GB right now
- Look at the wallet log, created by Monero next to the binaries.
- Look at the daemon log, usually in the datastore directory at top-level.
- Wait a little (should not be more than 30 seconds though), especially when performing a transaction or asking for a transaction fee estimate.
- Try loading the same wallet with monero-wallet-cli, and see what happens. New wallets have to refresh from the blockchain, and we don't do that automatically yet.

### Parity (ETH)
I support Ethereum via [Parity](https://www.parity.io/), due to its flexibility with blockchain options.

Once [gas estimation works in the light client](https://github.com/paritytech/parity/issues/8976), we will use it. But right now the light client is experimental, and that specific query didn't seem to work for me on the main Ethereum network.

We also send the log to the datastore directory for ETH.

We don't check wallet version compatibility here, because this is handled by Web3.py [so well that you can even use different clients](http://web3py.readthedocs.io/en/stable/node.html).

The connection to Parity is via IPC, not HTTP, so we use whatever node is running on the `datastore_path`, and there is no need for further settings (ports and such). It is also somewhat more secure.

For `transactions_since`, we use [an external service](https://www.etherchain.org/) due to it being impractical to do. This has some caveats (see the docs for ETH [`transactions_since`](https://github.com/danuker/piggies/blob/master/piggies/piggy_eth.py#L129)). In the future, we might integrate [QuickBlocks](https://quickblocks.io/) to avoid these caveats.

### Others
I might support Litecoin, Bitcoin Cash, ZCash and other distributed currencies, but I don't know for sure.
I consider Ripple and Stellar too centralized, however will review PRs for them or any other currency, if you want to support them yourself.

## Testing
To perform tests, run `./setup.py test`.

## Feedback

All feedback is welcome.

I especially welcome any ideas/problems about security, or about how to do testing.
If you can think of a way for using [Hypothesis](https://hypothesis.readthedocs.io/en/master/) here, that would be excellent!

To disclose something privately (i.e, security vulnerabilities), send me an e-mail at `danuthaiduc (monkeytail) gmail (period) com`.

Feel free to use GitHub issues, or even open a pull request, for non-security issues!
