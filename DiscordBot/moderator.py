from enum import auto, Enum


class State(Enum):
    REPORT_START = auto()
    WAITING_REASON = auto()
    WAITING_USER = auto()
    WAITING_DANGER = auto()
    # GOT_USER_ID = auto()
    WAITING_DOXING_TYPE = auto()
    GOT_DOXING_TYPE = auto()
    WAITING_MOD_DELETE = auto()
    WAITING_FRAUD_TYPE = auto()
    REPORT_COMPLETE = auto()

class DoxingType(Enum):
    DEANONYMIZATION = auto()
    TARGETING = auto()
    DELEGIITIMIZATION = auto()



class Moderator:
    HANDLE_KEYWORD = "handle"
    def __init__(self): 
        self.state = State.REPORT_START
        self.doxing_type = None

    # Special handler designed to handle reports from the bot classifer. Note that the
    # classifer does not generate a 'report' object, so it requires a different system.
    async def handle_bot_report(self, reported_message, message, reported_user, channel):
        print('message', message.content)
        print('state', self.state)
        
        # Start of the bot reporting process: Look at the message and determine if it's doxing or not
        if self.state == State.REPORT_START:
            self.state = State.WAITING_REASON
            return ['is the user in question being doxed? (yes, no)']

        if self.state == State.WAITING_REASON:
            response = message.content.lower()
            if response == 'yes':
                self.state = State.WAITING_DANGER
                return ['Is the user in some sort of physical danger?']
            elif response == 'no':
                self.state = State.REPORT_COMPLETE
                return ['No doxing here, move on']

        # Check to see if the message puts someone in danger, since the classifier does not look for this
        if self.state == State.WAITING_DANGER:
            response = message.content.lower()
            if response == 'yes':
                self.state = State.REPORT_COMPLETE
                return ['The user has imminent danger so we will report to other moderator teams to verify the claim and report to authorities!']
            else:
                self.state = State.WAITING_DOXING_TYPE
                return ["What type of doxing is this? (deanonymization doxing, targeting doxing, delegitimization doxing)"]

        # Look at the three types of doxing to determine the best course of action
        # NOTE: do not need to look for fraudulent reports, as the moderator verifies that at the beginning.
        if self.state == State.WAITING_DOXING_TYPE:

            doxing_type = message.content.lower()
            if doxing_type == 'deanonymization doxing':
                self.doxing_type = DoxingType.DEANONYMIZATION
                self.state = State.REPORT_COMPLETE

                # Delete message, ban the user
                await reported_message.delete()
                await reported_user.send("You have been banned from the channel for doxing!")
                await channel.send(reported_user.name + " has been banned from the channel")
                return ["The message has been removed and the user has been banned."]

            elif doxing_type == 'targeting doxing':
                self.doxing_type = DoxingType.TARGETING
                self.state = State.REPORT_COMPLETE

                # Delete the message, ban the user
                await reported_message.delete()
                await reported_user.send("You have been banned from the channel for doxing!")
                await channel.send(reported_user.name + " has been banned from the channel")
                return ["The message has been removed and the user has been banned."]

            elif doxing_type == 'delegitimization doxing':
                self.doxing_type = DoxingType.DELEGIITIMIZATION
                self.state = State.REPORT_COMPLETE

                # Delete the message, warn the user
                await reported_message.delete()
                await reported_user.send("Warning! You have been reported by other users for doxing! You will be removed if you do it again")
                return ["The message has been removed and the user has been warned."]

    
    async def handle_report(self, report, message, user, reported_user, channel):

        print('message', message.content)
        print('state', self.state)
        
        # Send the Initial message to begin the reporting process.
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the report handling process. "
            reply += "handle report about this message: \n"
            reply += "```" + report.reported_userName + ": " + report.report_message.content + "```"
            reply += "This message is reported by " +  report.userName + '\n'
            # reply += "Say `help` at any time for more information.\n\n"
            reply += "User has reported this message as " + report.reason_type +'. '
            reply += "What is the reason for the report? (spam, harassment, doxing)"
            self.state = State.WAITING_REASON
            return [reply]
        
        # Determine whether the report is for doxing, spam, or harassment.
        if self.state == State.WAITING_REASON:
            reason = message.content.lower()
            if self.state == State.WAITING_REASON:
                self.state = State.WAITING_USER
            if reason == 'spam':
                self.func = self.handle_spam_report
            elif reason == 'harassment':
                self.func = self.handle_harassment_report
            elif 'doxing' in reason:
                self.func = self.handle_doxing_report
            else:
                self.state = State.REPORT_START
                return ["Invalid reason for the report."]

        # If the user has reported imminent danger on their behalf, escalate the report to a different team
        if self.state == State.WAITING_USER :
            if report.imminent_danger:
                return ['The user has imminent danger so we will report to other moderator teams to verify the claim and report to authorities!']
            else:
                return await self.func(report.report_message, report, user, reported_user, channel)
                
        if self.state == State.WAITING_DOXING_TYPE or self.state == State.WAITING_FRAUD_TYPE or self.state==State.GOT_DOXING_TYPE:
            return await self.func(message,report, user, reported_user, channel)


    async def handle_spam_report(self, message,report, user, reported_user, channel):
        # Handle the spam report (e.g., warn the user, delete messages, etc.)
        # You can customize the actions based on your moderation policies
        # # Example actions:
        # await client.send_message(user_id, "You have been reported for spamming. Please refrain from such behavior.")
        # await client.delete_messages(user_id, additional_info)
        self.state = State.REPORT_COMPLETE
        # TODO: Handle spam report
        print("Spam report complete.")
        return ["Spam report complete."]

    async def handle_harassment_report(self, message, report,  user, reportd_user, channel):
        # Handle the harassment report (e.g., warn the user, mute the user, etc.)
        # You can customize the actions based on your moderation policies
        # Example actions:
        # await client.send_message(user_id, "You have been reported for harassment. This behavior is not tolerated.")
        # await client.mute_user(user_id, additional_info)
        self.state = State.REPORT_COMPLETE
        # TODO: Handle harassment report
        print("Harassment report complete.")
        return ["Harassment report complete."]


    async def handle_doxing_report(self, message, report, user, reported_user, channel):
        # Handle the doxing report (e.g., warn the user, delete doxing messages, etc.)
        # You can customize the actions based on your moderation policies
        # Example actions:
        # await client.send_message(user_id, "You have been reported for doxing. Sharing personal information without consent is not allowed.")
        
        # Ask the moderator to determine what type of doxing is happening
        if self.doxing_type == None and self.state == State.WAITING_USER:
            self.state = State.WAITING_DOXING_TYPE
            return ["What type of doxing is this? (deanonymization doxing, targeting doxing, delegitimization doxing)"]

        # Doxing type received
        if self.state == State.WAITING_DOXING_TYPE:
            doxing_type = message.content.lower()
            if doxing_type == 'deanonymization doxing':
                self.doxing_type = DoxingType.DEANONYMIZATION
                self.state = State.WAITING_FRAUD_TYPE
                return ["Is this claim fraudulent? (yes, no)"]

            elif doxing_type == 'targeting doxing':
                self.doxing_type = DoxingType.TARGETING
                print('targeting doxing is reported')
                self.state = State.WAITING_FRAUD_TYPE
                return ["Is this claim fraudulent? (yes, no)"]

            elif doxing_type == 'delegitimization doxing':
                self.doxing_type = DoxingType.DELEGIITIMIZATION
                # TODO: Handle doxing report for this type
                await report.report_message.delete()
                # user = client.get_user(int(report.reported_userID))
                await user.send('Warning! You have been reported by other users for doxing! You will be removed if you do it again')
                self.state = State.REPORT_COMPLETE
                return ["The message has been removed and the user has been warned."]

        # Verify if the doxing claim is legitimate
        if self.state == State.WAITING_FRAUD_TYPE:
            fraud_type = message.content.lower()
            if fraud_type == 'yes':
                self.state = State.REPORT_COMPLETE
                await user.send("Warning! You have sent frivlous claims!")
                return ["The user has been warned."]

            elif fraud_type == 'no':
                self.state = State.REPORT_COMPLETE
                
                # handle the case by banning the user and removing the message
                await report.report_message.delete()
                await user.send("Your reported message has been removed and the user is banned!")
                await reported_user.send('You have been banned from the channel')
                await channel.send(report.report_message.author.name + " have been banned from the channel")
                return ["Action has been taken against the offender."]
            else:
                self.state = State.GOT_DOXING_TYPE
                return ["Invalid fraud type."]
        
    async def reset(self):
        self.state = State.REPORT_START
        self.doxing_type = None

    async def report_complete(self):
        return self.state == State.REPORT_COMPLETE