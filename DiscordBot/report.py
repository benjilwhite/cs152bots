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
        self.askToBlock = False
        self.isBlocked = None
        self.userID = None
        self.reported_userID =None
        self.userName = None
        self.reported_userName = None
        self.report_message = None
        self.handle_required = False
        self.mod_channel = None
        self.reason_type = None

    async def handle_message(self, message, mod_channel):
        self.mod_channel = mod_channel
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            self.userID = message.author.id
            self.userName = message.author.name
            # print('user name', message.author.name)
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            print('message',m)
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
                self.report_message = message
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            self.state = State.MESSAGE_IDENTIFIED
            self.reported_userID = message.author.id
            self.reported_userName = message.author.name
            # print('reported user', message.author.name)
            self.message = message.content
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "What is your reason for reporting? You can say `spam`, `harassment`, `doxing`, `reporting on behalf of someone else`, or `other`."]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if self.reason == Reason.UNKNOWN:
                if message.content.lower() == "spam":
                    self.reason = Reason.SPAM
                    self.reason_type = "spam"
                elif message.content.lower() == "harassment":
                    self.reason = Reason.HARASSMENT
                    self.reason_type = "harassment"
                elif message.content.lower() == "doxing":
                    self.reason = Reason.DOXING
                    self.reason_type ="doxing"
                elif message.content.lower() == "reporting on behalf of someone else":
                    self.reason = Reason.REPORT_OTHER
                    self.reason_type = "reporting other"
                    
                elif message.content.lower() == "other":
                    self.reason = Reason.OTHER
                    self.reason_type = "other"
                else:
                    return ["Please specify the reason for your report."]

            if self.reason == Reason.SPAM or self.reason == Reason.HARASSMENT or self.reason == Reason.REPORT_OTHER or self.reason == Reason.OTHER:
                self.state = State.REPORT_COMPLETE
                self.askToBlock = True
                self.handle_required = True
                return ["Thank you for the report. Our moderation team will take appropriate action. Would you like to block the user? You can say `yes` or `no`."]
            elif self.state == State.MESSAGE_IDENTIFIED and self.reason == Reason.DOXING and self.doxing_subreason == DoxingSubReason.UNKNOWN:
                if message.content.lower() == "sensitive information about me":
                    self.doxing_subreason = DoxingSubReason.SENSITIVE_INFO
                elif message.content.lower() == "threatening to leak my information":
                    self.doxing_subreason = DoxingSubReason.THREATENING_LEAK
                elif message.content.lower() == "exposing my information":
                    self.doxing_subreason = DoxingSubReason.EXPOSING_INFO

                if self.doxing_subreason == DoxingSubReason.UNKNOWN:
                    return ["Please specify. You can say `sensitive information about me`, `threatening to leak my information`, or `exposing my information`."]
                elif self.doxing_subreason != DoxingSubReason.UNKNOWN:
                    if self.imminent_danger == None:
                        return ["Does the information present an imminent physical danger to you? You can say `yes` or `no`."]
                    else:
                        mod_response = "handle report about this message: \n"
                        mod_response += "```" + self.reported_userName + ": " + self.message + "```",
                        mod_response += "This message is reported by " +  self.userName
                        await mod_channel.send(mod_response)
                        print('mod channel', mod_channel)
                        self.askToBlock = True
                        if self.imminent_danger: 
                            self.state = State.REPORT_COMPLETE
                            self.handle_required = True
                            return ["Your report has been received. Our moderation team will investigate the situation and resolve the situation as soon as possible. In the meantime, would you like to block the user? You can say `yes` or `no`."]
                        else: 
                            self.handle_required = True
                            return ["Thank you for the report. Our moderation team will take appropriate action. Would you like to block the user? You can say `yes` or `no` to block the user."]

        if self.state == State.MESSAGE_IDENTIFIED and self.reason == Reason.DOXING and self.doxing_subreason != DoxingSubReason.UNKNOWN and self.imminent_danger == None:
            if message.content.lower() == "yes":
                self.imminent_danger = True
            elif message.content.lower() == "no":
                self.imminent_danger = False
            self.askToBlock = True
            self.handle_required = True
            return ["We will remind the user of our doxing policy. Your report has been received. Our moderation team will take appropriate action. Would you like to block the user? You can say `yes` or `no`."]
        
        if self.askToBlock == True:
            if message.content.lower() == "yes":
                self.isBlocked = True
                self.askToBlock = False
                self.state = State.REPORT_COMPLETE
                return["User blocked. Thank you for your report."]
            elif message.content.lower() == "no":
                self.isBlocked = False
                self.askToBlock = False
                
                self.state = State.REPORT_COMPLETE
                return["User not blocked. Thank you for your report."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
    async def need_handle(self):
        # print('mod channel', mod_channel)
        # print('message', self.report_message.content)
        # print('user', self.reported_userName)
        # mod_response = "handle report about this message: \n"
        # mod_response += "```" + self.reported_userName + ": " + self.report_message.content + "```"
        # mod_response += "This message is reported by " +  self.userName
        # await self.mod_channel.send(mod_response)
        return self.handle_required 