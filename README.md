Usage Menu for Bot Commands
Display usage menu:
.usage
Add event:
.add_event <event_name> <event_date> <event_time> <location> <contact>
Delete event:
.delete_event <event_name>
Update event information:
.update_event <event_name> <name|date|time|location|contact=val_to_update> ...
Clear all events:
.clear_events
View details of a specific event:
.view_event <event_name>
View todo list of a specific person:
.todo <person_name>
View all events from entire/weekly/monthly calendar:
.calendar [optional: <-a|-w> | <-m> <target_month>]
Refresh calendar by removing outdate events:
.refresh_calendar
Count number of events:
.count_events
Exit to stop bot from running:
.exit