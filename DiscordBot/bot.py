# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from moderator import Moderator
import pdb
import openai
import boto3

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']

    # Setup OpenAI keys
    openai.organization = tokens['openai-org']
    openai.api_key = tokens['openai-api-key']
    


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.moderator = Moderator()
        self.reports = {} # Map from user IDs to the state of their report
        self.last_report = None
        self.bot_report_message = None
        self.channel = None

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')
        
        

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name ==f'group-{self.group_num}':
                    # print('guild id', guild.id)
                    self.channel = channel
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
             await self.handle_dm(message)
        #await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        mod_channel= self.mod_channels[self.guilds[0].id]
        if not message.guild:
            if message.content == Report.HELP_KEYWORD:
                reply =  "Use the `report` command to begin the reporting process.\n"
                reply += "Use the `cancel` command to cancel the report process.\n"
                await message.channel.send(reply)
                return

            author_id = message.author.id
            responses = []

            # Only respond to messages if they're part of a reporting flow
            if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
                return

            # If we don't currently have an active report for this user, add one
            if author_id not in self.reports:
                self.reports[author_id] = Report(self)

            # Let the report class handle this message; forward all the messages it returns to uss
            responses = await self.reports[author_id].handle_message(message, mod_channel)
            for r in responses:
                await message.channel.send(r)
            if self.reports[author_id].report_complete():
                self.last_report = self.reports[author_id]
                self.last_author_id = author_id

        # If the report is complete or cancelled, remove it from our map
        if self.last_report:
            print('report flow is complete')
            # if author_id is not None:
            #     self.last_report = self.reports[author_id]
            # print(message.content[:6])
            # if message.channel.id == mod_channel.id and message.content[:6] == Moderator.HANDLE_KEYWORD:
            if self.last_report.need_handle():
                print('handling the report')
                reported_user =await self.fetch_user(int(self.last_report.report_message.author.id))
                print('rpoert id', self.last_report.reported_userID)
                print('user id', self.last_report.userID)
                print('reported user', reported_user)
                user = await self.fetch_user(int(self.last_report.userID))
                res = await self.moderator.handle_report(report = self.last_report, message = message, user = user, reported_user = reported_user, channel= self.channel)
                if res is not None:
                    for r in res:
                        # await message.channel.send(r)
                        # mod_response = "Doxing is not detected or reported, please call the other moderator team to take care!"
                        await mod_channel.send(r)
                if await self.moderator.report_complete():
                    # self.handle = False
                    
                    await self.moderator.reset()
                    self.last_report = None
                    self.reports.pop(self.last_author_id)
                    self.last_author_id = None
                # self.reports.pop(author_id)

    # Handles automated classification
    async def handle_channel_message(self, message):

        mod_channel = self.mod_channels[message.guild.id]

        # Only handle messages sent in the "group-#" channel
        if message.channel.name == f'group-{self.group_num}':

            # Evaluate using GPT and Amazon Comprehend
            gpt_model = "gpt-3.5-turbo"
            dox = self.eval_dox(message.content, gpt_model)
            pii_response = self.eval_pii(message.content)

            # At least one of the classifiers needs to be triggered to send a bot report
            if dox == "Threatening" or len(pii_response) > 0:

                # Forward the message to the mod channel
                response_message = "**Automatically evaluated the following message:**\n```" + str(message.author.name) + ": \"" + str(message.content) + "\"```"

                # Append PII report to the message if it was detected
                if len(pii_response) > 0:
                    response_message += "Detected the following types of sensitive personal information with probabilities:\n```"
                    for i in pii_response:
                        response_message = response_message + i['Name'] + ": " + str(i['Score']) + "\n"
                    response_message += "```"

                # Append GPT threat report if ti happened
                if dox == "Threatening":
                    response_message = response_message + gpt_model + " indicates that the message potentially threatens a doxing attack\n"

                # Prompt the mod to handle the report
                response_message += "Type *report* if you would like to take action."

                await mod_channel.send(response_message)
                self.last_report = True
                self.bot_report_message = message

        # Handle Moderator messages in the mod channel
        elif message.channel.name == f'group-{self.group_num}-mod' and self.last_report == True:

            # Call the moderator pipeline
            res = await self.moderator.handle_bot_report(self.bot_report_message, message, self.bot_report_message.author, self.channel)

            # if the user responds, send the message to the mod channel
            if res is not None:
                for r in res:
                    await mod_channel.send(r)

            if await self.moderator.report_complete():
                await self.moderator.reset()
                self.last_report = None

    
    def eval_dox(self, message, model):

        response = openai.ChatCompletion.create(
        model=model,
        messages=[
        {"role": "system", "content": "You are a content moderation system designed to detect threats of doxing. Classify each input as either Threatening or Not Threatening."},
        {"role": "user", "content": "I know where you live"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I know where you work"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "Your address is mine"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I'm excited for the party tonight! Can I have your address?"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "Where do you live?"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I know you're at College University"},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "I know where you live and I'm going to kill you"},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "Your ip address is 1.1.1.1"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I know your ip address"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "What is your ip address?"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I know that your name is John Doe"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "Hey, do you still live in this area? I'm looking to catch up sometime"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "Hey I'm doing some research on you and am gonna post a bunch of your personal info. Starting with location, place of work, parents home, sibling address, etc."},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "Your social security numer is 123-45-6789"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I know your social security number. Give me money or else I will leak this information to the world."},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "I know you study at stanford"},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "Where do you go to school?"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I know your name. You're dead to me."},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "What is your social security number?"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": "I am going to kill you"},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "I know who you are. Send me $10000 or else I'll post your social security number publicly."},
        {"role": "assistant", "content": "Threatening"},
        {"role": "user", "content": "Hey there man! Can you give me the address of the party?"},
        {"role": "assistant", "content": "Not Threatening"},
        {"role": "user", "content": message}
        ]
        )

        return response['choices'][0]['message']['content']

    def eval_pii(self, message):
        aws_comprehend = boto3.client('comprehend')

        # Detect PII components in the message
        response = aws_comprehend.contains_pii_entities(Text = message, LanguageCode = 'en')
        return response['Labels']
    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "GPT evaluated message as: '" + text+ "'"


client = ModBot()
client.run(discord_token)
