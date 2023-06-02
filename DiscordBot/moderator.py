from enum import auto, Enum


class State(Enum):
    REPORT_START = auto()
    WAITING_REASON = auto()
    WAITING_USER = auto()
    # GOT_USER_ID = auto()
    WAITING_DOXING_TYPE = auto()
    GOT_DOXING_TYPE = auto()
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
    
    async def handle_report(self, report, message, user, reported_user, channel):
        # if message.content.startswith('!report'):
            # Extract the relevant information from the message
        # report_info = message.content.split(' ')[1:]
        # user_id = report_info[0]  # User ID being reported
        # reason = report_info[1]  # Reason for the report
        # additional_info = ' '.join(report_info[2:])  # Additional information provided

        # # Handle the report based on the reason
        # if reason == 'spam':
        #     await self.handle_spam_report(user_id, additional_info, client)
        # elif reason == 'harassment':
        #     await self.handle_harassment_report(user_id, additional_info, client)
        # elif reason == 'doxing':
        #     await self.handle_doxing_report(user_id, additional_info, client)
        # else:
        #     await message.channel.send("Invalid reason for the report.")
        # if message.content.lower().startswith('cancel'):
        #     self.state = State.REPORT_START
        #     self.func = None
        #     return ["Report cancelled."]
        # if message.content.lower().startswith('help'):
        #     return ["This is the help message."]
        print('message', message.content)
        print('state', self.state)
        
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
            # return ["Please provide the user ID of the user being reported."]
        if self.state == State.WAITING_USER :
            if report.imminent_danger:
                return ['The user has imminent danger so we will report to other moderator teams to verify the claim and report to authorities!']
            else:
                return await self.func(report.report_message, report, user, reported_user, channel)
        if self.state == State.WAITING_DOXING_TYPE or self.state == State.WAITING_FRAUD_TYPE or self.state==State.GOT_DOXING_TYPE:
            return await self.func(message,report, user, reported_user, channel)
        
        # if self.state == State.WAITING_USER_ID:
        #     user_id = message.content
        #     self.state = State.GOT_USER_ID
        #     return await self.func(user_id, client, message)

        # if self.state.value >= State.GOT_USER_ID.value:
        #     return await self.func(message, client, message)



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
        
        # Delete doxing messages from the user
        # await self.delete_doxing_messages(user_id, additional_info)
        # if self.doxing_type == None and self.state == State.GOT_USER_ID:
        if self.doxing_type == None and self.state == State.WAITING_USER:
            self.state = State.WAITING_DOXING_TYPE
            return ["What type of doxing is this? (deanonymization doxing, targeting doxing, delegitimization doxing)"]
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
            # else:
            #     # self.state = State.GOT_USER_ID
            #     self.doxing_type = None
            #     return await self.handle_doxing_report(message, user, reported_user)
            # self.state = State.GOT_DOXING_TYPE
            # self.state = State.WAITING_FRAUD_TYPE
            # return ["Is this claim fraudulent? (yes, no)"]
            # return ["Doxing Type Received!"]
        
        # if self.state == State.GOT_DOXING_TYPE:
        #     self.state = State.WAITING_FRAUD_TYPE
        #     return ["Is this claim fraudulent? (yes, no)"]
        if self.state == State.WAITING_FRAUD_TYPE:
            fraud_type = message.content.lower()
            if fraud_type == 'yes':
                self.state = State.REPORT_COMPLETE
                # TODO: Handle this
                # user = client.get_user(int(report.userID))
                await user.send("Warning! You have sent frivlous claims!")
                return ["The user has been warned."]
            elif fraud_type == 'no':
                self.state = State.REPORT_COMPLETE
                # TODO: Handle this
                await report.report_message.delete()
                # reported_user = client.get_user(int(report.reported_userID))
                await user.send("Your reported message has been removed and the user is banned!")

                await reported_user.send('You have been banned from the channel')
                await channel.send(report.report_message.author.name + " have been banned from the channel")
                # user = client.get_user(int(report.userID))
               
                return ["Action has been taken against the offender."]
            else:
                self.state = State.GOT_DOXING_TYPE
                return ["Invalid fraud type."]
        
    async def reset(self):
        self.state = State.REPORT_START
        self.doxing_type = None

    # async def delete_doxing_messages(self, user_id, additional_info, client):
    #     # Fetch the channel where the doxing messages were reported
    #     channel = client.get_channel(additional_info)

    #     if channel:
    #         async for message in channel.history(limit=None):
    #             if message.author.id == user_id:
    #                 # Delete the doxing message
    #                 await message.delete()

    async def report_complete(self):
        return self.state == State.REPORT_COMPLETE