# Mastodon Status ("Toot") higher-level API

The code here is an extract from a Mastodon client I wrote to scratch a
personal itch.  I don't think I'm going to have time to properly clean it
up, test and document it, etc to the level that a full open-source release
would require to make it useable by others, so this is just the snippet
that actually talks to the Mastodon API to log in, retrieve statuses, and
create ("post") new statuses.

This has been lightly cleaned up and scrubbed from the form I'm actually using
it in my custom client, so it may contain bugs from not being tested - but
hopefully only obvious ones.

## Copyright and license

This code is copyright © 2023 Charles Cazabon <charlesc-github-projects AT pyropus.ca>.

Licensed under the GNU General Public License version 2 (only).
See the file LICENSE for details.

## Requirements

There are two direct PyPI package dependencies:

- the official Mastodon Python library (I'm using v1.8.0)
- PyYAML, which is used for storing configuration data (I'm using 6.0)

Install them with poetry, pipenv, pip, or what have you.  Use a Python
virtual environment for sanity.

## Config file

There's pieces in the code that would start from a clean slate and create a
configuration file, register an application with the Mastodon instance, log
in, and save the tokens and whatnot needed to use that the next session,
but I had such problems with authentication that I didn't end up using that.

This code requires a minimal config in YAML format which you can create by
hand.  Register/create your client application through the Mastodon web UI,
and put its info into a file.  The code by default will look for it in
`~/.config/APPLICATION_NAME/config.yaml`, but you can pass a different
config directory to the constructor.

```yaml
application:
  client_id: "application-id-from-the-Mastodon-UI"
instance:
  base_url: "https://my-mastodon-instance/"
  client_key: "aaaaaaaaaaaaa-bbbbbbbbb-cc-dddddddddddddddd"
  client_secret: "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopq"
user:
  access_token: "..."
```

`access_token` isn't used with the simple login/connect flow.
`client_key` and `client_secret` are given to you when you create/register
your application in the web UI.

## Usage

Example code using this package to post a status ("toot"):

```python
instance = MastodonClientApp(...)
result = instance.post_toot(message)
```

