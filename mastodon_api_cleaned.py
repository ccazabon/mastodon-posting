"""
Wrapper providing a higher-level API around the official Mastodon Python library, for retrieving
or posting statuses ("toots").

Copyright © 2023 Charles Cazabon <charlesc-github-projects AT pyropus.ca>.

Licensed under the GNU General Public License version 2 (only).  See the file COPYING
for details.
"""
import sys
import time
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from mastodon import Mastodon, MastodonError, MastodonIllegalArgumentError
from mastodon.utility import AttribAccessDict
import yaml


APPLICATION_NAME = "my-app-name"


class MastodonClientApp:
    def __init__(self, config_dir: Path | None = None, base_url: str | None = None):
        self.config: AttribAccessDict
        self.config_dir: Path = (
            config_dir if config_dir else Path.home() / ".config" / APPLICATION_NAME
        )
        self.config_file: Path = self.config_dir / "config.yaml"

        if not self.config_dir.is_dir():
            raise ValueError(f"{self.config_dir}: no such directory")

        if not self.config_file.is_file():
            raise ValueError(f"{self.config_file}: no such file")

        self._load_config()

        if self.config.instance.base_url and base_url:
            # one or the other, not both
            raise ValueError(f"already have base_url {self.config.instance.base_url}")

        if not self.config.get("application", {}).get("client_id", None):
            assert self.config.get("instance", None) is None
            self.config["instance"] = AttribAccessDict()
            self.config["instance"]["base_url"] = base_url
            self.register_app()

        if not self.config.get("user", None):
            self.config["user"] = AttribAccessDict()

        self.connect()

        self._save_config()

    def orig_connect(self):
        # Note: this didn't work correctly.  I would get credentials back but they would not
        # work for future requests, or it failed to refresh the access token, or something like
        # that - I don't remember exactly as it's been a while.  I disabled this code and just
        # always do the dumb email/password login instead, in connect() below.

        init_args = AttribAccessDict(
            api_base_url=self.config.instance.base_url,
            # debug_requests=False,
            ratelimit_method="pace",
            ratelimit_pacefactor=1.1,
            request_timeout=defaults.request_timeout,
            # mastodon_version=None,
            version_check_mode="created",
            # Requests session
            # session=None,
            feature_set="mainline",
            user_agent=APPLICATION_NAME,
            lang="en",
        )
        if self.config.user.access_token:
            init_args["access_token"] = self.config.user.access_token
        else:
            init_args["client_id"] = self.config.application.client_id
            init_args["client_secret"] = self.config.application.client_secret

        self.mastodon = Mastodon(
            **init_args
        )

        login_args = AttribAccessDict(
            scopes=['read', 'write'],
        )
        if self.config.user.get("access_token", None):
            login_args["refresh_token"] = self.config.user.access_token
        else:
            login_args["username"] = self.config.user.username
            login_args["password"] = self.config.user.password

        try:
            access_token = self.mastodon.log_in(**login_args)
            self.config.user["access_token"] = access_token
        except MastodonIllegalArgumentError as e:
            # die(), not shown here, just logs the exception with as much info as possible
            # and exits.
            die("login error", exit_code=10, exception=e, show_stack=defaults.debug)

        if not self.config.user.get("preferences", None):
            preferences = self.mastodon.preferences()
            self.config.user["preferences"] = AttribAccessDict()
            self.config.user.preferences.update(preferences)

    def connect(self):
        self.mastodon = Mastodon(
            client_id="my-application-clientcred.secret",
            api_base_url=self.config.instance.base_url,
        )

        r = self.mastodon.log_in(
            "<email>",
            password="<password>",
            to_file="my-application-usercred.secret",
        )
        self.user = self.mastodon.me()

    def get_statuses(self, limit: int):
        """Returns a list of status dicts."""
        # Each dict is:
        # {
        #     'id': # Numerical id of this toot
        #     'uri': # Descriptor for the toot
        #         # EG 'tag:mastodon.social,2016-11-25:objectId=<id>:objectType=Status'
        #     'url': # URL of the toot
        #     'account': # User dict for the account which posted the status
        #     'in_reply_to_id': # Numerical id of the toot this toot is in response to
        #     'in_reply_to_account_id': # Numerical id of the account this toot is in response to
        #     'reblog': # Denotes whether the toot is a reblog. If so, set to the original toot dict.
        #     'content': # Content of the toot, as HTML: '<p>Hello from Python</p>'
        #     'created_at': # Creation time
        #     'reblogs_count': # Number of reblogs
        #     'favourites_count': # Number of favourites
        #     'reblogged': # Denotes whether the logged in user has boosted this toot
        #     'favourited': # Denotes whether the logged in user has favourited this toot
        #     'sensitive': # Denotes whether media attachments to the toot are marked sensitive
        #     'spoiler_text': # Warning text that should be displayed before the toot content
        #     'visibility': # Toot visibility ('public', 'unlisted', 'private', or 'direct')
        #     'mentions': # A list of users dicts mentioned in the toot, as Mention dicts
        #     'media_attachments': # A list of media dicts of attached files
        #     'emojis': # A list of custom emojis used in the toot, as Emoji dicts
        #     'tags': # A list of hashtag used in the toot, as Hashtag dicts
        #     'bookmarked': # True if the status is bookmarked by the logged in user, False if not.
        #     'application': # Application dict for the client used to post the toot (Does not federate
        #                    # and is therefore always None for remote toots, can also be None for
        #                    # local toots for some legacy applications).
        #     'language': # The language of the toot, if specified by the server,
        #                 # as ISO 639-1 (two-letter) language code.
        #     'muted': # Boolean denoting whether the user has muted this status by
        #              # way of conversation muting
        #     'pinned': # Boolean denoting whether or not the status is currently pinned for the
        #               # associated account.
        #     'replies_count': # The number of replies to this status.
        #     'card': # A preview card for links from the status, if present at time of delivery,
        #             # as card dict.
        #     'poll': # A poll dict if a poll is attached to this status.
        # }

        statuses = self.mastodon.account_statuses(
            self.user.id,
            only_media=False,
            pinned=False,
            exclude_replies=True,
            exclude_reblogs=True,
            tagged=None,
            max_id=None,
            min_id=None,
            since_id=None,
            limit=limit,
        )
        return statuses

    def _load_config(self):
        data = yaml.safe_load(self.config_file.open("r"))
        if data is None:
            data = {}

        for (k, v) in data.items():
            if isinstance(v, dict):
                v = AttribAccessDict(v)
                data[k] = v

        self.config = AttribAccessDict(data)

    def _save_config(self):
        output: str = yaml.safe_dump(
            self.data,
            default_flow_style=False,
            indent=2,
            allow_unicode=True,
            # encoding="utf-8",
        )
        self.config_file.open("w").write(output)

    def post_toot(self, message: Message):
        """Create a new status/toot.

        Message, not shown here, is just a dataclass holding the various attributes of the
        posted content.  You could use a dict or whatever instead.
        """
        status_dict = self.mastodon.status_post(
            message.text,
            in_reply_to_id=message.in_reply_to_id,
            # sensitive=False,
            visibility=message.visibility,
            # spoiler_text=None,
            language="en",
            # scheduled_at=None,    # datetime
        )

        return status_dict
