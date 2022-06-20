LOCAL_TRACE = """
ContractA.methodWithoutArguments() -> 0x00..7a9c [469604 gas]
├── CALL: SYMBOL.<0x045856de>  [461506 gas]
├── SYMBOL.methodB1(lolol="ice-cream", dynamo=345457847457457458457457457)
│   [402067 gas]
│   ├── ContractC.getSomeList() -> [
│   │     3425311345134513461345134534531452345,
│   │     111344445534535353,
│   │     993453434534534534534977788884443333
│   │   ] [370103 gas]
│   └── ContractC.methodC1(
│         windows95="simpler",
│         jamaica=345457847457457458457457457,
│         cardinal=0xF2Df0b975c0C9eFa2f8CA0491C2d1685104d2488
│       ) [363869 gas]
├── SYMBOL.callMe(blue=0x1e59ce931B4CFea3fe4B875411e280e173cB7A9C) ->
│   0x1e59ce931B4CFea3fe4B875411e280e173cB7A9C [233432 gas]
├── SYMBOL.methodB2(trombone=0x1e59ce931B4CFea3fe4B875411e280e173cB7A9C) [231951
│   gas]
│   ├── ContractC.paperwork(0xF2Df0b975c0C9eFa2f8CA0491C2d1685104d2488) -> (
│   │     os="simpler",
│   │     country=345457847457457458457457457,
│   │     wings=0xF2Df0b975c0C9eFa2f8CA0491C2d1685104d2488
│   │   ) [227360 gas]
│   ├── ContractC.methodC1(
│   │     windows95="simpler",
│   │     jamaica=0,
│   │     cardinal=0x274b028b03A250cA03644E6c578D81f019eE1323
│   │   ) [222263 gas]
│   ├── ContractC.methodC2() [147236 gas]
│   └── ContractC.methodC2() [122016 gas]
├── ContractC.addressToValue(0x1e59ce931B4CFea3fe4B875411e280e173cB7A9C) -> 0
│   [100305 gas]
├── SYMBOL.bandPractice(0x1e59ce931B4CFea3fe4B875411e280e173cB7A9C) -> 0 [94270
│   gas]
├── SYMBOL.methodB1(lolol="lemondrop", dynamo=0) [92321 gas]
│   ├── ContractC.getSomeList() -> [
│   │     3425311345134513461345134534531452345,
│   │     111344445534535353,
│   │     993453434534534534534977788884443333
│   │   ] [86501 gas]
│   └── ContractC.methodC1(
│         windows95="simpler",
│         jamaica=0,
│         cardinal=0xF2Df0b975c0C9eFa2f8CA0491C2d1685104d2488
│       ) [82729 gas]
└── SYMBOL.methodB1(lolol="snitches_get_stiches", dynamo=111) [55252 gas]
    ├── ContractC.getSomeList() -> [
    │     3425311345134513461345134534531452345,
    │     111344445534535353,
    │     993453434534534534534977788884443333
    │   ] [52079 gas]
    └── ContractC.methodC1(
          windows95="simpler",
          jamaica=111,
          cardinal=0xF2Df0b975c0C9eFa2f8CA0491C2d1685104d2488
        ) [48306 gas]
"""
MAINNET_FAIL_TRACE = """
Call trace for '0x053cba5c12172654d894f66d5670bab6215517a94189a9ffc09bc40a589ec04d'
reverted with message: "UNIV3R: min return"
txn.origin=0xd2f91C13e2D7ABbA4408Cd3D86285b7835524ad7
CALL:  AggregationRouterV4.<0x30786534>  [208466 gas]
├── CALL: 0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5.<0x128acb08>  [235702 gas]
│   ├── WETH.transfer(dst=AggregationRouterV4, wad=2098831888913057968) -> True [198998 gas]
│   ├── XDEFI.balanceOf(account=0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5) -> 1300692354907962674610343 [166172 gas]
│   │   └── (delegate) FixedToken.balanceOf(account=0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5) -> 1300692354907962674610343 [161021 gas]
│   ├── AggregationRouterV4.uniswapV3SwapCallback(
│   │     amount0Delta=12851675475480000000000,
│   │     amount1Delta=-2098831888913057968,
│   │     0x00..4ad7
│   │   ) [157874 gas]
│   │   ├── STATICCALL: 0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5.<0x0dfe1681>  [154703 gas]
│   │   ├── STATICCALL: 0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5.<0xd21220a7>  [154293 gas]
│   │   ├── STATICCALL: 0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5.<0xddca3f43>  [153845 gas]
│   │   └── XDEFI.transferFrom(
│   │         sender=tx.origin,
│   │         recipient=0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5,
│   │         amount=12851675475480000000000
│   │       ) -> True [152092 gas]
│   │       └── (delegate) FixedToken.transferFrom(
│   │             sender=tx.origin,
│   │             recipient=0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5,
│   │             amount=12851675475480000000000
│   │           ) -> True [149572 gas]
│   └── XDEFI.balanceOf(account=0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5) -> 1313544030383442674610343 [135118 gas]
│       └── (delegate) FixedToken.balanceOf(account=0x77924185CF0cbB2Ae0b746A0086A065d6875b0a5) -> 1313544030383442674610343 [132875 gas]
└── CALL: 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640.<0x128acb08>  [130650 gas]
    ├── CALL: FiatTokenProxy.<0xa9059cbb>  [102998 gas]
    │   └── (delegate) FiatTokenV2_1.transfer(to=tx.origin, value=4192051335) -> True [94297 gas]
    ├── WETH.balanceOf(0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640) -> 68357784800426962457000 [73171 gas]
    ├── AggregationRouterV4.uniswapV3SwapCallback(
    │     amount0Delta=-4192051335,
    │     amount1Delta=2098831888913057968,
    │     0x00..097d
    │   ) [69917 gas]
    │   ├── STATICCALL: 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640.<0x0dfe1681>  [68120 gas]
    │   ├── STATICCALL: 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640.<0xd21220a7>  [67710 gas]
    │   ├── STATICCALL: 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640.<0xddca3f43>  [67262 gas]
    │   └── WETH.transfer(
    │         dst=0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640,
    │         wad=2098831888913057968
    │       ) -> True [65595 gas]
    └── WETH.balanceOf(0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640) -> 68359883632315875514968 [59578 gas]
"""
MAINNET_TRACE = """
Call trace for '0xb7d7f1d5ce7743e821d3026647df486f517946ef1342a1ae93c96e4a8016eab7'
txn.origin=0x5668EAd1eDB8E2a4d724C8fb9cB5fFEabEB422dc
CALL: DSProxy.<0x30783163>  [1275643 gas]
└── (delegate) LoanShifterTaker.moveLoan(
      _exchangeData=[
        0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE,
        ZERO_ADDRESS,
        0,
        0,
        0,
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        '',
        0
      ],
      _loanShift=[
        0,
        1,
        0,
        True,
        322647834938052117610,
        48354766774065079392000,
        Dai,
        CErc20Delegator,
        GemJoin,
        CEther,
        11598,
        0
      ]
    ) [1579778 gas]
    ├── GST2.balanceOf(owner=DSProxy) -> 0 [1550845 gas]
    ├── ShifterRegistry.getAddr(_contractName="MCD_SHIFTER") -> McdShifter [1547186 gas]
    ├── McdShifter.getLoanAmount(_cdpId=11598, _joinAddr=Dai) -> 48354786024690521017562 [1543624 gas]
    │   ├── DssCdpManager.ilks(11598) -> 'ETH-A' [1517521 gas]
    │   ├── Vat.ilks('ETH-A') -> (
    │   │     Art=333364930546330776399823641,
    │   │     rate=1021289223898672834155324367,
    │   │     spot=247460000000000000000000000000,
    │   │     line=540000000000000000000000000000000000000000000000000000,
    │   │     dust=100000000000000000000000000000000000000000000000
    │   │   ) [1514626 gas]
    │   ├── DssCdpManager.urns(11598) -> UrnHandler [1508213 gas]
    │   ├── Vat.urns('ETH-A', UrnHandler) -> (ink=322647834938052117611, art=47346809202686778770770) [1505140 gas]
    │   ├── DssCdpManager.urns(11598) -> UrnHandler [1501218 gas]
    │   └── Vat.dai(UrnHandler) -> 802993823174527025406118085 [1498156 gas]
    ├── ShifterRegistry.getAddr(_contractName="LOAN_SHIFTER_RECEIVER") -> LoanShifterReceiver [1513897 gas]
    ├── CALL: LoanShifterReceiver  [3000 gas]
    ├── DSProxy.authority() -> DSGuard [1509589 gas]
    ├── DSGuard.permit(src=LoanShifterReceiver, dst=DSProxy, sig=0x1c..0000) [1506402 gas]
    ├── CALL: InitializableAdminUpgradeabilityProxy.<0x5cffe9de>  [1478494 gas]
    │   └── (delegate) LendingPool.flashLoan(
    │         _receiver=LoanShifterReceiver,
    │         _reserve=Dai,
    │         _amount=48354786024690521017562,
    │         _params=0x00..0000
    │       ) [1452618 gas]
    │       ├── STATICCALL: InitializableAdminUpgradeabilityProxy.<0x05075d6e>  [1421040 gas]
    │       │   └── (delegate) LendingPoolCore.getReserveIsActive(_reserve=Dai) -> True [1396219 gas]
    │       ├── DAI.balanceOf(InitializableAdminUpgradeabilityProxy) -> 10684533234693042314924969 [1414582 gas]
    │       ├── STATICCALL: InitializableAdminUpgradeabilityProxy.<0x586feb40>  [1410882 gas]
    │       │   └── (delegate) LendingPoolParametersProvider.getFlashLoanFeesInBips() -> [9, 3000] [1386223 gas]
    │       ├── CALL: InitializableAdminUpgradeabilityProxy.<0xfa93b2a5>  [1404860 gas]
    │       │   └── (delegate) LendingPoolCore.transferToUser(
    │       │         _reserve=Dai,
    │       │         _user=LoanShifterReceiver,
    │       │         _amount=48354786024690521017562
    │       │       ) [1380252 gas]
    │       │       └── DAI.transfer(dst=LoanShifterReceiver, wad=48354786024690521017562) -> True [1355286 gas]
    │       ├── LoanShifterReceiver.executeOperation(
    │       │     _reserve=Dai,
    │       │     _amount=48354786024690521017562,
    │       │     _fee=43519307422221468915,
    │       │     _params=0x00..0000
    │       │   ) [1365176 gas]
    │       │   ├── ShifterRegistry.getAddr(_contractName="MCD_SHIFTER") -> McdShifter [1334090 gas]
    │       │   ├── ShifterRegistry.getAddr(_contractName="COMP_SHIFTER") -> CompShifter [1330143 gas]
    │       │   ├── DAI.transfer(dst=DSProxy, wad=48354786024690521017562) -> True [1325760 gas]
    │       │   ├── CALL: DSProxy  [3000 gas]
    │       │   ├── DSProxy.execute(_target=McdShifter, _data=0x8d..046a) -> '' [1296546 gas]
    │       │   │   ├── DSGuard.canCall(src_=LoanShifterReceiver, dst_=DSProxy, sig=0x1cff79cd) -> True [1271307 gas]
    │       │   │   └── (delegate) McdShifter.close(
    │       │   │         _cdpId=11598,
    │       │   │         _joinAddr=GemJoin,
    │       │   │         _loanAmount=48354786024690521017562,
    │       │   │         _collateral=322647834938052117610
    │       │   │       ) [1263595 gas]
    │       │   │       ├── DssCdpManager.owns(11598) -> DSProxy [1241823 gas]
    │       │   │       ├── DSProxy.owner() -> tx.origin [1238873 gas]
    │       │   │       ├── DssCdpManager.ilks(11598) -> 'ETH-A' [1235815 gas]
    │       │   │       ├── DssCdpManager.vat() -> Vat [1232928 gas]
    │       │   │       ├── DssCdpManager.urns(11598) -> UrnHandler [1230064 gas]
    │       │   │       ├── Vat.urns('ETH-A', UrnHandler) -> (ink=322647834938052117611, art=47346809202686778770770) [1226950 gas]
    │       │   │       ├── Vat.ilks('ETH-A') -> (
    │       │   │       │     Art=333364930546330776399823641,
    │       │   │       │     rate=1021289223898672834155324367,
    │       │   │       │     spot=247460000000000000000000000000,
    │       │   │       │     line=540000000000000000000000000000000000000000000000000000,
    │       │   │       │     dust=100000000000000000000000000000000000000000000000
    │       │   │       │   ) [1223091 gas]
    │       │   │       ├── DssCdpManager.urns(11598) -> UrnHandler [1216363 gas]
    │       │   │       ├── Vat.ilks('ETH-A') -> (
    │       │   │       │     Art=333364930546330776399823641,
    │       │   │       │     rate=1021289223898672834155324367,
    │       │   │       │     spot=247460000000000000000000000000,
    │       │   │       │     line=540000000000000000000000000000000000000000000000000000,
    │       │   │       │     dust=100000000000000000000000000000000000000000000000
    │       │   │       │   ) [1213226 gas]
    │       │   │       ├── Vat.urns('ETH-A', UrnHandler) -> (ink=322647834938052117611, art=47346809202686778770770) [1206844 gas]
    │       │   │       ├── Vat.dai(UrnHandler) -> 802993823174527025406118085 [1202964 gas]
    │       │   │       ├── DAI.allowance(DSProxy, DaiJoin) -> 0 [1199562 gas]
    │       │   │       ├── DAI.approve(
    │       │   │       │     usr=DaiJoin,
    │       │   │       │     wad=115792089237316195423570985008687907853269984665640564039457584007913129639935
    │       │   │       │   ) -> True [1196465 gas]
    │       │   │       ├── DaiJoin.join(usr=UrnHandler, wad=48354786024690521017562) [1172639 gas]
    │       │   │       │   ├── Vat.move(
    │       │   │       │   │     src=DaiJoin,
    │       │   │       │   │     dst=UrnHandler,
    │       │   │       │   │     rad=48354786024690521017562000000000000000000000000000
    │       │   │       │   │   ) [1151523 gas]
    │       │   │       │   └── DAI.burn(usr=DSProxy, wad=48354786024690521017562) [1131471 gas]
    │       │   │       ├── Vat.dai(UrnHandler) -> 48354786024690521017562802993823174527025406118085 [1132005 gas]
    │       │   │       ├── Vat.ilks('ETH-A') -> (
    │       │   │       │     Art=333364930546330776399823641,
    │       │   │       │     rate=1021289223898672834155324367,
    │       │   │       │     spot=247460000000000000000000000000,
    │       │   │       │     line=540000000000000000000000000000000000000000000000000000,
    │       │   │       │     dust=100000000000000000000000000000000000000000000000
    │       │   │       │   ) [1129085 gas]
    │       │   │       ├── Vat.urns('ETH-A', UrnHandler) -> (ink=322647834938052117611, art=47346809202686778770770) [1122703 gas]
    │       │   │       ├── DssCdpManager.frob(cdp=11598, dink=0, dart=-47346809202686778770770) [1118678 gas]
    │       │   │       │   └── Vat.frob(
    │       │   │       │         i='ETH-A',
    │       │   │       │         u=UrnHandler,
    │       │   │       │         v=UrnHandler,
    │       │   │       │         w=UrnHandler,
    │       │   │       │         dink=0,
    │       │   │       │         dart=-47346809202686778770770
    │       │   │       │       ) [1095663 gas]
    │       │   │       ├── DssCdpManager.frob(cdp=11598, dink=-322647834938052117610, dart=0) [1064536 gas]
    │       │   │       │   └── Vat.frob(
    │       │   │       │         i='ETH-A',
    │       │   │       │         u=UrnHandler,
    │       │   │       │         v=UrnHandler,
    │       │   │       │         w=UrnHandler,
    │       │   │       │         dink=-322647834938052117610,
    │       │   │       │         dart=0
    │       │   │       │       ) [1042367 gas]
    │       │   │       ├── DssCdpManager.flux(cdp=11598, dst=DSProxy, wad=322647834938052117610) [999964 gas]
    │       │   │       │   └── Vat.flux(
    │       │   │       │         ilk='ETH-A',
    │       │   │       │         src=UrnHandler,
    │       │   │       │         dst=DSProxy,
    │       │   │       │         wad=322647834938052117610
    │       │   │       │       ) [978844 gas]
    │       │   │       ├── GemJoin.dec() -> 18 [959971 gas]
    │       │   │       ├── GemJoin.exit(usr=DSProxy, wad=322647834938052117610) [957179 gas]
    │       │   │       │   ├── Vat.slip(ilk='ETH-A', usr=DSProxy, wad=-322647834938052117610) [938667 gas]
    │       │   │       │   └── WETH.transfer(dst=DSProxy, wad=322647834938052117610) -> True [928712 gas]
    │       │   │       ├── GemJoin.gem() -> WETH9 [907991 gas]
    │       │   │       ├── GemJoin.gem() -> WETH9 [905041 gas]
    │       │   │       ├── WETH.withdraw(wad=322647834938052117610) [902143 gas]
    │       │   │       │   └── CALL: DSProxy  [9700 gas] [322.64783494 value]
    │       │   │       ├── GemJoin.gem() -> WETH9 [888841 gas]
    │       │   │       └── CALL: LoanShifterReceiver  [9700 gas] [322.64783494 value]
    │       │   ├── CALL: DSProxy  [9700 gas] [322.64783494 value]
    │       │   ├── DSProxy.execute(_target=CompShifter, _data=0xf4..11cd) -> '' [909826 gas]
    │       │   │   ├── DSGuard.canCall(src_=LoanShifterReceiver, dst_=DSProxy, sig=0x1cff79cd) -> True [890636 gas]
    │       │   │   └── (delegate) CompShifter.open(
    │       │   │         _cCollAddr=CEther,
    │       │   │         _cBorrowAddr=CErc20Delegator,
    │       │   │         _debtAmount=48398305332112742486477
    │       │   │       ) [883181 gas]
    │       │   │       ├── cDAI.underlying() -> Dai [867384 gas]
    │       │   │       ├── CALL: Unitroller.<0xc2998238>  [864100 gas]
    │       │   │       │   └── (delegate) Comptroller.enterMarkets(cTokens=['CEther']) -> [0] [848828 gas]
    │       │   │       ├── cETH.mint() [792439 gas] [322.64783494 value]
    │       │   │       │   ├── WhitePaperInterestRateModel.getBorrowRate(
    │       │   │       │   │     cash=877351454208435550173127,
    │       │   │       │   │     borrows=71532761571023032787465,
    │       │   │       │   │     _reserves=85036995401300782846
    │       │   │       │   │   ) -> [0, 13098657989] [762396 gas]
    │       │   │       │   ├── CALL: Unitroller.<0x4ef4c3e1>  [723939 gas]
    │       │   │       │   │   └── (delegate) Comptroller.mintAllowed(
    │       │   │       │   │         cToken=CEther,
    │       │   │       │   │         minter=DSProxy,
    │       │   │       │   │         mintAmount=322647834938052117610
    │       │   │       │   │       ) -> 0 [710857 gas]
    │       │   │       │   │       ├── cETH.totalSupply() -> 4737635605632584 [694083 gas]
    │       │   │       │   │       └── cETH.balanceOf(owner=DSProxy) -> 0 [660582 gas]
    │       │   │       │   └── CALL: Unitroller.<0x41c728b9>  [635900 gas]
    │       │   │       │       └── (delegate) Comptroller.mintVerify(
    │       │   │       │             cToken=CEther,
    │       │   │       │             minter=DSProxy,
    │       │   │       │             actualMintAmount=322647834938052117610,
    │       │   │       │             mintTokens=1611076291918
    │       │   │       │           ) [624188 gas]
    │       │   │       ├── CALL: Unitroller.<0xc2998238>  [642849 gas]
    │       │   │       │   └── (delegate) Comptroller.enterMarkets(cTokens=['CErc20Delegator']) -> [0] [631034 gas]
    │       │   │       ├── cDAI.borrow(borrowAmount=48398305332112742486477) -> 0 [589960 gas]
    │       │   │       │   └── (delegate) CDaiDelegate.borrow(borrowAmount=48398305332112742486477) -> 0 [578445 gas]
    │       │   │       │       ├── Pot.drip() -> 1018008449363110619399951035 [560289 gas]
    │       │   │       │       │   └── Vat.suck(u=Vow, v=Pot, rad=0) [535897 gas]
    │       │   │       │       ├── Pot.pie(CErc20Delegator) -> 284260123136722085910285951 [524992 gas]
    │       │   │       │       ├── Pot.chi() -> 1018008449363110619399951035 [522194 gas]
    │       │   │       │       ├── DAIInterestRateModelV3.getBorrowRate(
    │       │   │       │       │     cash=289379207170181335004456462,
    │       │   │       │       │     borrows=941810534050634017587632492,
    │       │   │       │       │     reserves=740992012814482879709740
    │       │   │       │       │   ) -> 18203490479 [516927 gas]
    │       │   │       │       ├── CALL: Unitroller.<0xda3d454c>  [479751 gas]
    │       │   │       │       │   └── (delegate) Comptroller.borrowAllowed(
    │       │   │       │       │         cToken=CErc20Delegator,
    │       │   │       │       │         borrower=DSProxy,
    │       │   │       │       │         borrowAmount=48398305332112742486477
    │       │   │       │       │       ) -> 0 [470485 gas]
    │       │   │       │       │       ├── UniswapAnchoredView.getUnderlyingPrice(cToken=CErc20Delegator) -> 1008191000000000000 [457718 gas]
    │       │   │       │       │       ├── cETH.getAccountSnapshot(account=DSProxy) -> [
    │       │   │       │       │       │     0,
    │       │   │       │       │       │     1611076291918,
    │       │   │       │       │       │     0,
    │       │   │       │       │       │     200268501595128483184821061
    │       │   │       │       │       │   ] [448905 gas]
    │       │   │       │       │       ├── UniswapAnchoredView.getUnderlyingPrice(cToken=CEther) -> 372470000000000000000 [437795 gas]
    │       │   │       │       │       ├── cDAI.getAccountSnapshot(account=DSProxy) -> [0, 0, 0, 207212981963466297091815184] [429670 gas]
    │       │   │       │       │       │   └── cDAI.delegateToImplementation(data=0xc3..52dd) -> 0x00..f710 [420666 gas]
    │       │   │       │       │       │       └── (delegate) CDaiDelegate.getAccountSnapshot(account=DSProxy) -> [0, 0, 0, 207212981963466297091815184] [411653 gas]
    │       │   │       │       │       │           ├── Pot.pie(CErc20Delegator) -> 284260123136722085910285951 [399791 gas]
    │       │   │       │       │       │           └── Pot.chi() -> 1018008449363110619399951035 [396992 gas]
    │       │   │       │       │       ├── UniswapAnchoredView.getUnderlyingPrice(cToken=CErc20Delegator) -> 1008191000000000000 [406426 gas]
    │       │   │       │       │       ├── cDAI.borrowIndex() -> 1043822572059955633 [396422 gas]
    │       │   │       │       │       └── cDAI.totalBorrows() -> 941810568339112196812875778 [391711 gas]
    │       │   │       │       ├── Pot.pie(CErc20Delegator) -> 284260123136722085910285951 [370881 gas]
    │       │   │       │       ├── Pot.chi() -> 1018008449363110619399951035 [368082 gas]
    │       │   │       │       ├── Pot.chi() -> 1018008449363110619399951035 [361087 gas]
    │       │   │       │       ├── Pot.exit(wad=47542145020890376480893) [358200 gas]
    │       │   │       │       │   └── Vat.move(
    │       │   │       │       │         src=Pot,
    │       │   │       │       │         dst=CErc20Delegator,
    │       │   │       │       │         rad=48398305332112742486477763707302301597839813074255
    │       │   │       │       │       ) [337234 gas]
    │       │   │       │       ├── DaiJoin.exit(usr=DSProxy, wad=48398305332112742486477) [319250 gas]
    │       │   │       │       │   ├── Vat.move(
    │       │   │       │       │   │     src=CErc20Delegator,
    │       │   │       │       │   │     dst=DaiJoin,
    │       │   │       │       │   │     rad=48398305332112742486477000000000000000000000000000
    │       │   │       │       │   │   ) [310617 gas]
    │       │   │       │       │   └── DAI.mint(usr=DSProxy, wad=48398305332112742486477) [298832 gas]
    │       │   │       │       └── CALL: Unitroller.<0x5c778605>  [228678 gas]
    │       │   │       │           └── (delegate) Comptroller.borrowVerify(
    │       │   │       │                 cToken=CErc20Delegator,
    │       │   │       │                 borrower=DSProxy,
    │       │   │       │                 borrowAmount=48398305332112742486477
    │       │   │       │               ) [223335 gas]
    │       │   │       ├── DAI.balanceOf(DSProxy) -> 48398305332112742486477 [240919 gas]
    │       │   │       └── DAI.transfer(dst=LoanShifterReceiver, wad=48398305332112742486477) -> True [238005 gas]
    │       │   ├── LendingPoolAddressesProvider.getLendingPoolCore() -> InitializableAdminUpgradeabilityProxy [237443 gas]
    │       │   └── DAI.transfer(
    │       │         dst=InitializableAdminUpgradeabilityProxy,
    │       │         wad=48398305332112742486477
    │       │       ) -> True [233519 gas]
    │       ├── DAI.balanceOf(InitializableAdminUpgradeabilityProxy) -> 10684576754000464536393884 [244972 gas]
    │       └── CALL: InitializableAdminUpgradeabilityProxy.<0x09ac2953>  [241025 gas]
    │           └── (delegate) LendingPoolCore.updateStateOnFlashLoan(
    │                 _reserve=Dai,
    │                 _availableLiquidityBefore=10684533234693042314924969,
    │                 _income=30463515195555028241,
    │                 _protocolFee=13055792226666440674
    │               ) [234627 gas]
    │               ├── LendingPoolAddressesProvider.getTokenDistributor() -> InitializableAdminUpgradeabilityProxy [227466 gas]
    │               ├── DAI.transfer(
    │               │     dst=InitializableAdminUpgradeabilityProxy,
    │               │     wad=13055792226666440674
    │               │   ) -> True [224005 gas]
    │               ├── DAI.balanceOf(InitializableAdminUpgradeabilityProxy) -> 10684563698208237869953210 [181734 gas]
    │               └── OptimizedReserveInterestRateStrategy.calculateInterestRates(
    │                     _reserve=Dai,
    │                     _availableLiquidity=10684594161723433424981451,
    │                     _totalBorrowsStable=4087641944510702330917327,
    │                     _totalBorrowsVariable=11620401514013264063886023,
    │                     _averageStableBorrowRate=75619477990158369945895021
    │                   ) -> (
    │                     currentLiquidityRate=39043727754079106944517822,
    │                     currentStableBorrowRate=79637571899426327680798964,
    │                     currentVariableBorrowRate=62077167215997382294265458
    │                   ) [176223 gas]
    │                   ├── LendingPoolAddressesProvider.getLendingRateOracle() -> LendingRateOracle [170119 gas]
    │                   └── LendingRateOracle.getMarketBorrowRate(_asset=Dai) -> 35000000000000000000000000 [167314 gas]
    ├── DSProxy.authority() -> DSGuard [185527 gas]
    ├── DSGuard.forbid(src=LoanShifterReceiver, dst=DSProxy, sig=0x1c..0000) [182344 gas]
    └── DefisaverLogger.Log(
          _contract=DSProxy,
          _caller=tx.origin,
          _logName="LoanShifter",
          _data=0x00..0000
        ) [174327 gas]
"""
