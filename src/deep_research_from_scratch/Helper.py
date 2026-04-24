"""Azure OpenAI authentication helper and shared utilities."""
import json
import time
import urllib.parse  # noqa: F401 — pre-load before urllib3 can shadow it

from azure.identity import ChainedTokenCredential, DefaultAzureCredential
from dotenv import load_dotenv as _load_dotenv

_load_dotenv()
# Create a token manager that will be reused
class GenAIToken:
    """Module provides a class, GenAIToken, that represents a token for the GenAI service."""

    _shared_token: str | None = None
    _shared_expires_on: int | None = None
    _shared_refresh_threshold: int | None = None
    _credentials: ChainedTokenCredential | None = None

    def __init__(
        self,
        refresh_threshold: int = 1 * 60,
        cognitive_services: str = "https://cognitiveservices.azure.com/.default",
    ):
        """Initialize the GenAIToken object.

        Args:
            refresh_threshold (int): The threshold in seconds for refreshing the token.
                                    Default is 3600 seconds (1 hour).
            cognitive_services (str): The URL of the cognitive services endpoint.
                                    Default is "https://cognitiveservices.azure.com/.default".
        """
        self._refresh_threshold = refresh_threshold
        self._cognitive_services = cognitive_services
        if self.__class__._shared_refresh_threshold is None:
            self.__class__._shared_refresh_threshold = refresh_threshold
        else:
            self.__class__._shared_refresh_threshold = max(
                self.__class__._shared_refresh_threshold,
                refresh_threshold,
            )

        if self.__class__._shared_token is None or self.__class__._shared_expires_on is None:
            self.__class__._shared_token, self.__class__._shared_expires_on = self._get_token()

    @classmethod
    def _get_credentials(cls) -> ChainedTokenCredential:
        """Return the credentials for accessing the Azure services.

        Returns:
            ChainedTokenCredential: The credentials object.
        """
        if cls._credentials is None:
            cls._credentials = DefaultAzureCredential(exclude_interactive_browser_credential=False)
        return cls._credentials

    def _get_token(self) -> tuple[str, int]:
        """Get the token and its expiration time.

        Returns:
            tuple[str, int]: The token and its expiration time.
        """
        token = self._get_credentials().get_token(self._cognitive_services)
        return token.token, token.expires_on

    def token(self) -> str:
        """Return the token.

        If the token is expired or about to expire, it will be refreshed.

        Returns:
            str: The token.
        """
        if (
            self.__class__._shared_expires_on is None
            or self.__class__._shared_token is None
            or self.__class__._shared_expires_on < time.time() + self._refresh_threshold
        ):
            self.__class__._shared_token, self.__class__._shared_expires_on = self._get_token()
        return self.__class__._shared_token

def determine_mime_type(filename: str) -> str:
    """Determine the MIME type of a file based on its extension."""
    mime_types = {
        'pdf': 'application/pdf',
        'mp3': 'audio/mpeg',
        'mpeg': 'audio/mpeg',
        'wav': 'audio/wav',
        'png': 'image/png',
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'webp': 'image/webp',
        'txt': 'text/plain',
        'csv': 'text/plain',
        'mov': 'video/mov',
        'mp4': 'video/mp4',
        'mpg': 'video/mpg',
        'avi': 'video/avi',
        'wmv': 'video/wmv',
        'mpegps': 'video/mpegps',
        'flv': 'video/flv'
    }

    file_extension = filename.split('.')[-1].lower()
    mime_type = mime_types.get(file_extension)

    if mime_type is None:
        raise ValueError(f"Unknown file extension: {file_extension}")

    return mime_type
    """Load cached results from a JSON file"""
    try:
        with open(filename, encoding='utf-8') as f:
            cached_results = json.load(f)
        print(f"Cached results loaded from {filename}")  # noqa: T201
        return cached_results
    except FileNotFoundError:
        print(f"File {filename} not found. Starting with empty cache.")  # noqa: T201
        return {}
