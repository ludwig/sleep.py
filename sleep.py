#!/usr/bin/env python3
"""
sleep.py: Track your sleep using Google Calendar.

This script can be used to track your sleeping intervals using Google Calendar.

Everything gets added to a calendar named "Sleep", which you can create
manually ahead of time, or let this script create it for you.

----------------

Supported options for sleep.py:

Options related to the current sleep interval:
  -s, --start: Start time of sleep (e.g., "10 PM yesterday)"
  -e, --end: End time of sleep (e.g., "6 AM today")
  -d, --duration: Duration of sleep (e.g. "8 hours")

Options related to the next sleep interval:
  --next-start, --ns: Start time of next sleep event (e.g., "10 PM tomorrow")
  --next-end, --ne: End time of next sleep event (e.g., "6 AM tomorrow")
  --next-duration, --nd: Duration of next sleep event (e.g. "8 hours")

This offset represents how long you plan to stay awake for:
  --default-offset, -o: Default offset to next sleep event (e.g. "16 hours")

----------------

Example usage:

Suppose you fell asleep at 7:30pm yesterday and woke up at 1:30am today,
and you'd like to add that event to your "Sleep" google calendar.

./sleep.py -s '7:30pm yesterday' -e '1:30 am'

To predict the next sleep interval, add the '-p' flag.

And suppose you know you will fall asleep 21 hours after having woken up,
so you now add the '-o 21' option.

./sleep.py -s '7:30pm yesterday' -e '1:30 am' -p -o 21

And after checking the output is what you want, you can finally
update the "Sleep" Google Calendar by adding the '-u' flag.

./sleep.py -s '7:30pm yesterday' -e '1:30 am' -p -o 21 -u

"""

import argparse
import os
import pickle
import pytz
from datetime import datetime, timedelta

import dateparser
import parsedatetime as pdt
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Directory containing credentials for our script.
DEFAULT_SECURITY_DIR = "~/security/gcp/sleep.py/"
DEFAULT_SECURITY_DIR = os.path.normpath(os.path.expanduser(DEFAULT_SECURITY_DIR))
SECURITY_DIR = os.environ.get('SECURITY_DIR', DEFAULT_SECURITY_DIR)

# The credentials file for our script.
CLIENT_SECRET_JSON = "client_secret.json"
CLIENT_SECRET = os.path.join(SECURITY_DIR, CLIENT_SECRET_JSON)

# The temporary file caching our user's access and refresh tokens.
# We use this strategy to avoid having to re-authenticate through the
# web browser every single time we run the script.
TOKEN_PICKLE = os.path.join(SECURITY_DIR, "token.pickle")

# Calendar details for your "Sleep" calendar.
# You can create it manually in Google Calendar ahead of time,
# or let this script create it for you.
SLEEP_CALENDAR = {
    "summary": "Sleep",
    "timeZone": "America/Los_Angeles"
}
TIMEZONE = pytz.timezone(SLEEP_CALENDAR["timeZone"])

# ANSI escape sequences for colored output.
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def red(text):
    """Return the given text in red."""
    return f"{BOLD}{RED}{text}{RESET}"


def green(text):
    """Return the given text in green."""
    return f"{BOLD}{GREEN}{text}{RESET}"


def blue(text):
    """Return the given text in blue."""
    return f"{BOLD}{BLUE}{text}{RESET}"


def bold(text):
    """Return the given text in bold."""
    return f"{BOLD}{text}{RESET}"


def get_service():
    """Get a Google Calendar API service object."""
    creds = None

    # Basic checks to ensure we have the necessary files and directories.
    if not os.path.exists(SECURITY_DIR):
        raise ValueError(f"Security directory not found: {SECURITY_DIR}")
    if not os.path.exists(CLIENT_SECRET):
        raise ValueError(f"Credentials file not found: {CLIENT_SECRET}")

    # The "token.pickle" file stores the user's access and refresh tokens.
    # We create this file automatically when the authorization flow completes
    # for the first time.
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load client secrets from the JSON file
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)

    # Build the service object
    service = build("calendar", "v3", credentials=creds)
    return service


def list_calendars(service):
    print("Getting list of calendars")
    calendars_result = service.calendarList().list().execute()

    calendars = calendars_result.get("items", [])
    if not calendars:
        print("No calendars found.")
    for calendar in calendars:
        summary = calendar["summary"]
        print(summary)


