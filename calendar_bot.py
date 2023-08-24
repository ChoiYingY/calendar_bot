import os
import re
from datetime import datetime, timedelta, date
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
embed.add_field(name='Delete event:', value='`.delete_event <event_name>`', inline=False)
embed.add_field(name='Update event information:', value='`.update_event <event_name> <name|date|time|contact=val_to_update> ...`', inline=False)
embed.add_field(name='Clear all events:', value='`.clear_events`', inline=False)
embed.add_field(name='View details of a specific event:', value='`.view_event <event_name>`', inline=False)
embed.add_field(name='View todo list of a specific person:', value='`.todo <person_name>`', inline=False)
embed.add_field(name='View all events from entire/weekly/monthly calendar:', value='`.calendar [optional: <-a|-w> | <-m> <target_month>]`', inline=False)
embed.add_field(name='Count number of events:', value='`.num_events`', inline=False)
embed.add_field(name='Exit to stop bot from running:', value='`.exit`', inline=False)

'''
    Helper functions to validate date/time format
'''
def validate_date_format(input_date):
    try:
        input_date = input_date.replace('/', '-')
        return datetime.strptime(input_date, '%m-%d-%Y').date()
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
                raise Exception(f'invalid hour or min -> {hour}:{min}.')
            else:
                return f'{hour}:{min:02d} {time_period}'
    except Exception as e:
        print(f'Error: {e}')

def refresh_database():
    try:
        print('Starts refreshing...')
        today = datetime.now().date()
        cursor.execute('''
            DELETE FROM events where strftime('%Y-%m-%d', event_date) < ?
        ''',(today,))
        sql.commit()
        print('Finished refreshing.')
    except Exception as e:
        print(f'Error: {e}')

def create_calendar_embed(events, title, total_events):
    try:
        if not events:
            raise Exception('Nothing is on record.')

        # Else start printing calendar, sorted by ascending date
        event_list_title = 'Event Name, Event Date, Contact'
        event_list = ''
        events = sorted(events, key=lambda x: x[1])

        for event in events:
            event_name, event_date, event_time, contact = event
            event_list += f'{event_name}, {event_date}, {event_time}, {contact}\n'

        calendar_embed = discord.Embed(title=title, color=discord.Color.from_rgb(115, 138, 219))        
        calendar_embed.add_field(name='Number of events', value=total_events)
        calendar_embed.add_field(name=event_list_title, value=event_list, inline=False)

        return calendar_embed
    except Exception as e:
        print(f'Error: {e}')

'''
    Handling event
'''
# Bot will send welcome msg once ready
@bot.event
async def on_ready():
    global num_events
    print(f'\n{bot.user} has connected to Discord!\n')
    try:
        refresh_database()

        # Count how many events saved in database
        count = cursor.execute('SELECT Count(*) FROM events')
        num_events = count.fetchone()[0]
        print(f'There are {num_events} events on record.\n')

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
    Handling user commands
