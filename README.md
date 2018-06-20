# Piggies

![Piggies Logo (a piggybank)](piggies.svg)

## What is Piggies?

Piggies is a package to automatically manage your cryptocurrency wallets from Python.

It works by launching the wallets using `pexpect`, and communicating with them via JSONRPC.

I'm doing this because one should not hold their cryptocurrencies on an exchange, nor trust a closed-source multiwallet.
However, this is quite difficult, because you have to manage the wallets.

Hence this tool to help you live in the plumbing age of crypto :)

## Security risks

* Make sure not to expose the RPC ports you're using to attackers.
* Do your research before using (and please share findings!)
* Practice [OPSEC](https://en.wikipedia.org/wiki/Operations_security).
* I am not responsible if you lose your money.

## Supported operations

I wanted a consistent way to use various cryptocurrencies. The supported operations are:
* Checking wallet version compatibility
* Starting and stopping the wallet RPC servers
* Retrieving the balance
* Retrieving an address to receive funds
* Retrieving recent incoming transactions
* Suggesting a miner fee
* Performing a transaction with specified amount to send, and specified miner fee

## Supported wallets

### Electrum (BTC)
For Bitcoin, I decided to use Electrum instead of the official Bitcoin client. This is because of two reasons:
* it seems impossible to precisely specify the amount and fee to send, with the official client
* Electrum lets you offload computation to Electrum Servers (albeit at a risk of centralizing the Bitcoin network).

### Monero
Support for the Monero client is in progress, but `perform_transaction` is not yet finished.
Note: In case something goes wrong when executing commands, and the calls hang or timeout, try the following:
- Make sure you have the latest blockchain.
  - Time: since you start the daemon for the first time, it takes two days or so
  - Space: takes around ~55GB right now
- Look at the wallet log, created by Monero next to the binaries.
- Look at the daemon log, usually in the datastore directory at top-level. 
- Wait a little (should not be more than 30 seconds though), especially when performing a transaction or asking for a transaction fee estimate.
- Try loading the same wallet with monero-wallet-cli, and see what happens. New wallets have to refresh from the blockchain, and we don't do that automatically yet.

### Others
I intend to support Ethereum, Litecoin, Bitcoin Cash, ZCash and other distributed currencies.
I consider Ripple and Stellar too centralized, however will review PRs for them or any other currency, if you want to support them yourself.

## Running
Check out `demo.py` for learning how to configure and use Piggies.

## Testing
To perform tests, run `python setup.py test`.

## Feedback

All feedback is welcome.

I especially welcome any ideas/problems about security, or about how to do testing.
If you can think of a way for using [Hypothesis](https://hypothesis.readthedocs.io/en/master/) here, that would be excellent!

To disclose something privately (i.e, security vulnerabilities), send me an e-mail at `danuthaiduc (monkeytail) gmail (period) com`.

Feel free to use GitHub issues, or even open a pull request, for non-security issues!
