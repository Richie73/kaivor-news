"""Provider boundary. BorrowBox sync is deliberately not implemented pending approval."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderCapabilities:
    catalog_search: bool = False
    loans: bool = False
    due_dates: bool = False
    progress_sync: bool = False


class ReadingProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> ProviderCapabilities: ...


class BorrowBoxProvider:
    """Safe placeholder adapter: launches the official service, never scrapes it."""
    name = "borrowbox"
    capabilities = ProviderCapabilities()
    launch_url = "https://www.borrowbox.com/"

    def get_launch_url(self) -> str:
        return self.launch_url

    def sync(self):
        raise NotImplementedError(
            "BorrowBox synchronization is disabled until Bolinda confirms an authorized integration method."
        )
