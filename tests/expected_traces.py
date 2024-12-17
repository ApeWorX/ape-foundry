LOCAL_TRACE = r"""
Call trace for '0x([A-Fa-f0-9]{64})'
tx\.origin=0x[a-fA-F0-9]{40}
ContractA\.methodWithoutArguments\(\) -> 0x0000\.\.93bc \[\d+ gas\]
├── SYMBOL\.supercluster\(x=234444\) -> \[
│       \[23523523235235, 11111111111, 234444\],
│       \[
│         345345347789999991,
│         99999998888882,
│         345457847457457458457457457
│       \],
│       \[234444, 92222229999998888882, 3454\],
│       \[
│         111145345347789999991,
│         333399998888882,
│         234545457847457457458457457457
│       \]
│   \] \[\d+ gas\]
├── SYMBOL\.methodB1\(lolol="ice-cream", dynamo=345457847457457458457457457\) \[\d+ gas\]
│   ├── ContractC\.getSomeList\(\) -> \[
│   │     3425311345134513461345134534531452345,
│   │     111344445534535353,
│   │     993453434534534534534977788884443333
│   │   \] \[\d+ gas\]
│   └── ContractC\.methodC1\(
│         windows95="simpler",
│         jamaica=345457847457457458457457457,
│         cardinal=Contract[A|C]
│       \) \[\d+ gas\]
├── SYMBOL\.callMe\(blue=tx\.origin\) -> tx\.origin \[\d+ gas\]
├── SYMBOL\.methodB2\(trombone=tx\.origin\) \[\d+ gas\]
│   ├── ContractC\.paperwork\(Contract[A|C]\) -> \(
│   │     os="simpler",
│   │     country=345457847457457458457457457,
│   │     wings=Contract[A|C]
│   │   \) \[\d+ gas\]
│   ├── ContractC\.methodC1\(windows95="simpler", jamaica=0, cardinal=Contract[A|C]\) \[\d+ gas\]
│   ├── ContractC\.methodC2\(\) \[\d+ gas\]
│   └── ContractC\.methodC2\(\) \[\d+ gas\]
├── ContractC\.addressToValue\(tx.origin\) -> 0 \[\d+ gas\]
├── SYMBOL\.bandPractice\(tx.origin\) -> 0 \[\d+ gas\]
├── SYMBOL\.methodB1\(lolol="lemondrop", dynamo=0\) \[\d+ gas\]
│   ├── ContractC\.getSomeList\(\) -> \[
│   │     3425311345134513461345134534531452345,
│   │     111344445534535353,
│   │     993453434534534534534977788884443333
│   │   \] \[\d+ gas\]
│   └── ContractC\.methodC1\(windows95="simpler", jamaica=0, cardinal=Contract[A|C]\) \[\d+ gas\]
└── SYMBOL\.methodB1\(lolol="snitches_get_stiches", dynamo=111\) \[\d+ gas\]
    ├── ContractC\.getSomeList\(\) -> \[
    │     3425311345134513461345134534531452345,
    │     111344445534535353,
    │     993453434534534534534977788884443333
    │   \] \[\d+ gas\]
    └── ContractC\.methodC1\(windows95="simpler", jamaica=111, cardinal=Contract[A|C]\) \[\d+ gas\]
"""
MAINNET_FAIL_TRACE_FIRST_10_LINES = r"""
Call trace for '0x605ebd5a54b7d99d9bb61a228a57bfdf8614148c063a5f44e5d52b5a81c2679c'
reverted with message: "BAL#508"
tx\.origin=0xF36BCB79C3AD71Bd4E9343f78c402b0f6C99bF34
AggregationRouterV5\.swap\(
  executor=AggregationRouterV5,
  desc=\[
    AggregationRouterV5,
    AggregationRouterV5,
    AggregationRouterV5,
    tx\.origin,

"""
MAINNET_FAIL_TRACE_LAST_10_LINES = r"""
            48534500000000000000,
            0x0000\.\.0000
          ],
          funds=\['Vault', 0, 'Vault', 0\],
          limit=0,
          deadline=1734390153
        \) ->
        0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000
        000000000000000000000000000000000000000000000742414c2335303800000000000000000000000000000000
        000000000000000000 48534500000000000000 \[7542 gas\]

"""
MAINNET_TRACE_FIRST_10_LINES = r"""
Call trace for '0xb7d7f1d5ce7743e821d3026647df486f517946ef1342a1ae93c96e4a8016eab7'
tx\.origin=0x5668EAd1eDB8E2a4d724C8fb9cB5fFEabEB422dc

Events emitted:
log LogPermit\(src=0x0000\.\.09ad, dst=0x0000..52dd, sig=0x1cff\.\.0000\)
log Transfer\(
  from=CErc20Delegator,
  to=CErc20Delegator,
  amount=48354786024690521017562
\)\[x2\]
"""
MAINNET_TRACE_LAST_10_LINES = r"""
    │                       35000000000000000000000000 \[1164 gas\]
    ├── CErc20Delegator\.0xbf7e214f\(\) ->
    │   0x000000000000000000000000b67f15159e1c60d7e5f5b60316c4588b014c61fa \[1291 gas\]
    ├── DSGuard\.forbid\(src=DSGuard, dst=DSGuard, sig=0x1cff\.\.0000\) \[5253 gas\]
    └── DefisaverLogger\.Log\(
          _contract=DefisaverLogger,
          _caller=tx\.origin,
          _logName="LoanShifter",
          _data=0x0000\.\.0000
        \) \[6057 gas\]

"""
LOCAL_GAS_REPORT = r"""
 +ContractA Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  methodWithoutArguments +1 +\d+ +\d+ +\d+ + \d+
"""