def get_sleep_calendar_id(service, verbose=False):
    """Get the ID of the "Sleep" calendar.
    
    The name of the "Sleep" calendar is taken from the
    configuration value in SLEEP_CALENDAR["summary"].
    It can be modified there, but we shall refer to it
    generically as "Sleep".

    If the calendar doesn't exist, we create it.
    :return: The ID of the "Sleep" calendar.
    """

    # TODO: Figure out if the API supports a more direct way to check
    # whether a calendar exists.

    # Get list of all calendars.
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get("items", [])

    # Check if "Sleep" calendar exists.
    sleep_calendar = SLEEP_CALENDAR["summary"]
    for calendar in calendars:
        if calendar["summary"] == sleep_calendar:
            if verbose:
                print(f"Calendar '{blue(sleep_calendar)}' already exists.")
                print(f"{BOLD}Calendar ID: {blue(calendar['id'])}")
            return calendar["id"]
    
    # If "Sleep" calendar doesn't exist, create it.
    created_calendar = service.calendars().insert(body=SLEEP_CALENDAR).execute()
    if verbose:
        print(f"Created calendar '{blue(sleep_calendar)}'")
        print(f"{BOLD}Calendar ID: {blue(created_calendar['id'])}")

    return created_calendar["id"]


def create_calendar_event(service, calendar_id, summary, start_time, end_time, timezone, verbose=False):
    event = {
        "summary": summary,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": timezone,
        },
    }
    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    if verbose:
        url = event.get("htmlLink")
        print(f"{BOLD}Created event: {green(url)}")
    return event


def create_sleep_event_now(service, calendar_id, duration=8):
    # NOTE: This function was the original implementation
    # that checked we had the appropriate access to the
    # "Sleep" calendar in our Google account.

    timezone = SLEEP_CALENDAR["timeZone"]

    now = datetime.now(TIMEZONE)
    start_time = now
    end_time = now + timedelta(hours=duration)

    calendar_id = get_sleep_calendar_id(service, verbose=True)

    summary = f"Sleep: {duration:.1f} hours"
    create_calendar_event(service, calendar_id, summary, start_time, end_time, timezone)


def create_sleep_event(service, calendar_id, sleep_interval, event_prefix="Sleep"):
    timezone = SLEEP_CALENDAR["timeZone"]

    start_time, end_time, duration = sleep_interval
    duration_hours = duration.total_seconds() / 3600
    summary = f"{event_prefix}: {duration_hours:.1f} hours"

    event = create_calendar_event(
        service, calendar_id, summary, start_time, end_time, timezone)
    #print(event)

    return event


def create_current_sleep_event(service, calendar_id, current_interval):
    current_sleep_event = create_sleep_event(
        service, calendar_id, current_interval, event_prefix="Sleep")
    url = current_sleep_event.get("htmlLink")
    print(f"{BOLD}Current sleep event:   {green(url)}")
    return current_sleep_event


def create_next_sleep_event(service, calendar_id, next_interval):
    if not next_interval:
        return None
    next_sleep_event = create_sleep_event(
        service, calendar_id, next_interval, event_prefix="Predicted Sleep")
    url = next_sleep_event.get("htmlLink")
    print(f"{BOLD}Predicted sleep event: {green(url)}")
    return next_sleep_event


def parse_time(input_time):
    return dateparser.parse(input_time)


def parse_duration(input_duration):
    """Parse the duration string into a timedelta object.
    
    This function can handle various formats, such as
    "8 hours", "8 hours 30 minutes", "8h 30m", etc.
    """
    # First check whether the input_duration is a number.
    try:
        hours = float(input_duration)
        return timedelta(hours=hours)
    except ValueError:
        pass
    # If that failed, use parsedatetime to parse the duration string.
    cal = pdt.Calendar()
    now = datetime.now()
    time_struct, parse_status = cal.parseDT(
        datetimeString=input_duration,
        sourceTime=now,
    )
    if not parse_status:
        raise ValueError(f"Unable to parse duration: {red(input_duration)}")
    return time_struct - now


def get_checked_duration(start, end, check_duration, threshold_mins=5):
    """Get expected duration based on start and end times.

    We also pass a duration value to check for consistency.
    """
    calculated_duration = end - start
    if not check_duration:
        return calculated_duration

    threshold = timedelta(minutes=threshold_mins)
    if abs(calculated_duration - check_duration) > threshold:
        msg = f"Input duration {red(check_duration)} inconsistent"
        msg += f" with start {red(start)} and end {red(end)}"
        msg += f" (using threshold of {threshold_mins} mins)"
        raise ValueError(msg)
    return max(check_duration, calculated_duration)


