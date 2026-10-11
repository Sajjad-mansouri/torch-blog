"""
Behavioral tests for accounts.models and accounts.authentication.

Scope: `User`, `SocialLink`, `avatar_upload_path`, `EmailAuthBackend`.

These tests exercise real database state, real Django storage, and
real password hashing. They do not inspect Django internals.
"""

import pytest
from django.db import IntegrityError

from accounts.authentication import EmailAuthBackend
from accounts.models import SocialLink, User, avatar_upload_path


# ==================================================================
# avatar_upload_path — pure function
# ==================================================================
class TestAvatarUploadPath:
    def test_uses_new_segment_when_instance_has_no_pk(self):
        user = User(username="fresh")
        assert user.pk is None

        path = avatar_upload_path(user, "photo.png")

        assert path == "avatars/new/photo.png"

    def test_uses_instance_pk_when_present(self, test_user):
        path = avatar_upload_path(test_user, "photo.png")

        assert path == f"avatars/{test_user.pk}/photo.png"

    def test_preserves_filename_verbatim(self, test_user):
        # Spaces, unicode, mixed case — must survive unchanged.
        filename = "My Photo Ünïcode.png"

        path = avatar_upload_path(test_user, filename)

        assert path.endswith(f"/{filename}")
        assert path.startswith(f"avatars/{test_user.pk}/")


# ==================================================================
# User — defaults and persistence
# ==================================================================
@pytest.mark.django_db
class TestUserDefaults:
    def test_new_user_defaults_to_reader_role(self, test_user):
        assert test_user.role == User.Role.READER

    def test_new_user_email_is_not_verified(self, test_user):
        assert test_user.is_email_verified is False

    def test_new_user_website_defaults_to_empty_string(self, test_user):
        assert test_user.website == ""

    def test_new_user_bio_defaults_to_empty_string(self, test_user):
        assert test_user.bio == ""

    def test_new_user_has_no_avatar(self, test_user):
        assert not test_user.avatar

    def test_defaults_persist_after_refresh(self, test_user):
        # Guards against "in-memory looks right but DB got something else".
        refreshed = User.objects.get(pk=test_user.pk)

        assert refreshed.role == User.Role.READER
        assert refreshed.is_email_verified is False
        assert refreshed.website == ""
        assert refreshed.bio == ""


# ==================================================================
# User — __str__
# ==================================================================
@pytest.mark.django_db
class TestUserStr:
    @pytest.mark.parametrize(
        "role, expected_label",
        [
            (User.Role.READER, "Reader"),
            (User.Role.AUTHOR, "Author"),
            (User.Role.EDITOR, "Editor"),
        ],
    )
    def test_str_includes_username_and_role_label(self, role, expected_label):
        user = User.objects.create_user(
            username="alice", email="alice@example.com", password="x", role=role
        )

        assert str(user) == f"alice ({expected_label})"


# ==================================================================
# User — role helpers
# ==================================================================
@pytest.mark.django_db
class TestUserRoleHelpers:
    @pytest.mark.parametrize(
        "role, is_reader, is_author, is_editor",
        [
            (User.Role.READER, True, False, False),
            (User.Role.AUTHOR, False, True, False),
            (User.Role.EDITOR, False, False, True),
        ],
    )
    def test_role_helpers_are_exclusive(self, role, is_reader, is_author, is_editor):
        user = User.objects.create_user(
            username="who", email="who@example.com", password="x", role=role
        )

        assert user.is_reader is is_reader
        assert user.is_author is is_author
        assert user.is_editor is is_editor


# ==================================================================
# User — permission helpers (the authorization matrix)
# ==================================================================
@pytest.mark.django_db
class TestUserPermissionHelpers:
    @pytest.mark.parametrize(
        "role, can_write, can_publish, can_review, can_manage",
        [
            (User.Role.READER, False, False, False, False),
            (User.Role.AUTHOR, True, False, False, False),
            (User.Role.EDITOR, True, True, True, True),
        ],
    )
    def test_permission_matrix(
        self, role, can_write, can_publish, can_review, can_manage
    ):
        user = User.objects.create_user(
            username="who", email="who@example.com", password="x", role=role
        )

        assert user.can_write_posts is can_write
        assert user.can_publish_posts is can_publish
        assert user.can_review_posts is can_review
        assert user.can_manage_users is can_manage


# ==================================================================
# User — display_name
# ==================================================================
@pytest.mark.django_db
class TestUserDisplayName:
    def test_falls_back_to_username_when_no_names(self, test_user):
        assert test_user.display_name == test_user.username

    def test_uses_first_name_when_only_first_name_present(self, test_user):
        test_user.first_name = "Ada"
        test_user.save(update_fields=["first_name"])

        assert test_user.display_name == "Ada"

    def test_uses_full_name_when_first_and_last_present(self, test_user):
        test_user.first_name = "Ada"
        test_user.last_name = "Lovelace"
        test_user.save(update_fields=["first_name", "last_name"])

        # Django's get_full_name() joins with a single space.
        assert test_user.display_name == "Ada Lovelace"


