from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import FileTooLargeException, InvalidFileException
from app.services.storage import StorageService
from app.services.storage_paths import StorageFolder


class TestStorageServiceErrors:
    """Regression tests for storage exception handling."""

    @pytest.mark.asyncio
    async def test_upload_agent_avatar_preserves_invalid_file_error(self):
        service = StorageService()
        service.supabase = MagicMock()

        file = UploadFile(
            filename="avatar.txt",
            file=BytesIO(b"not-an-image"),
            headers=Headers({"content-type": "text/plain"}),
        )

        with pytest.raises(InvalidFileException):
            await service.upload_agent_avatar(file, agent_id=1)

    @pytest.mark.asyncio
    async def test_create_presigned_upload_oversize_returns_413_exception(self):
        service = StorageService()
        db = MagicMock()

        with pytest.raises(FileTooLargeException) as exc_info:
            await service.create_presigned_upload(
                filename="huge.jpg",
                content_type="image/jpeg",
                file_size=service._max_upload_bytes + 1,
                user_id=1,
                db=db,
                folder=StorageFolder.GENERIC_UPLOAD,
            )

        assert exc_info.value.status_code == 413
