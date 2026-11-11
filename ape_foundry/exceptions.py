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


class ForgeNotInstalledError(FoundrySubprocessError):
    """
    Raised when the ``forge`` executable is not installed.
    """

    def __init__(self):
        super().__init__(
            "Missing local `forge` executable. See ape-foundry README for install steps."
        )


class ForgeScriptError(FoundrySubprocessError):
    """
    Raised when a ``forge script`` run fails.
    """

    def __init__(self, return_code: int):
        self.return_code = return_code
        super().__init__(f"'forge script' exited with code {return_code}.")


class UnsupportedForgeSignerError(FoundryProviderError):
    """
    Raised when an account type cannot sign a ``forge script`` run.
    """

    def __init__(self, account):
        super().__init__(
            f"'{type(account).__name__}' accounts cannot sign forge scripts; use a test, "
            "keyfile or impersonated account."
        )
