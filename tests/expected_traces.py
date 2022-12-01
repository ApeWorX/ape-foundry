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
'0x([A-Fa-f0-9]{64})'
reverted with message: "UNIV3R: min return"
tx.origin=0x[a-fA-F0-9]{40}
AggregationRouterV4.uniswapV3Swap\(
  amount=12851675475480000000000,
  minReturn=4205588148,
  pools=\[
    682631518358379038160760928734868612545194078373,
    5789604461865809771178549250512551984713807685540901737341300416798777562476
"""
MAINNET_FAIL_TRACE_LAST_10_LINES = r"""
    │   ├── STATICCALL: 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640\.<0xd21220a7>
    │   │   \[\d+ gas\]
    │   ├── STATICCALL: 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640\.<0xddca3f43>
    │   │   \[\d+ gas\]
    │   └── WETH\.transfer\(
    │         dst=0x[a-fA-F0-9]{40},
    │         wad=2098831888913057968
    │       \) -> True \[\d+ gas\]
    └── WETH\.balanceOf\(0x[a-fA-F0-9]{40}\) ->
        68359883632315875514968 \[\d+ gas\]
"""
MAINNET_TRACE_FIRST_10_LINES = r"""
Call trace for
'0x([A-Fa-f0-9]{64})'
tx.origin=0x[a-fA-F0-9]{40}
DSProxy\.execute\(_target=LoanShifterTaker, _data=0x35\.\.0000\) -> '' \[\d+ gas\]
└── \(delegate\) LoanShifterTaker\.moveLoan\(
      _exchangeData=\[
        0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE,
        ZERO_ADDRESS,
        0,
        0,
"""
MAINNET_TRACE_LAST_10_LINES = r"""
    │                       35000000000000000000000000 \[\d+ gas\]
    ├── DSProxy\.authority\(\) -> DSGuard \[\d+ gas\]
    ├── DSGuard\.forbid\(src=LoanShifterReceiver, dst=DSProxy, sig=0x1c\.\.0000\)
    │   \[\d+ gas\]
    └── DefisaverLogger\.Log\(
          _contract=DSProxy,
          _caller=tx\.origin,
          _logName="LoanShifter",
          _data=0x00\.\.0000
        \) \[\d+ gas\]"""
LOCAL_GAS_REPORT = r"""
 +ContractA Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  methodWithoutArguments +1 +\d+ +\d+ +\d+ + \d+

 +ContractB Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  methodB1 +3 +\d+ +\d+ +\d+ + \d+
  callMe +1 +\d+ +\d+ +\d+ + \d+
  methodB2 +1 +\d+ +\d+ +\d+ + \d+
  bandPractice +1 +\d+ +\d+ +\d+ + \d+

 +ContractC Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  getSomeList +3 +\d+ +\d+ +\d+ + \d+
  methodC1 +4 +\d+ +\d+ +\d+ + \d+
  paperwork +1 +\d+ +\d+ +\d+ + \d+
  methodC2 +2 +\d+ +\d+ +\d+ + \d+
  addressToValue +1 +\d+ +\d+ +\d+ + \d+
"""
