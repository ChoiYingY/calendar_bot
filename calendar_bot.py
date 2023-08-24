import os
import re
import datetime
from dotenv import load_dotenv

import sqlite3
import discord
from discord.ext import commands

# Loading env for variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER_ID = int(os.getenv('SERVER_ID'))

# Connecting to local database & create table if not exists
sql = sqlite3.connect('events.db')
cursor = sql.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        event_name TEXT,
        event_date TEXT,
        event_time TEXT,
        contact TEXT
    )
''')
sql.commit()

# Set up discord bot connection
description = ''' Help command Description '''
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='.', description=description, intents=intents)

# Set up global variables (#events & embed usage menu)
num_events = 0
embed = discord.Embed(title=f'Usage Menu for Bot Commands', color=discord.Color.from_rgb(115, 138, 219))
embed.add_field(name='Display usage menu:', value='`.usage`')
embed.add_field(name='Add event:', value='`.add_event <event_name> <event_date> <event_time> <contact>`', inline=False)
embed.add_field(name='Update event:', value='`.update_event <event_name> <date|time|contact=val_to_update> ...`', inline=False)
embed.add_field(name='Delete event:', value='`.delete_event <event_name>`', inline=False)
embed.add_field(name='Count number of events:', value='`.num_events`', inline=False)
embed.add_field(name='View event calendar:', value='`.calendar`', inline=False)
embed.add_field(name='Clear all events:', value='`.clear_events`', inline=False)
embed.add_field(name='Exit to stop bot from running:', value='`.exit`', inline=False)

'''
    Handling event
'''
# Bot will send welcome msg once ready
@bot.event
async def on_ready():
    global num_events
    print(f'\n{bot.user} has connected to Discord!\n')
    try:
        # Count how many events saved in database
        count = cursor.execute('SELECT Count(*) FROM events')
        num_events = count.fetchone()[0]
        print(f'There are {num_events} events on record.')

        # Send welcome message
        guild = bot.get_guild(SERVER_ID)
        if guild:
            channel = discord.utils.get(guild.text_channels, name='general')
            if channel:
                await channel.send('Hello user! What can I help you today?')
                await channel.send(embed=embed)
    except Exception:
        print('Bot is unable to send welcome message on general channel')

'''
    Helper functions to validate date/time format
'''
def validate_date_format(input_date):
    try:
        input_date = input_date.replace('-', '/')
        return datetime.datetime.strptime(input_date, '%m/%d/%Y').date()
    except Exception as e:
        print(f'Error: {e}')

def validate_time_format(input_time):
    try:
        match = re.fullmatch('((\d{1}|\d{2}):(\d{2})(AM|PM))', input_time, re.IGNORECASE)
        if match:
            hour = int(match.group(2))
            min = int(match.group(3))
            time_period = match.group(4).upper()
            if hour <= 0 or hour >= 13 or min < 0 or min > 59:
                print(f'invalid hour or min - {hour}:{min}')
            else:
                min = '0'+ str(min) if min < 10 else str(min)
                return f'{hour}:{min} {time_period}'
    except Exception as e:
        print(f'Error: {e}')

'''
    Handling user commands
