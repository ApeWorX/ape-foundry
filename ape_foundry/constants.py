# Extracted from Erigon chain specs
# https://github.com/ledgerwatch/erigon/tree/devel/params/chainspecs
# https://gist.github.com/banteg/e38c7d98f35286c303311168f28404ca
EVM_VERSION_BY_NETWORK = {
    "ethereum": {
        "mainnet": {
            0: "frontier",
            1150000: "homestead",
            4370000: "byzantium",
            7280000: "petersburg",
            9069000: "istanbul",
            9200000: "muirglacier",
            12244000: "berlin",
            12965000: "london",
        },
        "ropsten": {
            0: "homestead",
            1700000: "byzantium",
            4230000: "constantinople",
            4939394: "petersburg",
            6485846: "istanbul",
            7117117: "muirglacier",
            9812189: "berlin",
            10499401: "london",
        },
        "rinkeby": {
            1: "homestead",
            1035301: "byzantium",
            3660663: "constantinople",
            4321234: "petersburg",
            5435345: "istanbul",
            8290928: "berlin",
            8897988: "london",
        },
        "goerli": {
            0: "petersburg",
            1561651: "istanbul",
            4460644: "berlin",
            5062605: "london",
        },
    },
    "polygon": {
        "mainnet": {
            0: "petersburg",
            3395000: "muirglacier",
            14750000: "berlin",
            23850000: "london",
        },
        "mumbai": {
            0: "petersburg",
            2722000: "muirglacier",
            13996000: "berlin",
            22640000: "london",
        },
    },
}