'''
# Bot will add event based on user input if receive '.add_event' command
@bot.command()
async def add_event(ctx, *args):
    try:
        global num_events
        if len(args) != 4:
            raise Exception(f'Usage: `.add_event <event_name> <event_date> <event_time> <contact>`')

        event_name, event_date, event_time, contact = args
        # Validate event date in format 'MM-DD-YYYY'
        formatted_date = validate_date_format(event_date)
        formatted_time = validate_time_format(event_time)

        print(f'formatted_date:{formatted_date}, formatted_time:{formatted_time}')
        
        if not formatted_date or not formatted_time:
            raise Exception(f"Error: please make sure event date&time match format 'MM/DD/YYYY' & 'HH:MM AM/PM'/")
    
        # Check if event time is outdated
        if formatted_date < date.today():
            raise Exception(f'Error: user cannot set past date as event time.')
            
        # Stop adding if event is already on record
        cursor.execute('SELECT * FROM events WHERE event_name=? COLLATE NOCASE', (event_name,))
        if cursor.fetchone():
            raise Exception(f"Event '{event_name}' is already on record. Please use `.update_event` command if you would like to update event information.")

        # Add event to database if not on record
        cursor.execute(
            'INSERT INTO events (event_name, event_date, event_time, contact) VALUES (?, ?, ?, ?)',
            (event_name.strip(), formatted_date, formatted_time, contact.strip())
        )
        sql.commit()
        num_events += 1
        await ctx.send(f'Event has added successfully for User {str(ctx.author.name)}. There are currently {num_events} events on record.')
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will update event based on user input if receive '.update_event' command
@bot.command()
async def update_event(ctx, *args):
    try:
        if len(args) < 2 or len(args) > 4:
            raise Exception(f'Usage: `.update_event <event_name> <name|date|time|contact=val_to_update> ...`')
    
        name, date, time, contact = None, None, None, None
        cursor.execute('SELECT * FROM events WHERE event_name=? COLLATE NOCASE', (args[0],))
        match = cursor.fetchone()
        if not match:
            raise Exception(f"Event '{args[0]}' is not on record. Please use `.add_event` command if you would like to update event information.")
        
        field_val_to_update = args[1:]

        for field_val in field_val_to_update:
            split_arr = field_val.split('=')

            # if given field_val string never contains '=' symbol
            if len(split_arr) == 1:
                raise Exception(f'Usage: `.update_event <event_name> <name|date|time|contact=val_to_update> ...`')
            
            field, val = split_arr[0].strip(), split_arr[1].strip()
            if field == 'name':
                name = val
            elif field == 'date':
                date = validate_date_format(val)
                if not date:
                    raise Exception(f"Error: event date '{date}' does not match format 'MM/DD/YYYY'")
            elif field == 'time':
                time = validate_time_format(val)
                if not time:
                    raise Exception(f"Error: event time '{time}' does not match format 'HH:MM AM/PM'")
            elif field == 'contact':
                contact = val
            else:
                raise Exception(f'Usage: `.update_event <event_name> <name|date|time|contact=val_to_update> ...`')
        
        if not name:
            name = match[0]
        if not date:
            date = match[1]
        if not time:
            time = match[2]
        if not contact:
            contact = match[3]
        
        print((name, date, time, contact))

        cursor.execute(
            '''
                UPDATE events
                SET event_name=?, event_date=?, event_time=?, contact=?
                WHERE event_name=?;
            ''', (name, date, time, contact, args[0])
        )
        sql.commit()

        update_embed = discord.Embed(title=f'Updated details of entered event', color=discord.Color.from_rgb(115, 138, 219))
        update_embed.add_field(name='Name', value=name)
        update_embed.add_field(name='Date', value=date, inline=False)
        update_embed.add_field(name='Time', value=time, inline=False)
        update_embed.add_field(name='Contact', value=contact, inline=False)
        await ctx.send(embed=update_embed)

    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will delete event based on user input if receive '.delete_event' command
@bot.command()
async def delete_event(ctx, event_name):
    global num_events
    try:
        if not event_name:
            raise Exception(f'Usage: `.delete_event <event_name>`')
        
        cursor.execute('SELECT * FROM events WHERE event_name=? COLLATE NOCASE', (event_name,))
        match = cursor.fetchone()
        if not match:
            raise Exception(f"Event '{event_name}' is not on record and so cannot be deleted.")
            
        print(match)
        cursor.execute('DELETE FROM events WHERE event_name=?', (event_name,))
        sql.commit()
        num_events -= 1
        await ctx.send(f"Event '{event_name}' has now deleted from record. There are currently {num_events} events on record.")
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will display event info based on given name if receive '.view_event' command
@bot.command()
async def view_event(ctx, event_name):
    try:
        if not event_name:
            raise Exception(f'Usage: `.view_event <event_name>`')
    
        cursor.execute('SELECT * FROM events WHERE event_name=? COLLATE NOCASE', (event_name,))
        match = cursor.fetchone()
        if not match:
            raise Exception(f"Event '{event_name}' is not on record.")
        
        name, date, time, contact = match
        event_embed = discord.Embed(title='Event details', color=discord.Color.from_rgb(115, 138, 219))
        event_embed.add_field(name='Name', value=name)
        event_embed.add_field(name='Date', value=date, inline=False)
        event_embed.add_field(name='Time', value=time, inline=False)
        event_embed.add_field(name='Contact', value=contact, inline=False)
        await ctx.send(embed=event_embed)
    except Exception as e:
        print(f'Error: {e}')
        ctx.send(e)

# Bot will display all todo events of given contact if receive '.todo' command
@bot.command()
async def todo(ctx, contact):
    try:
        if not contact:
            raise Exception(f'Usage: `.todo <contact>`')

        cursor.execute('''SELECT * FROM events WHERE contact LIKE ? COLLATE NOCASE''', (f'%{contact.strip()}%',))
        events = cursor.fetchall()
        total_events = len(events)

        # Create & send embed of todo list
        calendar_embed = create_calendar_embed(events, f'Todo calendar for {contact.capitalize()}', total_events)
        if not calendar_embed:
            raise Exception(f'No task todo for {contact.capitalize()}.')
        await ctx.send(embed=calendar_embed)
    except Exception as e:
        print(f'Error: {e}')
        ctx.send(e)

# Bot will list all events (of all time OR curr week OR curr/given month) stored in database if receive '.calendar' command
@bot.command()
async def calendar(ctx, option=None, additional_arg=None):
    global num_events
    try:
        if option and option != '-a' and option != '-w' and option != '-m':
            raise Exception(f'Usage: `.calendar [optional: <-a|-w> | <-m> <target_month>]`')

        events = None
        total_events = 0
        title = 'Calendar - '
        no_record_msg = 'There is currently no event on record. Start adding by using `.add_event` command now!'
        
        # Display entire calendar / calendar of the week
        if not option or option == '-a':
            # Obtain list of events from database
            cursor.execute('SELECT * FROM events')
            events = cursor.fetchall()
            title += 'Current semester'
            total_events = num_events = len(events)
        else:
            # Calculate start & end date of current week/month or given month for calendar
            today = datetime.now()
    
            if option == '-w':
                # format start & end of curr week to string
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=6)
                start = start.strftime('%Y-%m-%d')
                end = end.strftime('%Y-%m-%d')

                title += f'Week of {start}'
                no_record_msg = 'There is currently no event on record for current week.'
            else:
                target_year = today.year
                target_month = today.month
                if additional_arg:
                    target_month = int(additional_arg)
                    no_record_msg = 'There is currently no event on record for given month.'
                else:
                    no_record_msg = 'There is currently no event on record for current month.'

                if target_month < today.month:
                    raise Exception(f'Note: Given target_month should be in range from current month - December.')

                date_obj = datetime(target_year, target_month, 1)
                title += date_obj.strftime('%B')

                start = f'{target_year:04d}-{target_month:02d}-01'
                end = f'{target_year:04d}-{target_month:02d}-31'

            print(f'start:{start} - end:{end}\n')

            # Find all events during given time range
            cursor.execute('''
                SELECT * FROM events
                WHERE strftime('%Y-%m-%d', event_date) BETWEEN ? AND ?
            ''', (start, end))
            events = cursor.fetchall()
            total_events = len(events)
        
        # Create & send embed of calendar
        calendar_embed = create_calendar_embed(events, title, total_events)
        if not calendar_embed:
            raise Exception(no_record_msg)
        await ctx.send(embed=calendar_embed)
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will refresh calendar & remove outdated event(s) from database if receive '.refresh_calendar' command
@bot.command
async def refresh_calendar(ctx):
    try:
        if num_events > 0:
            refresh_database()
            await ctx.send(f'Calendar refreshed: All outdated events have been deleted.')
        else:
            raise Exception('Nothing to be refresh on calendar')
    except Exception as e:
        await ctx.send(f'Error: {e}')

# Bot will clear all events stored in database if receive '.clear_events' command
@bot.command()
async def clear_events(ctx):
    try:
        global num_events
        cursor.execute('DELETE FROM events')
        sql.commit()
        num_events = 0
        await ctx.send(f'Event list has cleared successfully.')
    except Exception as e:
        await ctx.send(f'Error: {e}')

# Bot will list number of events stored in database if receive '.num_events' command
@bot.command()
async def num_events(ctx):
    try:
        await ctx.send(f'There are currently {num_events} events on the record.')
    except Exception as e:
        await ctx.send(f'Error: {e}')

# Bot will print usage menu if receive '.usage' command
@bot.command()
async def usage(ctx):
    try:
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f'Error: {e}')


# Bot will close database connection & go offline if receive '.exit' command
@bot.command()
async def exit(ctx):
    try:
        cursor.close()
        sql.close()
        await ctx.send('I will now go offline. See you later!')
        await bot.close()
        exit(1)
    except Exception as e:
        await ctx.send(f'Error: {e}')
        exit(0)

'''
    Running main function
'''
if __name__ == '__main__':
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'Error: {e}')