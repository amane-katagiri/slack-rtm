#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import pathlib
from typing import Union

from tornado import httpclient
from tornado import httpserver
from tornado import httputil
from tornado import ioloop
from tornado import web
from tornado.options import define
from tornado.options import options


define("conf", default="./conf/slack_rtm.conf")
define("slack_app_id", default="xxx", type=str)
define("slack_verify_token", default="xxxxxx", type=str)
define("slack_access_token", default="xxxx-xxx-xxx-xxx-xxxxxx", type=str)
define("target_channel_names", default=["random"], type=list)
define("target_channel_ids", default=[], type=list)
define("target_reactions", default=["eyes"], type=list)
define("success_reaction", default="email", type=str)
define("failure_reaction", default="x", type=str)
define("mail_command", default=":/bin/send_feed", type=str)
define("mail_command_options", default=[], type=list)
define("mail_subject", default="{title} - {sitename}", type=str)
define("mail_body_file", default="./conf/mail.txt", type=str)
define("mail_body", default="{url}\n\n{description}", type=str)
define("mail_from", default="sender@example.com", type=str)
define("mail_to", default="recipient@example.com", type=str)
define("api_endpoint", default="/slack_api/", type=str)
define("port", default=8000, type=int)

EXAMPLE_CONF = pathlib.Path(__file__).resolve().parent / "conf" / "example-slack_rtm.conf"
EXAMPLE_MAIL_BODY_FILE = pathlib.Path(__file__).resolve().parent / "conf" / "example-mail.txt"


