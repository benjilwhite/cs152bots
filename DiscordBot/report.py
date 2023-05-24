from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Reason(Enum):
    SPAM = auto()
    HARASSMENT = auto()
    DOXING = auto()
    REPORT_OTHER = auto()
    OTHER = auto()
    UNKNOWN = auto()

class DoxingSubReason(Enum):
    SENSITIVE_INFO = auto()
    THREATENING_LEAK = auto()
    EXPOSING_INFO = auto()
    UNKNOWN = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reason = Reason.UNKNOWN
        self.doxing_subreason = DoxingSubReason.UNKNOWN
        self.imminent_danger = None

    async def handle_message(self, message):
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            self.state = State.MESSAGE_IDENTIFIED
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "What is your reason for reporting? You can say `spam`, `harassment`, `doxing`, `reporting on behalf of someone else`, or `other`."]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if self.reason == Reason.UNKNOWN:
                return ["Please specify the reason for your report."]
            elif self.reason == Reason.SPAM or self.reason == Reason.HARASSMENT or self.reason == Reason.REPORT_OTHER or self.reason == Reason.OTHER:
                self.state = State.REPORT_COMPLETE
                return ["Thank you for the report. Our moderation team will take appropriate action. Would you like to block the user? You can say `yes` or `no`."]
            elif self.reason == Reason.DOXING:
                if self.doxing_subreason == DoxingSubReason.UNKNOWN:
                    return ["Please specify. You can say `sensitive information about me`, `threatening to leak my information`, or `exposing my information`."]
                elif self.doxing_subreason != DoxingSubReason.UNKNOWN:
                    if self.imminent_danger == None:
                        return ["Does the information present an imminent physical danger to you? You can say `yes` or `no`."]
                    else:
                        self.state = State.REPORT_COMPLETE
                        if self.imminent_danger:
                            return ["Your report has been received. Our moderation team will investigate the situation and resolve the situation as soon as possible. In the meantime, would you like to block the user? You can say `yes` or `no`."]
                        else:
                            return ["Thank you for the report. Our moderation team will take appropriate action. Would you like to block the user? You can say `yes` or `no`."]

        if self.state == State.MESSAGE_IDENTIFIED and self.reason == Reason.UNKNOWN:
            if message.content.lower() == "spam":
                self.reason = Reason.SPAM
            elif message.content.lower() == "harassment":
                self.reason = Reason.HARASSMENT
            elif message.content.lower() == "doxing":
                self.reason = Reason.DOXING
            elif message.content.lower() == "reporting on behalf of someone else":
                self.reason = Reason.REPORT_OTHER
            elif message.content.lower() == "other":
                self.reason = Reason.OTHER

        if self.state == State.MESSAGE_IDENTIFIED and self.reason == Reason.DOXING and self.doxing_subreason == DoxingSubReason.UNKNOWN:
            if message.content.lower() == "sensitive information about me":
                self.doxing_subreason = DoxingSubReason.SENSITIVE_INFO
                return ["We will remind the user of our doxing policy. Your report has been received. Our moderation team will take appropriate action. Would you like to block the user? You can say `yes` or `no`."]
            elif message.content.lower() == "threatening to leak my information":
                self.doxing_subreason = DoxingSubReason.THREATENING_LEAK
            elif message.content.lower() == "exposing my information":
                self.doxing_subreason = DoxingSubReason.EXPOSING_INFO

        if self.state == State.MESSAGE_IDENTIFIED and self.reason == Reason.DOXING and self.doxing_subreason != DoxingSubReason.UNKNOWN and self.imminent_danger == None:
            if message.content.lower() == "yes":
                self.imminent_danger = True
            elif message.content.lower() == "no":
                self.imminent_danger = False

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
