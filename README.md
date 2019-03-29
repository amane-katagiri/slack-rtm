# Slack RTM

Slack RTM (reaction to mail) checks Slack reaction event and forward message as mail. **This application is compatible with messages sent by [Slack RSS App](https://slack.com/apps/A0F81R7U7-rss).**

## Usage

You ...

1. Add reaction (default: `:eyes:`) to a message you want to read later.

Slack RTM ...

1. Forward the message to you.
1. Add reaction (default: `:email:`(success) or `:x:`(failure)) to the message.

## Installation

### Get your app

1. Open [https://api.slack.com/apps](https://api.slack.com/apps).
1. Press "Create New App".
1. Fill form and Press "Create App".

### Configure your app

There are required permissions of your app.

#### Basic Information -> Event Subscriptions

* `channel_created`
* `channel_rename`
* `reaction_added`

#### OAuth & Permissions -> Scopes

* `channels:history`
* `channels:read`
* `reactions:read`
* `reactions:write`

### Configure Slack RTM

1. Copy [:/slack_rtm/conf/example-slack_rtm.conf](https://github.com/amane-katagiri/slack-rtm/blob/master/slack_rtm/conf/example-slack_rtm.conf) to `./conf/slack_rtm.conf`.
1. Copy [:/slack_rtm/conf/example-mail.txt](https://github.com/amane-katagiri/slack-rtm/blob/master/slack_rtm/conf/example-mail.txt) to `./conf/mail.txt`.

Tips: Leading `:/` will be replaced with cwd(`/path/to/slack-rtm/slack_rtm`) in `mail_command`(default: `:/bin/send_feed`) and `mail_body_file`(default: `./conf/mail.txt`)

#### Credentials

* `slack_app_id`: Basic Information -> App ID
* `slack_verify_token`: Basic Information -> Verification Token
* `slack_access_token`: OAuth & Permissions -> OAuth Access Token

#### Mail options

* `mail_command`: Path to executable to send mail.
    * args: `mail_subject`(formatted), `mail_from`, `mail_to` and `mail_command_options`(extracted).
    *  mail body is read from standard input.
* `mail_from`
* `mail_to`
* `mail_command_options`: list of `mail_command` options. [:/bin/send_feed](https://github.com/amane-katagiri/slack-rtm/blob/master/slack_rtm/bin/send_feed) uses [Heirloom mailx](http://heirloom.sourceforge.net/mailx.html) (example: `["-S", "smtp=smtp://smtp.example.com:25"]`).
* `mail_subject`: Use Python string formatting style with `title` and `sitename`.
* `mail_body_file`: Path to text file in Python string formatting style with `url` and `description` (sample: `slack_rtm/conf/example-mail.txt`).

#### Subscribing Slack event options

* `target_channel_names`: If source channel of reaction event is in these, check reaction with `target_reactions`.
* `target_reactions`: If reaction name is in these, send mail to `mail_to`.
* `success_reaction`: If `mail_command` succeed, add this reaction to the message.
* `failure_reaction`: If `mail_command` failed, add this reaction to the message.
* `api_endpoint`: Events API request URL.

### Configure request URL of your app

#### Basic Information -> Event Subscriptions

* Fill "Request URL" with "https://your.domain.example.com `api_endpoint`" and test it.

## Use with Docker

wip
