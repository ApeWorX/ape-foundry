LOCAL_TRACE = r"""
Call trace for
'0x([A-Fa-f0-9]{64})'
tx\.origin=0x[a-fA-F0-9]{40}
ContractA\.methodWithoutArguments\(\) -> 0x00..5174 \[\d+ gas\]
├── SYMBOL\.methodB1\(lolol="ice-cream", dynamo=36\) \[\d+ gas\]
│   ├── ContractC\.getSomeList\(\) -> \[
│   │     3425311345134513461345134534531452345,
│   │     111344445534535353,
│   │     993453434534534534534977788884443333
│   │   \] \[\d+ gas\]
│   └── ContractC\.methodC1\(windows95="simpler", jamaica=36, cardinal=ContractA\)
│       \[\d+ gas\]
├── SYMBOL\.callMe\(blue=tx.origin\) -> tx\.origin \[\d+ gas\]
├── SYMBOL\.methodB2\(trombone=tx.origin\) \[\d+ gas\]
│   ├── ContractC\.paperwork\(ContractA\) -> \(os="simpler", country=36,
│   │   wings=ContractA\) \[\d+ gas\]
│   ├── ContractC\.methodC1\(windows95="simpler", jamaica=0, cardinal=ContractC\)
│   │   \[\d+ gas\]
│   ├── ContractC\.methodC2\(\) \[\d+ gas\]
│   └── ContractC\.methodC2\(\) \[\d+ gas\]
├── ContractC\.addressToValue\(tx\.origin\) -> 0 \[\d+ gas\]
├── SYMBOL\.bandPractice\(tx\.origin\) -> 0 \[\d+ gas\]
├── SYMBOL\.methodB1\(lolol="lemondrop", dynamo=0\) \[\d+ gas\]
│   ├── ContractC\.getSomeList\(\) -> \[
│   │     3425311345134513461345134534531452345,
│   │     111344445534535353,
│   │     993453434534534534534977788884443333
│   │   \] \[\d+ gas\]
│   └── ContractC.methodC1\(windows95="simpler", jamaica=0, cardinal=ContractA\)
│       \[\d+ gas\]
└── SYMBOL\.methodB1\(lolol="snitches_get_stiches", dynamo=111\) \[\d+ gas\]
    ├── ContractC\.getSomeList\(\) -> \[
    │     3425311345134513461345134534531452345,
    │     111344445534535353,
    │     993453434534534534534977788884443333
    │   \] \[\d+ gas\]
    └── ContractC\.methodC1\(windows95="simpler", jamaica=111, cardinal=ContractA\)
        \[\d+ gas\]
"""
MAINNET_FAIL_TRACE_FIRST_10_LINES = r"""
Call trace for
'0x053cba5c12172654d894f66d5670bab6215517a94189a9ffc09bc40a589ec04d'
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
    │   ├── 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640\.0xd21220a7\(\) ->
    │   │   0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    │   ├── 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640\.0xddca3f43\(\) ->
    │   │   0x00000000000000000000000000000000000000000000000000000000000001f4
    │   └── WETH.transfer\(
    │         dst=0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640,
    │         wad=2098831888913057968
    │       \) -> True
    └── WETH\.balanceOf\(0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640\) ->
        68359883632315875514968
"""
MAINNET_TRACE_FIRST_10_LINES = r"""
Call trace for
'0xb7d7f1d5ce7743e821d3026647df486f517946ef1342a1ae93c96e4a8016eab7'
tx\.origin=0x5668EAd1eDB8E2a4d724C8fb9cB5fFEabEB422dc
DSProxy\.execute\(_target=LoanShifterTaker, _data=0x35\.\.0000\) -> '' \[1249147 gas\]
└── \(delegate\) LoanShifterTaker\.moveLoan\(
      _exchangeData=\[
        0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE,
        ZERO_ADDRESS,
        0,
        0,
"""
MAINNET_TRACE_LAST_10_LINES = r"""
    │                   └── LendingRateOracle\.getMarketBorrowRate\(_asset=DAI\) ->
    │                       35000000000000000000000000
    ├── DSProxy\.authority\(\) -> DSGuard
    ├── DSGuard\.forbid\(src=LoanShifterReceiver, dst=DSProxy, sig=0x1c\.\.0000\)
    └── DefisaverLogger\.Log\(
          _contract=DSProxy,
          _caller=tx\.origin,
          _logName="LoanShifter",
          _data=0x00\.\.0000
        \)
"""
LOCAL_GAS_REPORT = r"""
 +ContractA Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  methodWithoutArguments +1 +\d+ +\d+ +\d+ + \d+
"""
