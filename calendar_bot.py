import os
import re
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

import sqlite3
import discord
from discord.ext import commands, tasks

# Loading env for variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER_ID = int(os.getenv('SERVER_ID'))

# Connecting to local database & create event & todo tables if not exists
sql = sqlite3.connect('calendar.db')
cursor = sql.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        event_name TEXT,
        event_date TEXT,
        event_time TEXT,
        location TEXT,
        contact TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS todos (
        task_name TEXT,
        task_deadline TEXT,
        status TEXT,
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
embed.add_field(name='Add event:', value='`.add_event <event_name> <event_date> <event_time> <location> <contact>`', inline=False)
embed.add_field(name='Delete event:', value='`.delete_event <event_name>`', inline=False)
embed.add_field(name='Update event information:', value='`.update_event <event_name> <name|date|time|location|contact=val_to_update> ...`', inline=False)
embed.add_field(name='Clear all events:', value='`.clear_events`', inline=False)
embed.add_field(name='View details of a specific event:', value='`.view_event <event_name>`', inline=False)
embed.add_field(name='View todo list of a specific person:', value='`.todo <person_name>`', inline=False)
embed.add_field(name='View all events from entire/weekly/monthly calendar:', value='`.calendar [optional: <-a|-w> | <-m> <target_month>]`', inline=False)
embed.add_field(name='Refresh calendar by removing outdate events:', value='`.refresh_calendar`', inline=False)
embed.add_field(name='Count number of events:', value='`.count_events`', inline=False)
embed.add_field(name='Exit to stop bot from running:', value='`.exit`', inline=False)

'''
    Helper functions
'''
# To validate date format
def validate_date_format(input_date):
    try:
        input_date = input_date.replace('/', '-')
        return datetime.strptime(input_date, '%m-%d-%Y').date()
    except Exception as e:
        print(f'Error: {e}')

# To validate time format
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

# Search event based on given name
def search_event(event_name):
    try:
        cursor.execute('SELECT * FROM events WHERE event_name=? COLLATE NOCASE', (event_name,))
        return cursor.fetchone()
    except Exception as e:
        print(f'Error: {e}')

# Calculate time range from start to end given option flag & optional month param
def calculate_time_range(option, month=None):
    try:
        today = datetime.now()
        # return month
        if option == '-m' and month:
            return (f'{today.year:04d}-{month:02d}-01', f'{today.year:04d}-{month:02d}-31')
        
        # else return week by default
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    except Exception as e:
        print(f'Error: {e}')

def count_num_events():
    global num_events
    try:
        count = cursor.execute('SELECT Count(*) FROM events')
        num_events = count.fetchone()[0]
        print(f'There are {num_events} event(s) on record.\n')
        return num_events
    except Exception as e:
        print(f'Error: {e}')

# Refresh database
def refresh_database():
    try:
        print('Starts refreshing...')
        today = datetime.now().date()
        cursor.execute('''
            DELETE FROM events where strftime('%Y-%m-%d', event_date) < ?
        ''',(today,))
        sql.commit()
        count_num_events()
        print('Finished refreshing.')
    except Exception as e:
        print(f'Error: {e}')

# Create a discord embed of calendar
def create_calendar_embed(title, events):
    try:
        if not events:
            raise Exception('Nothing is on record.')

        # Else start printing calendar, sorted by ascending date
        event_list = ''
        events = sorted(events, key=lambda x: x[1])

        for event in events:
            event_name, event_date, event_time, location, contact = event
            event_list += f'{event_name}, {event_date}, {event_time}, {location}, {contact}\n'

        calendar_embed = discord.Embed(title=title, color=discord.Color.from_rgb(115, 138, 219))        
        calendar_embed.add_field(name='Number of events', value=len(events))
        calendar_embed.add_field(name='Event Name, Event Date, Event Time, Location, Contact', value=event_list, inline=False)

        return calendar_embed
    except Exception as e:
        print(f'Error: {e}')

# Create a discord embed of an event
def create_event_embed(title, event):
    try:
        if not event:
            raise Exception('Nothing is on record.')

        name, date, time, location, contact = event

        event_embed = discord.Embed(title=title, color=discord.Color.from_rgb(115, 138, 219))        
        event_embed.add_field(name='Name', value=name)
        event_embed.add_field(name='Date', value=date, inline=False)
        event_embed.add_field(name='Time', value=time, inline=False)
        event_embed.add_field(name='Location', value=location, inline=False)
        event_embed.add_field(name='Contact', value=contact, inline=False)

        return event_embed
    except Exception as e:
        print(f'Error: {e}')

# '''
#     A loop to check reminders every 30 minutes (adjust as needed)
# '''
# @tasks.loop(minutes=30)
# async def check_reminders():
#     events = get_upcoming_events()

#     for event in events:
#         # # Calculate the time remaining until the event's deadline
#         # time_until_deadline = event['deadline'] - datetime.now()

#         # # Define the time threshold for sending reminders (e.g., 1 hour)
#         # reminder_threshold = timedelta(hours=1)

#         # if time_until_deadline < reminder_threshold:
#         #     # Send a reminder message to the designated Discord channel
#         #     channel_id = event['channel_id']
#         #     channel = bot.get_channel(channel_id)
#         #     await channel.send(f"Reminder: {event['name']} is coming up soon!")

'''
    Handling event
'''
# Bot will send welcome msg once ready
@bot.event
async def on_ready():
    print(f'\n{bot.user} has connected to Discord!\n')
    try:
        # check_reminders.start()
        
        # Refresh database & count how many events saved in updated database
        refresh_database()

        # Find all events happening today
        count = cursor.execute('''
            SELECT Count(*) FROM events
            WHERE strftime('%Y-%m-%d', event_date) = ?
        ''', (datetime.now().date(),))
        count_event_today = count.fetchone()[0]

        event_today_msg = f' There are {count_event_today} event(s) happening today.' if count_event_today else ''

        # Send welcome message
        guild = bot.get_guild(SERVER_ID)
        if guild:
            channel = discord.utils.get(guild.text_channels, name='general')
            if channel:
                await channel.send(f'Hello user!{event_today_msg} What can I help you?')
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
        if len(args) != 5:
            raise Exception(f'Usage: `.add_event <event_name> <event_date> <event_time> <contact>`')

        event_name, event_date, event_time, location, contact = args
        formatted_date, formatted_time = validate_date_format(event_date), validate_time_format(event_time)
        print(f'formatted_date:{formatted_date}, formatted_time:{formatted_time}')
        
        # Error: Invalid date/time
        if not formatted_date or not formatted_time or formatted_date < date.today():
            exception_str = f'Error: user cannot set past date as event time.' if formatted_date < date.today() else f"Error: please make sure event date&time match format 'MM/DD/YYYY' & 'HH:MM AM/PM'."
            raise Exception(exception_str)
        
        # Error: Event to add already exists
        if search_event(event_name):
            raise Exception(f"Event '{event_name}' is already on record. Please use `.update_event` command if you would like to update event information.")
            
        # Add event to database if not on record
        cursor.execute(
            'INSERT INTO events (event_name, event_date, event_time, location, contact) VALUES (?, ?, ?, ?, ?)',
            (event_name.strip(), formatted_date, formatted_time, location.strip(), contact.strip())
        )
        sql.commit()

        await ctx.send(f'Event has added successfully for User {str(ctx.author.name)}. There are currently {count_num_events()} event(s) on record.')
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will update event based on user input if receive '.update_event' command
@bot.command()
async def update_event(ctx, *args):
    try:
        if len(args) < 2 or len(args) > 4:
            raise Exception(f'Usage: `.update_event <event_name> <name|date|time|location|contact=val_to_update> ...`')
        
        # Set up dictionary for event info to update & check if event exists
        event_info = { 'name': None, 'date': None, 'time': None, 'location': None, 'contact': None }
        match = search_event(args[0])
        if not match:
            raise Exception(f"Event '{args[0]}' is not on record. Please use `.add_event` command if you would like to update event information.")
        
        # Set up dictionary for event info that matches event name
        match_event_info = {}
        for i, field in enumerate(['name', 'date', 'time', 'location', 'contact']):
            match_event_info[field] = match[i]

        # Update infomation based on each given arg
        for i in range(1, len(args)):
            split_arr = args[i].split('=')

            # if given field_val string never contains '=' symbol
            if len(split_arr) == 1:
                raise Exception(f'Usage: `.update_event <event_name> <name|date|time|location|contact=val_to_update> ...`')
            
            field, val = split_arr[0].strip(), split_arr[1].strip()

            if field == 'name' or field == 'location' or field == 'contact':
                event_info[field] = val
            elif field == 'date':
                event_info['date'] = validate_date_format(val)
                if not event_info['date']:
                    raise Exception(f"Error: event date '{val}' does not match format 'MM/DD/YYYY'.")
            elif field == 'time':
                event_info['time'] = validate_time_format(val)
                if not event_info['time']:
                    raise Exception(f"Error: event time '{val}' does not match format 'HH:MM AM/PM'.")
            else:
                raise Exception(f'Usage: `.update_event <event_name> <name|date|time|contact=val_to_update> ...`')
            
            for field in event_info:
                if not event_info[field]:
                    event_info[field] = match_event_info[field]
        
        cursor.execute(
            '''
                UPDATE events
                SET event_name=?, event_date=?, event_time=?, location=?, contact=?
                WHERE event_name=? COLLATE NOCASE
            ''', (event_info['name'], event_info['date'], event_info['time'], event_info['location'], event_info['contact'], args[0])
        )
        sql.commit()

        event_embed = create_event_embed('Updated information of entered event',(event_info['name'], event_info['date'], event_info['time'], event_info['location'], event_info['contact']))
        if not event_embed:
            raise Exception(f"Unable to print out updated information.")
        await ctx.send(embed=event_embed)

    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will delete event based on user input if receive '.delete_event' command
@bot.command()
async def delete_event(ctx, event_name):
    try:
        if not event_name:
            raise Exception(f'Usage: `.delete_event <event_name>`')
        
        if not search_event(event_name):
            raise Exception(f"Event '{event_name}' is not on record and so cannot be deleted.")
            
        cursor.execute('DELETE FROM events WHERE event_name=? COLLATE NOCASE', (event_name,))
        sql.commit()

        await ctx.send(f"Event '{event_name}' has now deleted from record. There are currently {count_num_events()} event(s) on record.")
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will display event info based on given name if receive '.view_event' command
@bot.command()
async def view_event(ctx, event_name):
    try:
        if not event_name:
            raise Exception(f'Usage: `.view_event <event_name>`')
    
        matched_event = search_event(event_name)
        if not matched_event:
            raise Exception(f"Event '{event_name}' is not on record.")
        
        event_embed = create_event_embed('Event information', matched_event)
        if not event_embed:
            raise Exception(f"Unable to print out updated information.")
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

        # Create & send embed of todo list
        calendar_embed = create_calendar_embed(f'Todo calendar for {contact.capitalize()}', events)
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
        title = 'Calendar - '
        no_record_msg = 'There is currently no event on record. Start adding by using `.add_event` command now!'
        
        # Display entire calendar / calendar of the week
        if not option or option == '-a':
            # Obtain list of events from database
            cursor.execute('SELECT * FROM events')
            events = cursor.fetchall()
            title += 'Current semester'
            num_events = len(events)
        else:
            # Calculate start & end date of current week/month or given month for calendar
            if option == '-w':
                start, end = calculate_time_range(option)
                title += f'Week of {start}'
                no_record_msg = 'There is currently no event on record for current week.'
            else:
                today = datetime.now()
                target_month = int(additional_arg) if additional_arg else today.month
                if target_month < today.month:
                    raise Exception(f'Note: Given target_month should be in range from current month - December.')

                start, end = calculate_time_range(option, target_month)
                date_obj = datetime(today.year, target_month, 1)
                title += date_obj.strftime('%B')
                no_record_msg = 'There is currently no event on record for given month.' if additional_arg else 'There is currently no event on record for current month.'

            print(f'start:{start} - end:{end}\n')

            # Find all events during given time range
            cursor.execute('''
                SELECT * FROM events
                WHERE strftime('%Y-%m-%d', event_date) BETWEEN ? AND ?
            ''', (start, end))
            events = cursor.fetchall()

        # Create & send embed of calendar
        calendar_embed = create_calendar_embed(title, events)
        if not calendar_embed:
            raise Exception(no_record_msg)
        await ctx.send(embed=calendar_embed)
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(e)

# Bot will refresh calendar & remove outdated event(s) from database if receive '.refresh_calendar' command
@bot.command()
async def refresh_calendar(ctx):
    try:
        if num_events > 0:
            print(f'Now refreshing: we had {num_events} on calendar.')
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
        cursor.execute('DELETE FROM events')
        sql.commit()
        count_num_events()
        await ctx.send(f'Event list has cleared successfully.')
    except Exception as e:
        await ctx.send(f'Error: {e}')

# Bot will list number of events stored in database if receive '.num_events' command
@bot.command()
async def count_events(ctx):
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