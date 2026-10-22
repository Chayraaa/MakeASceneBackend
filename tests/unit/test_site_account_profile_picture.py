from unittest.mock import Mock

from app.domain_models.site_account.SiteAccount import SiteAccount
from app.repositories.storage.image.mem_image_storage import InMemoryImageStorage
from app.services.image_service import ImageService
from app.services.site_account_service import SiteAccountService


def test_profile_picture_upload_url_and_clear():
    repo, search = Mock(), Mock()
    account = SiteAccount(id=1, name="Site", creator_id=1, layout="[]")
    service = SiteAccountService(repo, Mock(), ImageService(InMemoryImageStorage("images")), search, Mock())
    service.modify_site_account(account, profile_picture="data:image/png;base64,aGVsbG8=")
    assert account.profile_picture.startswith("http://127.0.0.1:5000/v1/image/site_account/1/")
    assert account.to_dict()["picture"] == account.profile_picture
    service.modify_site_account(account, profile_picture="https://example.com/profile.png")
    assert account.profile_picture == "https://example.com/profile.png"
    service.modify_site_account(account, profile_picture="")
    assert account.profile_picture is None
    repo.update_site_account.assert_called_with(account)
