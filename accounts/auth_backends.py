import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars


logger = logging.getLogger(__name__)


class ActiveDirectoryBackend(ModelBackend):
    """
    Authenticate users against Active Directory when the integration is enabled.
    Local Django permissions/groups remain the source of authorization.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not settings.USE_AD_AUTH:
            return None

        username = (username or "").strip()
        password = password or ""
        if not username or not password:
            return None

        local_admin_username = (settings.DJANGO_SUPERUSER_USERNAME or "").strip().lower()
        if local_admin_username and username.lower() == local_admin_username:
            return None

        ad_user = self._authenticate_against_ad(username, password)
        if not ad_user:
            return None

        return self._get_or_create_local_user(ad_user)

    def _authenticate_against_ad(self, username, password):
        server = Server(settings.AD_SERVER_URI, get_info=ALL)

        try:
            with Connection(
                server,
                user=settings.AD_BIND_DN,
                password=settings.AD_BIND_PASSWORD,
                auto_bind=True,
                raise_exceptions=True,
            ) as service_connection:
                user_entry = self._find_user(service_connection, username)
                if not user_entry:
                    return None

            with Connection(
                server,
                user=user_entry.entry_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=True,
            ):
                return {
                    "username": self._normalize_username(user_entry),
                    "email": self._read_attr(user_entry, "mail"),
                    "first_name": self._read_attr(user_entry, "givenName"),
                    "last_name": self._read_attr(user_entry, "sn"),
                }

        except LDAPException as exc:
            logger.warning("Falha na autenticacao AD para '%s': %s", username, exc)
            return None

    def _find_user(self, connection, username):
        normalized = username.strip()
        sam_account_name = normalized.split("@", 1)[0].split("\\", 1)[-1]
        upn_candidate = normalized
        if "@" not in upn_candidate and settings.AD_DEFAULT_DOMAIN:
            upn_candidate = f"{sam_account_name}@{settings.AD_DEFAULT_DOMAIN_FQDN}"

        search_filter = (
            "(|"
            f"(sAMAccountName={escape_filter_chars(sam_account_name)})"
            f"(userPrincipalName={escape_filter_chars(upn_candidate)})"
            f"(mail={escape_filter_chars(normalized)})"
            ")"
        )

        found = connection.search(
            search_base=settings.AD_USER_SEARCH_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=["sAMAccountName", "userPrincipalName", "mail", "givenName", "sn"],
            size_limit=1,
        )
        if not found or not connection.entries:
            return None
        return connection.entries[0]

    def _get_or_create_local_user(self, ad_user):
        UserModel = get_user_model()
        username = ad_user["username"]
        defaults = {
            "email": ad_user["email"],
            "first_name": ad_user["first_name"],
            "last_name": ad_user["last_name"],
            "is_active": True,
        }
        user, created = UserModel.objects.get_or_create(username=username, defaults=defaults)

        changed = False
        for field in ("email", "first_name", "last_name"):
            value = ad_user.get(field) or ""
            if getattr(user, field, "") != value:
                setattr(user, field, value)
                changed = True

        if not user.is_active:
            user.is_active = True
            changed = True

        if created:
            user.set_unusable_password()
            changed = True

        if changed:
            user.save()

        return user

    def _normalize_username(self, user_entry):
        sam_account_name = self._read_attr(user_entry, "sAMAccountName")
        if sam_account_name:
            return sam_account_name.lower()

        upn = self._read_attr(user_entry, "userPrincipalName")
        if upn:
            return upn.split("@", 1)[0].lower()

        return user_entry.entry_dn.lower()

    @staticmethod
    def _read_attr(user_entry, attr_name):
        try:
            value = getattr(user_entry, attr_name).value
        except Exception:
            value = None
        return "" if value is None else str(value).strip()
