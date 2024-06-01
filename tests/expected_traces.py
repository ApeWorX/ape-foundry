LOCAL_TRACE = r"""
Call trace for '0x([A-Fa-f0-9]{64})'
tx\.origin=0x[a-fA-F0-9]{40}
ContractA\.methodWithoutArguments\(\) -> 0x00\.\.93bc \[\d+ gas\]
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
│         cardinal=ContractA
│       \) \[\d+ gas\]
├── SYMBOL\.callMe\(blue=tx\.origin\) -> tx\.origin \[\d+ gas\]
├── SYMBOL\.methodB2\(trombone=tx\.origin\) \[\d+ gas\]
│   ├── ContractC\.paperwork\(ContractA\) -> \(
│   │     os="simpler",
│   │     country=345457847457457458457457457,
│   │     wings=ContractA
│   │   \) \[\d+ gas\]
│   ├── ContractC\.methodC1\(windows95="simpler", jamaica=0, cardinal=ContractC\) \[\d+ gas\]
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
│   └── ContractC\.methodC1\(windows95="simpler", jamaica=0, cardinal=ContractA\) \[\d+ gas\]
└── SYMBOL\.methodB1\(lolol="snitches_get_stiches", dynamo=111\) \[\d+ gas\]
    ├── ContractC\.getSomeList\(\) -> \[
    │     3425311345134513461345134534531452345,
    │     111344445534535353,
    │     993453434534534534534977788884443333
    │   \] \[\d+ gas\]
    └── ContractC\.methodC1\(windows95="simpler", jamaica=111, cardinal=ContractA\) \[\d+ gas\]
"""
MAINNET_FAIL_TRACE_FIRST_10_LINES = r"""
Call trace for '0x053cba5c12172654d894f66d5670bab6215517a94189a9ffc09bc40a589ec04d'
reverted with message: "UNIV3R: min return"
tx\.origin=0xd2f91C13e2D7ABbA4408Cd3D86285b7835524ad7
AggregationRouterV4\.uniswapV3Swap\(
  amount=12851675475480000000000,
  minReturn=4205588148,
  pools=\[
    682631518358379038160760928734868612545194078373,
    5789604461865809771178549250512551984713807685540901737341300416798777562476
"""
MAINNET_FAIL_TRACE_LAST_10_LINES = r"""
    ├── AggregationRouterV4\.uniswapV3SwapCallback\(
    │     amount0Delta=-4192051335,
    │     amount1Delta=2098831888913057968,
    │     0x00\.\.097d
    │   \) \[9861 gas\]
    │   ├── UniswapV3Pool.token0\(\) -> FiatTokenProxy \[266 gas\]
    │   ├── UniswapV3Pool\.token1\(\) -> WETH \[308 gas\]
    │   ├── UniswapV3Pool\.fee\(\) -> 500 \[251 gas\]
    │   └── WETH\.transfer\(dst=UniswapV3Pool, wad=2098831888913057968\) -> True \[6062 gas\]
    └── WETH\.balanceOf\(UniswapV3Pool\) -> 68359883632315875514968 \[534 gas\]
"""
MAINNET_TRACE_FIRST_10_LINES = r"""
Call trace for '0xb7d7f1d5ce7743e821d3026647df486f517946ef1342a1ae93c96e4a8016eab7'
tx\.origin=0x5668EAd1eDB8E2a4d724C8fb9cB5fFEabEB422dc
DSProxy\.execute\(_target=LoanShifterTaker, _data=0x35\.\.0000\) -> "" \[\d+ gas\]
└── \(delegate\) LoanShifterTaker\.moveLoan\(
      _exchangeData=\[
        0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE,
        ZERO_ADDRESS,
        0,
        0,
"""
MAINNET_TRACE_LAST_10_LINES = r"""
    │                   └── LendingRateOracle\.getMarketBorrowRate\(_asset=DAI\) ->
    │                       35000000000000000000000000 \[1164 gas\]
    ├── DSProxy\.authority\(\) -> DSGuard \[1291 gas\]
    ├── DSGuard\.forbid\(src=LoanShifterReceiver, dst=DSProxy, sig=0x1c\.\.0000\) \[5253 gas\]
    └── DefisaverLogger\.Log\(
          _contract=DSProxy,
          _caller=tx\.origin,
          _logName="LoanShifter",
          _data=0x00\.\.0000
        \) \[6057 gas\]
"""
LOCAL_GAS_REPORT = r"""
 +ContractA Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  methodWithoutArguments +1 +\d+ +\d+ +\d+ + \d+
"""