# ==================================================================
# User — avatar_url
# ==================================================================
@pytest.mark.django_db
class TestUserAvatarUrl:
    def test_fallback_when_no_avatar(self, test_user):
        assert test_user.avatar_url == "/static/img/default-avatar.jpg"

    def test_returns_storage_url_when_avatar_present(
        self, test_user, test_image, media_root
    ):
        test_user.avatar.save("avatar.png", test_image, save=True)

        url = test_user.avatar_url

        # Contract: URL is not the fallback, and it points at MEDIA_URL.
        assert url != "/static/img/default-avatar.jpg"
        assert url.startswith("/media/")
        # The stored file actually exists in the temporary MEDIA_ROOT.
        assert (media_root / url.removeprefix("/media/")).exists()

    def test_file_is_written_under_avatars_pk_directory(
        self, test_user, test_image, media_root
    ):
        test_user.avatar.save("avatar.png", test_image, save=True)

        expected_dir = media_root / "avatars" / str(test_user.pk)
        assert expected_dir.is_dir()
        files = list(expected_dir.iterdir())
        assert len(files) == 1
        assert files[0].name.endswith(".png")


# ==================================================================
# User — email uniqueness at the model layer
# ==================================================================
@pytest.mark.django_db
class TestUserEmailUniqueness:
    """
    Documents current behavior. `AbstractUser.email` is not
    `unique=True`, so two rows can share an email at the DB level.
    Serializers enforce uniqueness on their paths; the model does
    not. If email uniqueness becomes a model-level requirement,
    flip this test to expect IntegrityError and add the matching
    migration.
    """

    def test_two_users_can_share_email_at_the_model_layer(self):
        User.objects.create_user(
            username="first", email="shared@example.com", password="x"
        )
        User.objects.create_user(
            username="second", email="shared@example.com", password="x"
        )

        assert User.objects.filter(email="shared@example.com").count() == 2


# ==================================================================
# SocialLink
# ==================================================================
@pytest.mark.django_db
class TestSocialLinkDefaults:
    def test_defaults_and_created_at(self, test_user):
        link = SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/example",
        )

        refreshed = SocialLink.objects.get(pk=link.pk)

        assert refreshed.username == ""
        assert refreshed.order == 0
        assert refreshed.created_at is not None

    def test_default_ordering_is_by_order_then_platform(self, test_user):
        # Create in reverse of the expected order.
        SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.TWITTER,
            url="https://twitter.com/a",
            order=2,
        )
        SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/a",
            order=1,
        )
        SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.LINKEDIN,
            url="https://linkedin.com/a",
            order=1,
        )

        ordered = list(SocialLink.objects.filter(user=test_user))

        # order=1 first, ties broken by platform alphabetically:
        #   github (o=1), linkedin (o=1), twitter (o=2)
        assert [s.platform for s in ordered] == [
            SocialLink.Platform.GITHUB,
            SocialLink.Platform.LINKEDIN,
            SocialLink.Platform.TWITTER,
        ]


@pytest.mark.django_db
class TestSocialLinkConstraints:
    def test_duplicate_platform_per_user_violates_unique_constraint(self, test_user):
        SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/a",
        )

        with pytest.raises(IntegrityError):
            SocialLink.objects.create(
                user=test_user,
                platform=SocialLink.Platform.GITHUB,
                url="https://github.com/b",
            )

    def test_same_platform_for_two_users_is_allowed(self, test_user, test_author):
        SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/a",
        )
        SocialLink.objects.create(
            user=test_author,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/b",
        )

        assert (
            SocialLink.objects.filter(platform=SocialLink.Platform.GITHUB).count() == 2
        )


@pytest.mark.django_db
class TestSocialLinkCascade:
    def test_deleting_user_deletes_their_social_links(self, test_user):
        SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/a",
        )
        SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.TWITTER,
            url="https://twitter.com/a",
        )

        test_user.delete()

        assert SocialLink.objects.filter(user_id=test_user.pk).count() == 0


@pytest.mark.django_db
class TestSocialLinkStr:
    def test_str_format(self, test_user):
        link = SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.STACKOVERFLOW,
            url="https://stackoverflow.com/users/1",
        )

        assert str(link) == f"{test_user.username} - Stack Overflow"


# ==================================================================
# EmailAuthBackend
# ==================================================================
@pytest.mark.django_db
class TestEmailAuthBackend:
    def test_authenticate_by_email_returns_user(self, test_user):
        backend = EmailAuthBackend()

        result = backend.authenticate(
            request=None,
            username=test_user.email,
            password="testpass123",
        )

        assert result == test_user

    def test_authenticate_with_wrong_password_returns_none(self, test_user):
        backend = EmailAuthBackend()

        result = backend.authenticate(
            request=None,
            username=test_user.email,
            password="wrong-password",
        )

        assert result is None

    def test_authenticate_with_unknown_email_returns_none(self):
        backend = EmailAuthBackend()

        result = backend.authenticate(
            request=None,
            username="nobody@example.com",
            password="whatever",
        )

        assert result is None

    def test_get_user_returns_user_for_valid_pk(self, test_user):
        backend = EmailAuthBackend()

        assert backend.get_user(test_user.pk) == test_user

    def test_get_user_returns_none_for_unknown_pk(self):
        backend = EmailAuthBackend()

        assert backend.get_user(999_999) is None
