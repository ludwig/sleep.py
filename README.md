
![Banner](./images/banner.png)

# sleep.py

You just woke up. Questions arise.
* When did I last sleep? 
* When will I sleep again?
* How regularly have I been sleeping the whole week?

Let's make it easy to answer those questions with a sleep.py helper script.

We can make it easy on ourselves by relying on the excellent
Google Calendar UI to remember all those sleep events in a way that
can be visualized easily.

This means that we need a way to have our script authenticate via OAuth
so that we can automatically create all the necessary entries under our account.
This page contains instructions for how to set up all that nonsense.

## Quickstart

![Awake](./images/awake.png)

Here is the basic usage pattern.

You just woke up.

You want to update Google Calendar as quickly as possible.

```bash
./sleep.py -u
```

That's it!

There are default values you can override, of course.

This might be the case if you didn't sleep exactly 8 hours.

You can specify intervals via the usual start, end, duration values.
The script itself will check for consistency, and fill in reasonable
defaults for the missing information.

The `-u` flag can be omitted if you want to double check
the sleep intervals that will be created. When you're ready to update
the Google Calendar you can put it back.

## Sleep Prediction

![Future](./images/future.png)

We only "predict" the next sleep interval in the sense that we make it easy
to add the next entry to our "Sleep" calendar.

You can include the next sleep interval by simply adding the `-p` flag
to our command invocation.

You can manipulate the offset value with the `-o` option by providing
the number of hours you plan to stay awake. The default is 16, but if you
know you'll be up for 20 hours, you can override it easily.

```
./sleep.py -p -o 20
```

Let's provide a few more examples.

Say you woke up at 1:30 AM and you know you slept 6 hours. You also
want to see when you'll be falling asleep next if you stay up for 21.5 hours.

```
./sleep.py -s '1:30am' -d '6 hours' -o 21.5 -p
```

Now let's suppose you fell asleep yesterday at 1pm and didn't wake up until
11pm and now you want to know when you'd be waking up if you stay up for
27 hours and sleep for 6.5 hours. Note that the `-p` flag is implied
by overriding any of the `--next-*` options.

```
./sleep.py -s '1pm yesterday' -e '11pm yesterday' -o 27 --nd 6.5
```

## CLI Options

![Options](./images/options.png)

Thanks to the `dateparser` Python library, we are able to process input dates
in a natural way. Check it out:
* [dateparser - python parser for human readable dates](https://dateparser.readthedocs.io/en/latest/)

Here is a guide to the options you will see after running:
```bash
./sleep.py --help
```

Options related to the current sleep interval:
*  `-s, --start`: Start time of sleep (e.g., "10 PM yesterday)
*  `-e, --end`: End time of sleep (e.g., "6 AM today")
*  `-d, --duration`: Duration of sleep (e.g. "8 hours")

Options related to the next sleep interval:
* `--predict-next, -p`: Predict the next sleep event.
* `--next-start, --ns`: Start time of next sleep event (e.g., "10 PM tomorrow")
* `--next-end, --ne`: End time of next sleep event (e.g., "6 AM tomorrow")
* `--next-duration, --nd`: Duration of next sleep event (e.g. "8 hours")

This offset represents how long you plan to stay awake for.
* `--default-offset, -o`: Default offset to next sleep event (e.g. "16 hours")

Options related to Google Calendar:
* `--update-calendar, -u`: Update calendar with specified sleep events.

## Installation

I'm using the [miniforge](https://github.com/conda-forge/miniforge) conda
distribution, but you can use a pip in a virtualenv or whatever else works
for you.

```
mamba create -n lam python=3.11
mamba install -n lam install --file requirements.txt
```

Now just make sure you've activated the environment before invoking the
script:
```
conda activate lam
./sleep.py --help
```

## Google Calendar Integration

![Calendar Setup](./images/setup.png)

Here's a step-by-step guide to set up your OAuth credentials to work
correctly with this script.

### Step 1: Create a Google Cloud Platform Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account.
3. Click on "Select a project" at the top of the screen, then click on "New Project".
4. Enter a project name (like "My Personal Projects"), then click on "Create".

### Step 2: Enable the Google Calendar API

1. In your new project, click on "APIs & Services > Dashboard".
2. Click on "+ ENABLE APIS AND SERVICES" at the top of the screen.
3. Search for "Google Calendar API" and select it.
4. Click "Enable" to enable the Google Calendar API for your project.

### Step 3: Create OAuth 2.0 Credentials

1. Go to the "Credentials" page in your project from the sidebar on the left.
2. Create on "Create credentials" and select "OAuth client ID".
3. If prompted, configure the OAuth consent screen:
    - Select "External" as the user type.
    - FIll in the required fields ("sleep.py" for the app name, support email, etc.)
    - Add your email address under "Test users". This allows your Google account to authenticate with the script.
    - Save and continue.
4. Go back to the "Create OAuth client ID" screen:
    - Select "Desktop app" as the application type.
    - Name your OAuth client ("sleep.py client", for example)
    - Click "Create".

### Step 4: Download OAuth Client Configuration

1. Once the credentials are created, you'll see a "Client ID" and "Client Secret" on the screen.
2. Next to the OAuth client, click on the download icon to download the JSON file.
3. The JSON file contains your client ID and client secret. Keep it secure and do not share it.

### Step 5: Install Google Client Library

You'll need the Google Client Library for Python to use OAuth 2.0 credentials
in your script. Install it using pip:

```bash
pip install -U google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Step 6: Implement OAuth in Your Script

In your Python script, you'll use the downloaded JSON file to initiate the
OAuth flow, as demonstrated in this script. The first time you run your
script, it will open a browser window asking you to log in to your
Google account and grant the necessary permissions.

Here's an example script you can use to test this integration:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def list_calendars(service):
    print("Getting list of calendars...")
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get("items", [])
    if not calendars:
        print("No calendars found.")
    for calendar in calendars:
        summary = calendar["summary"]
        print(summary)

def main():
    # Load client secrets from the JSON file
    flow = InstalledAppFlow.from_client_secrets_file(
        "path/to/client_secret.json",
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    credentials = flow.run_local_server(port=0)

    # Build the service object
    service = build("calendar", "v3", credentials=credentials)

    # Now you can use 'service' to interact with the Google Calendar API.
    # For example, listing the available calendars, etc.
    list_calendars(service)

if __name__ == "__main__":
    main()
```