'''
# Bot will add event based on user input if receive '.add_event <event_name> <event_date> <contact>' command
@bot.command()
async def add_event(ctx, *args):
    global num_events
    if len(args) != 4:
        await ctx.send(f'Usage: `.add_event <event_name> <event_date> <event_time> <contact>`')
        return

    event_name, event_date, event_time, contact = args
    try:
        # Validate event date in format 'MM/DD/YYYY'
        formatted_date = validate_date_format(event_date)
        formatted_time = validate_time_format(event_time)
        
        if not formatted_date:
            await ctx.send(f"Error: event date '{event_date}' does not match format 'MM/DD/YYYY'")
            return
        if not formatted_time:
            await ctx.send(f"Error: event time '{event_time}' does not match format 'HH:MM AM/PM'")
            return
    except Exception as e:
        await ctx.send(f'Error: unable to validate event date/time. Try entering command again.')
        return
    
    # Add event to database if time is not outdated & not on record
    try:
        if formatted_date >= datetime.date.today():
            # stop adding if event is already on record
            cursor.execute('SELECT * FROM events WHERE event_name=?', (event_name,))
            if cursor.fetchone():
                await ctx.send(f'Event {event_name} is already on record. Please use `.update_event` command if you would like to update event information.')
                return

            cursor.execute(
                'INSERT INTO events (event_name, event_date, event_time, contact) VALUES (?, ?, ?, ?)',
                (event_name, formatted_date, formatted_time, contact)
            )
            sql.commit()
            num_events += 1
            await ctx.send(f'Event has added successfully for User {str(ctx.author.name)}. There are currently {num_events} events on record.')
        else:
            await ctx.send(f'Error: user cannot set past date as event time.')
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(f'Error: unable to add event. Try entering command again.')

# Bot will update event based on user input if receive '.update_event <event_name> <field=val_to_update>' command
@bot.command()
async def update_event(ctx, *args):
    if len(args) < 2 or len(args) > 4:
        await ctx.send(f'Usage: `.update_event <event_name> <date|time|contact=val_to_update> ...`')
        return
    
    try:
        event_name, event_date, event_time, contact = args[0], None, None, None
        cursor.execute('SELECT * FROM events WHERE event_name=?', (event_name,))
        match = cursor.fetchone()
        if not match:
            await ctx.send(f'Event {event_name} is not on record. Please use `.add_event` command if you would like to update event information.')
            return
        
        field_val_to_update = args[1:]

        for field_val in field_val_to_update:
            split_arr = field_val.split('=')

            # if given field_val string never contains '=' symbol
            if len(split_arr) == 1:
                await ctx.send(f'Usage: `.update_event <event_name> <date|time|contact=val_to_update> ...`')
                return
            
            field, val = split_arr[0], split_arr[1]
            if field == 'date':
                event_date = validate_date_format(val)
                if not event_date:
                    await ctx.send(f"Error: event date '{event_date}' does not match format 'MM/DD/YYYY'")
                    return
            elif field == 'time':
                event_time = validate_time_format(val)
                if not event_time:
                    await ctx.send(f"Error: event date '{event_time}' does not match format 'HH:MM AM/PM'")
                    return
            elif field == 'contact':
                contact = val
            else:
                await ctx.send(f'Usage: `.update_event <event_name> <date|time|contact=val_to_update> ...`')
                return
        
        if not event_date:
            event_date = match[1]
        if not event_time:
            event_time = match[2]
        if not contact:
            contact = match[3]
        
        print((event_name, event_date, event_time, contact))

        cursor.execute(
            '''
                UPDATE events
                SET event_date=?, event_time=?, event_time=?
                WHERE event_name=?;
            ''', (event_date, event_time, contact, event_name)
        )
        sql.commit()

        embed = discord.Embed(title=f'Updated detail of Event {event_name}', color=discord.Color.from_rgb(115, 138, 219))
        embed.add_field(name='Date', value=event_date)
        embed.add_field(name='Time', value=event_time, inline=False)
        embed.add_field(name='Contact', value=contact, inline=False)
        await ctx.send(embed=embed)

    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(f'Error: unable to update event. Try entering command again.')

# Bot will delete event based on user input if receive '.delete_event <event_name>' command
@bot.command()
async def delete_event(ctx, event_name):
    global num_events
    if not event_name:
        await ctx.send(f'Usage: `.delete_event <event_name>`.')
        return
    
    cursor.execute('SELECT * FROM events WHERE event_name=?', (event_name,))
    match = cursor.fetchone()
    if match:
        print(match)
        cursor.execute('DELETE FROM events WHERE event_name=?', (event_name,))
        sql.commit()
        num_events -= 1
        await ctx.send(f'Event {event_name} has now deleted from record. There are currently {num_events} events on record.')
    else:
        await ctx.send(f'Event {event_name} is not on record and so cannot be deleted.')
        return

# Bot will lists all events stored in database if receive '.calendar' command
@bot.command()
async def calendar(ctx, option=None):
    global num_events
    if option and option != '-i':
        await ctx.send(f'Usage: `.calendar <-i [optional]>`')
        return

    # Obtain list of events from database
    cursor.execute('SELECT rowid, * FROM events')
    events = cursor.fetchall()
    num_events = len(events)
    event_list_title = 'Event ID, Event Name, Date/Deadline, Contact' if option else 'Event Name, Event Date, Contact'

    if events:
        event_list = ''
        for event in events:
            id, event_name, event_date, event_time, contact = event
            event_detail = f'{event_name}, {event_date}, {event_time}, {contact}'
            event_list += f'\n{id}, {event_detail}' if option else event_detail

        embed = discord.Embed(title=f'Calendar - Week of {datetime.date.today()}', color=discord.Color.from_rgb(115, 138, 219))
        embed.add_field(name='Number of events', value=num_events)
        embed.add_field(name=event_list_title, value=event_list, inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'There is currently no event on record. Start adding by using `.add_event` command now!')


# Bot will clear all events stored in database if receive '.clear_events' command
@bot.command()
async def clear_events(ctx):
    global num_events
    cursor.execute('DELETE FROM events')
    sql.commit()
    num_events = 0
    await ctx.send(f'Event list has cleared successfully.')

# Bot will list number of events stored in database if receive '.num_events' command
@bot.command()
async def num_events(ctx):
    await ctx.send(f'There are currently {num_events} on the record.')

# Bot will print usage menu if receive '.usage' command
@bot.command()
async def usage(ctx):
    await ctx.send(embed=embed)

# Bot will close database connection & go offline if receive '.bye' command
@bot.command()
async def exit(ctx):
    cursor.close()
    sql.close()

    await ctx.send('I will now go offline. See you later!')
    await bot.close()
    exit(1)

'''
    Running main function
'''
if __name__ == '__main__':
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'Error: {e}')