def get_interval(input_start, input_end, input_duration, default_end='now', default_duration='8'):
    """Get time interval based on start, end, and duration.
    
    Missing values are calculated based on the other two values.
    Applicable defaults are also introduced in some cases."""

    # Logic to calculate missing value or perform consistency checks.
    start = parse_time(input_start) if input_start else None
    end = parse_time(input_end) if input_end else None
    duration = parse_duration(input_duration) if input_duration else None

    if all([start, end, duration]):
        # Consistency check.
        duration = get_checked_duration(start, end, duration)

    elif start and end:
        # Calculate duration
        duration = get_checked_duration(start, end, duration)
    
    elif start and duration:
        # Calculate end
        end = start + duration
    
    elif end and duration:
        # Calculate start
        start = end - duration

    elif duration and not (start or end):
        end = parse_time(default_end)
        start = end - duration
    
    elif start and not (end or duration):
        duration = parse_duration(default_duration)
        end = start + duration
    
    elif end and not (start or duration):
        duration = parse_duration(default_duration)
        start = end - duration
    
    elif not (start or end or duration):
        # Nothing was passed. Assume end is primary.
        end = parse_time(default_end)
        duration = parse_duration(default_duration)
        start = end - duration
    
    else:
        # Is this even reachable?
        print(f"{BOLD}{RED}DEBUG: start={start}, end={end}, duration={duration}{RESET}")
        raise ValueError("Invalid combination of start, end, and duration")

    start = TIMEZONE.localize(start)
    end = TIMEZONE.localize(end)

    # Check that start is before end.
    if start > end:
        raise ValueError(f"Start time {red(start)} is after end time {red(end)}")

    return start, end, duration


def print_interval(start, end, duration):
    # Can also use '%z' to display offset from UTC.
    start_str = start.strftime("%Y-%m-%d %H:%M %Z")
    end_str = end.strftime("%Y-%m-%d %H:%M %Z")
    duration_hours = duration.total_seconds() / 3600
    duration_str = f"{duration_hours:.1f} hours"
    msg = f"start_time: {green(start_str)}"
    msg += f", end_time: {green(end_str)}"
    msg += f", duration: {green(duration_str)}"
    print(msg)


def prediction_requested(args):
    return args.predict_next or args.next_start or args.next_end or args.next_duration


def get_current_interval(args, verbose=False):
    """Get the current sleep interval."""
    current_interval = get_interval(args.start, args.end, args.duration)
    if verbose:
        print(bold("Current sleep interval:"))
        print_interval(*current_interval)
    return current_interval


def get_next_interval(args, current_interval, verbose=False):
    """Get the next sleep interval, when requested."""
    if not prediction_requested(args):
        return None

    next_start = args.next_start
    next_end = args.next_end
    next_duration = args.next_duration
    offset = parse_duration(args.default_offset)

    if not any([next_start, next_end, next_duration]):
        # Prediction was requested, but no interval information was provided.
        # Let's assume we the start of our next sleep interval will begin
        # after a constant offset (default 16 hours) from the end of the
        # current sleep interval.
        _, curr_end, _ = current_interval
        next_start = curr_end + offset
        next_start = next_start.strftime("%Y-%m-%d %H:%M")

    next_interval = get_interval(next_start, next_end, next_duration)
    if verbose:
        print(bold("Next sleep interval:"))
        print_interval(*next_interval)

    return next_interval


def create_parser():
    parser = argparse.ArgumentParser(
        description="Track sleep and predict next sleep event",
    )
    parser.add_argument(
        "-s", "--start", help='Start time of sleep (e.g., "10 PM yesterday)"')
    parser.add_argument(
        "-e", "--end", help='End time of sleep (e.g., "6 AM today")')
    parser.add_argument(
        "-d", "--duration", help='Duration of sleep (e.g. "8 hours")')

    parser.add_argument(
        "-p", "--predict-next", action='store_true',
        help='Predict the next sleep event')
    parser.add_argument(
        "--next-start", "--ns",
        help='Start time of next sleep event (e.g., "10 PM tomorrow")')
    parser.add_argument(
        "--next-end", "--ne",
        help='End time of next sleep event (e.g., "6 AM tomorrow")')
    parser.add_argument(
        "--next-duration", "--nd",
        help='Duration of next sleep event (e.g. "8 hours")')

    parser.add_argument(
        "--default-offset", "-o", default="16",
        help='Default offset to next sleep event (e.g. "16 hours")')
    
    parser.add_argument(
        "--update-calendar", "-u", action='store_true',
        help='Update calendar with specified sleep events')
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    #print(args)

    # Determine the current sleep interval.
    current_interval = get_current_interval(args, verbose=True)

    # Determine the next sleep interval, if requested.
    next_interval = get_next_interval(args, current_interval, verbose=True)

    if not args.update_calendar:
        return

    # Update the calendar with the sleep events.
    service = get_service()
    calendar_id = get_sleep_calendar_id(service, verbose=True)
    create_current_sleep_event(service, calendar_id, current_interval)
    create_next_sleep_event(service, calendar_id, next_interval)

if __name__ == "__main__":
    main()
