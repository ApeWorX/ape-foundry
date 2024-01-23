from pathlib import Path
from ape.api import AccountAPI, AccountContainerAPI
from ape_accounts.accounts import KeyfileAccount
from ape.types import AddressType
from eth_account import Account as EthAccount
import os
from typing import Iterator, Optional

class AccountContainer(AccountContainerAPI):
    """
    A container for Foundry accounts. Foundry accounts are stored as keyfiles
    and are identical to the ones ape uses, except they don't have a .json
    extension and are stored in a different path.
    """

    accounts_dir: Path = Path.home() / ".foundry" / "keystores"

    @property
    def aliases(self) -> Iterator[str]:
        return (p.stem for p in self.accounts_dir.glob("*"))

    @property
    def accounts(self) -> Iterator[AccountAPI]:
        return (FoundryAccount(keyfile_path=p) for p in self.accounts_dir.glob("*"))

    def __len__(self) -> int:
        return len([*self.accounts_dir.glob("*")])


class FoundryAccount(KeyfileAccount):

    _address: Optional[AddressType] = None

    @property
    def address(self) -> AddressType:
        # NOTE: Foundry uses standard Ethereum keystores which do not have an
        #      address field. We need to compute the address from the private
        #      key. Because this requires unlocking, we do two things:
        #      - return cached value (or None) if locked, to allow easy iteration
        #        over accounts without prompting for a password each time
        #      - cache the address once computed, so we don't have to compute
        #        it again, potentially requiring a password if the account
        #        is re-locked
        if self.locked:
            return self._address or "*address encrypted*" # cached value or placeholder
        if self._address is None:
            key = self._KeyfileAccount__key
            account = EthAccount.from_key(key)
            self._address = AddressType(account.address)
        return self._address