def _load_json(data: Union[str, bytes]) -> dict:
    try:
        return json.loads(data if type(data) is str else str(data, encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logging.warning("bad json data({}): {}".format(e, data))
        raise web.HTTPError(400)
    except TypeError:
        logging.error("bad json data(TypeError): {}".format(data))
        raise web.HTTPError(500)


async def _fetch_message(channel: str, ts: str) -> dict:
    http_client = httpclient.AsyncHTTPClient()
    try:
        response = await http_client.fetch(
            httputil.url_concat(
                "https://slack.com/api/channels.history",
                {"token": options.slack_access_token,
                 "channel": channel,
                 "latest": ts,
                 "inclusive": "true",
                 "count": 1})
        )
    except Exception as ex:
        logging.error("{}: channel='{}', ts='{}'".format(ex, channel, ts))
        raise web.HTTPError(500)
    messages = _load_json(response.body).get("messages", [])
    if len(messages) != 1:
        _buf = "no message found on '{}': channel='{}', ts='{}'"
        logging.error(_buf.format(messages, channel, ts))
        raise web.HTTPError(500)
    return messages[0]


async def _send_mail(subject: str, body: str, sender: str, recipient: str) -> int:
    mail = await asyncio.create_subprocess_exec(
        options.mail_command, subject, sender, recipient, *options.mail_command_options,
        stdin=asyncio.subprocess.PIPE
    )
    await mail.communicate(bytes(body, encoding="utf-8"))
    return mail.returncode


async def _add_reaction(emoji: str, channel: str, ts: str) -> httpclient.HTTPResponse:
    http_client = httpclient.AsyncHTTPClient()
    try:
        response = await http_client.fetch(
            "https://slack.com/api/reactions.add",
            method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer {}".format(options.slack_access_token)},
            body=json.dumps({"name": emoji,
                             "channel": channel,
                             "timestamp": ts})
        )
    except Exception as ex:
        logging.error("{}: emoji='{}', channel='{}', ts='{}'".format(ex, emoji, channel, ts))
        raise web.HTTPError(500)
    return response


async def _update_channel_ids() -> None:
    http_client = httpclient.AsyncHTTPClient()
    channels = dict()
    try:
        cursor = None
        while cursor is None or cursor:
            response = await http_client.fetch(
                httputil.url_concat(
                    "https://slack.com/api/channels.list",
                    {"token": options.slack_access_token}
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            body = _load_json(response.body)
            channels.update({x.get("id"): x.get("name") for x in body.get("channels", [])
                             if x.get("name") in options.target_channel_names})
            cursor = body.get("response_metadata", {}).get("next_cursor", "")
    except Exception as ex:
        logging.fatal("{}: failed to fetch channel list".format(ex))
    options.target_channel_ids = list(channels.keys())
    logging.info("updated channel list: {}".format(channels))


class SlackHandler(web.RequestHandler):
    def _validate_request(self) -> None:
        body = _load_json(self.request.body)
        if (body.get("token") != options.slack_verify_token or
                body.get("api_app_id") != options.slack_app_id):
            logging.warning("bad auth: token='{}', app_id='{}'".format(body.get("token"),
                                                                       body.get("api_app_id")))
            raise web.HTTPError(401)

    async def post(self) -> None:
        self._validate_request()

        body = _load_json(self.request.body)
        if body.get("type") == "url_verification":
            self.write(body.get("challenge", ""))
            return
        event_type = body.get("event", {}).get("type")
        if event_type == "reaction_added":
            event_emoji = body.get("event").get("reaction")
            if event_emoji in options.target_reactions:
                item = body.get("event").get("item", {})
                channel, ts = item.get("channel"), item.get("ts")
                if not(item and channel and ts):
                    _buf = "Insufficient parameters: item='{}', channel='{}', ts='{}'"
                    logging.info(_buf.format(item, channel, ts))
                    raise web.HTTPError(400)
                if channel in options.target_channel_ids:
                    msg = await _fetch_message(channel, ts)
                    urls = msg.get("attachments", [])
                    if urls:
                        title = urls[0].get("title", "untitled")
                        url = urls[0].get("title_link", "https://example.com/")
                        text = urls[0].get("text", "description")
                    else:
                        _buf = msg.get("text", "").split("\n")
                        _header, text = _buf[0], "\n".join(_buf[1:])
                        title = "".join(_header.strip("<>").split("|")[1:]) or "untitled"
                        url = _header.strip("<>").split("|")[0] or "https://example.com/"
                    sitename = msg.get("username", "untitled")
                    subject = options.mail_subject.format(title=title, sitename=sitename)
                    body = options.mail_body.format(url=url, description=text)
                    returncode = await _send_mail(subject, body,
                                                  options.mail_from, options.mail_to)
                    if returncode == 0:
                        emoji = options.success_reaction
                        _buf = "sucseeded in sending mail: emoji='{}', channel='{}', ts='{}'"
                        logging.info(_buf.format(emoji, channel, ts))
                    else:
                        emoji = options.failure_reaction
                        _buf = "failed to send mail: emoji='{}', channel='{}', ts='{}'"
                        logging.error(_buf.format(emoji, channel, ts))
                    await _add_reaction(emoji, channel, ts)
                else:
                    _buf = "recieved reaction event: emoji='{}', channel='{}', ts='{}'"
                    logging.debug(_buf.format(event_emoji, channel, ts))
            else:
                logging.debug("recieved reaction event: emoji='{}'".format(event_emoji))
        elif event_type in ["channel_created", "channel_rename"]:
            await _update_channel_ids()
        else:
            logging.debug("recieved event: event_type='{}'".format(event_type))


def _update_collon_with_cwd():
    cwd = pathlib.Path(__file__).resolve().parent
    if options.conf[:2] == ":/":
        options.conf = str(cwd / options.conf[2:])
    if options.mail_command[:2] == ":/":
        options.mail_command = str(cwd / options.mail_command[2:])
    if options.mail_body_file[:2] == ":/":
        options.mail_body_file = str(cwd / options.mail_body_file[2:])


def _load_conf():
    options.parse_command_line()
    _update_collon_with_cwd()

    if pathlib.Path(options.conf).is_file():
        options.parse_config_file(options.conf)
        logging.info("load conf from '{}'.".format(options.conf))
    elif EXAMPLE_CONF.is_file():
        options.parse_config_file(EXAMPLE_CONF)
        logging.warning("load example conf from '{}'.".format(EXAMPLE_CONF))
    else:
        logging.error("example conf '{}' is not found.".format(EXAMPLE_CONF))
    _update_collon_with_cwd()

    options.parse_command_line()
    _update_collon_with_cwd()

    if pathlib.Path(options.mail_body_file).is_file():
        with open(options.mail_body_file) as f:
            options.mail_body = f.read()
            logging.info("load mail body from '{}'.".format(options.mail_body_file))
    elif pathlib.Path(EXAMPLE_MAIL_BODY_FILE).is_file():
        with open(EXAMPLE_MAIL_BODY_FILE) as f:
            options.mail_body = f.read()
            logging.warning("load example mail body from '{}'.".format(EXAMPLE_MAIL_BODY_FILE))
    else:
        logging.error("example mail body file '{}' is not found.".format(EXAMPLE_MAIL_BODY_FILE))


def main():
    _load_conf()

    app = web.Application([
        (options.api_endpoint, SlackHandler, ),
    ], )
    server = httpserver.HTTPServer(app)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_update_channel_ids())

    server.listen(options.port)
    ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
