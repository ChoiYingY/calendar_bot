# Discord Calendar Bot

## Description
This is a Discord command bot developed to act as a calendar that manages upcoming events & to-do tasks for members within a Discord Channel.

## Usage Menu for Bot Commands
| Command                                                                          | Description                                                                                     |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `.usage`                                                                         | Display the usage menu.                                                                         |
| `.add_event <event_name> <event_date> <event_time> <location> <contact>`         | Add an event by name, date, time, location & contact.                                           |
| `.delete_event <event_name>`                                                     | Given the event name, delete that event.                                                        |
| `.update_event <event_name> <field1_to_update>=<val1_to_update> <field2_to_update>=<val2_to_update> ...` | Given the event name, update that event info by providing value(s) for one or more specific field to update (name / date / time / location / contact).   |
| `.clear_events`                                                                  | Clear all events on the calendar.                                                               |
| `.view_event <event_name>`                                                       | Given the event name, view its detailed information.                                            |
| `.todo <person_name>`                                                            | Given a person's name, view to-do lists and all events that are related to that person.         |
| `.calendar [optional: <-a> or <-w> or <-m> <target_month>]`                      | View all events from the entire/weekly/monthly calendar<br> `<-a>` for all,<br> `<-w>` for the current week,<br>`<-m>` for the current month and a specific month if enter along with arg <target_month>.                                  |
| `.refresh_calendar`                                                              | Refresh the calendar by removing outdated events.                                               |
| `.count_events`                                                                  | Count the number of upcoming events.                                                            |
| `.exit`                                                                          | Exit to stop the bot from running.                                                                  |
