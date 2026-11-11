import pytest
from ape_accounts import generate_account

from ape_foundry.scripting import run_forge_script

TRANSFER_SCRIPT = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

interface Vm {
    function envAddress(string calldata name) external view returns (address);
    function startBroadcast() external;
    function stopBroadcast() external;
}

contract Transfer {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run() external {
        address recipient = vm.envAddress("RECIPIENT");
        vm.startBroadcast();
        payable(recipient).transfer(1 ether);
        vm.stopBroadcast();
    }
}
"""
KEYFILE_PASSPHRASE = "example"


@pytest.fixture
def forge_project(tmp_path):
    (tmp_path / "foundry.toml").write_text('[profile.default]\nsrc = "src"\nscript = "script"\n')
    (tmp_path / "script").mkdir()
    script_path = tmp_path / "script" / "Transfer.s.sol"
    script_path.write_text(TRANSFER_SCRIPT)
    return script_path


@pytest.fixture
def recipient_env(mocker, receiver):
    return mocker.patch.dict("os.environ", {"RECIPIENT": str(receiver.address)})


@pytest.fixture
def keyfile_account(owner):
    account, _ = generate_account("forge-signer", KEYFILE_PASSPHRASE)
    owner.transfer(account, "2 ether")
    yield account
    account.keyfile_path.unlink()


def test_run_forge_script_broadcasts_as_a_test_account(
    connected_provider, forge_project, recipient_env, owner, receiver
):
    receiver_balance = receiver.balance

    run_forge_script(
        forge_project,
        connected_provider,
        owner,
        broadcast=True,
        forge_args=("--root", str(forge_project.parent.parent)),
    )

    assert receiver.balance == receiver_balance + 10**18


def test_run_forge_script_signs_with_a_keyfile(
    connected_provider, forge_project, recipient_env, keyfile_account, receiver
):
    receiver_balance = receiver.balance

    run_forge_script(
        forge_project,
        connected_provider,
        keyfile_account,
        broadcast=True,
        forge_args=("--root", str(forge_project.parent.parent), "--password", KEYFILE_PASSPHRASE),
    )

    assert receiver.balance == receiver_balance + 10**18
    assert keyfile_account.nonce == 1
