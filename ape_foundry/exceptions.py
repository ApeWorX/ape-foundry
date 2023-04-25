from ape.exceptions import ProviderError, SubprocessError


class FoundryProviderError(ProviderError):
    """
    An error related to the Foundry network provider plugin.
    """


class FoundrySubprocessError(FoundryProviderError, SubprocessError):
    """
    An error related to launching subprocesses to run Foundry.
    """


class FoundryNotInstalledError(FoundrySubprocessError):
    """
    Raised when Foundry is not installed.
    """

    def __init__(self):
        super().__init__(
            "Missing local Foundry node client. See ape-foundry README for install steps."
        )
