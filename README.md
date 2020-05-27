# TVMaze Integration
This script manages some DVR management tasks with help from data from TVMaze.  On supported DVRs, it will currently:

* take list of TVMaze Show IDs and schedule recurring recordings (i.e. Tivo OnePass)
* check your TVMaze followed shows and schedule recurring recordings (requires TVMaze subscription)
* take a list of shows for a given tag (or tags) and schedule recurring recordings (required TVMaze subscription)
* mark shows recorded by your DVR as aquired on TV Maze

## PREREQUISITES:
Python 3.x (tested with Python 3.7).  This almost certainly won't work with Python 2.7 (or earlier).  Please see <https://legacy.python.org/dev/peps/pep-0373/> for information on the sunset date for Python 2.7.

### Other Modules
There in one other module that is required for the script to work properly.
```
pip3 install requests
```

## INSTALLATION:
To install download and unzip in any directory.

## CONFIGURATION
You need to create a folder in resources called `data` and then create a file called `settings.py`.  At a minimum you'll need:

### for NextPVR:

* `dvr_auth = '<string>'` (default `'0000'`)  
The NextPVR remote access PIN.

* `tvmaze_user = '<string>'` (default `''`)  
For functions requiring a TVMaze subscription, the TVMaze user name.

* `tvmaze_apikey = '<string>'` (default `''`)  
For functions requiring a TVMaze subscription, the TVMaze api key.

### All available options:

* `dvr_type = '<string>'` (default `'nextpvr'`)  
Tells the script with which DVR it is communicating.  Currently only supports NextPVR.

* `dvr_host = '<string>'` (default `'localhost'`)  
The URL uses to communicate with the DVR server.

* `dvr_port = '<string>'` (default `'8866'`)  
The port on which the DVR server is communicating.

* `dvr_user = '<string>'` (default `''`)  
The username the DVR server requires (if the DVR server requires authentication for API access).

* `dvr_auth = '<string>'` (default `'0000'`)  
The apikey or password the DVR server requires (if the DVR server requires authentication for API access).

* `dvr_params = '<dict>'` (default `{ 'recurring_type':1 }`)  
List of params used to change some of the API calls to the DVR server (see below for more information).

* `tvmaze_user = '<string>'` (default `''`)  
For functions requiring a TVMaze subscription, the TVMaze user name.

* `tvmaze_apikey = '<string>'` (default `''`)  
For functions requiring a TVMaze subscription, the TVMaze api key.

* `tvmaze_wait = '<string>'` (default `'0.12'`)  
Amount of time (in secs) to wait between calls to TVMaze (to stay under API rate limiting).

* `tvmaze_untag = '<boolean>'` (default `True`)  
If you are scheduling recordings using tags, by default the script will untag the show after it schedules the recording.

* `lookforward = '<int>'` (default `10`)  
The number of days in the future that a TVMaze next episode can be scheduled and be considered valid for trying to schedule a recording (most DVRs only have 14 days of guide data).

* `dateformat = '<string>'` (default `'%Y-%m-%d'`)  
The date format for the season date used by the command line and the settings file.

* `aborttime = <int>` (default `30`)  
If another instance of script is running, amount of time (in seconds) to wait before giving up.

* `logbackups = <int>` (default `7`)  
The number of days of logs to keep.

* `debug = <boolean>` (default `False`)  
For debugging you can get a more verbose log by setting this to True.

## USAGE

```
usage: execute.py [-h] [-a ACTION] [-t TVMAZEIDS] [-r RECORDINGID]
                  [-l LOOKFORWARD]

optional arguments:
  -h, --help            show this help message and exit
  -a ACTION, --action ACTION
                        Action for the script to take (schedule or acquired)
  -t TVMAZEIDS, --tvmazeids TVMAZEIDS
                        TV Maze IDs (comma sep), 'followed', or 'tags:tagids (comma sep)
                        (needed for schedule)
  -r RECORDINGID, --recordingid RECORDINGID
                        The unique recording id provided by the PVR
                        (needed for aquired)
  -l LOOKFORWARD, --lookforward LOOKFORWARD
                        number of days forwards in time to look for episode match
                        (if you want to override the value set in settings)
```

### Creating Recurring Recordings

#### from a List of TV Maze IDs
The good news is, this is free.  The bad news is that you have to maintain the list of ids manually. You can find TV Maze IDs for shows by searching for them at <https://tvmaze.com> and looking at the show's URL.
```
    python3 execute.py -a schedule -t 42342,23030
```

#### from your Followed Recordings
If you have a TV Maze subscription (any level), you can use your followed shows as the list of shows to try and record.  You can either put your TV Maze credentials in settings.py or in the command line.
```
    python3 execute.py -a schedule -t followed
```

#### from Tags
If you have a TV Maze subscription (any level), you can use your tags to try and schedule only some shows.  You can include more than one tag by separating the tagids with commas. To find a tag id, go to your tag list and hover over one of them.  The URL will show the tag id. For instance, I label any new shows I add to a tag called NEW SHOWS.  By default, the script will untag the show (but not unfollow it) when a recurring recording is successfully scheduled.  You can either put your TV Maze credentials in settings.py or in the command line.
```
    python3 execute.py -a schedule -t tags:9001
```

### Marking a Recording as Acquired on TV Maze
```
    python3 execute.py -a aquired -r 3492
```

### Changing How Recurring Recordings Are Saved

#### NextPVR
You can change what kind of recurring recordings are saved by creating a `dvr_params` Python dict in settings.  Here's the structure and options:

```
dvr_params = { 'recurring_type':1,
               'keep':0,
               'pre_padding':'default',
               'post_padding':'default',
               'directory_id':'Default'
             }
```

The valid recurring type integers are:

* 1: Record Series (NEW episodes)
* 2: Record Series (All Episodes) <- This is the NextPVR default, the script defaults to 1
* 3: Record Series (Daily, this timeslot)
* 4: Record Series (Weekly, this timeslot)
* 5: Record Series (Monday-Friday, this timeslot)
* 6: Record Series (Weekends, this timeslot)
* 7: Record Series (All Episodes, All Channels)

The valid keep integers are:

* 0: All
* 1-20: Number of recordings

The valid pre and post padding values are:

* default
* 1-120: minutes of pre-padding

The valid directory id is either 'Default' (the primary directory) or the name of any other directory you've added.

## Triggering from the DVR

### NextPVR
To trigger the script to run, you need to add something to either your PostUpdateEPG (for scheduling) or PostProcessing (for marking as acquired) file in NextPVR.

#### On Windows
For scheduling you need to go to the NextPVR scripts directory, edit (or create) `PostUpdateEPG.bat`, and add:
```
C:\Program Files\Python36\python.exe C:\CustomApps\tvmaze.integration\execute.py -a schedule -t tags:9001
```

For marking as aquired you need to go to the NextPVR scripts directory, edit (or create) `PostProcessing.bat`, and add:
```
C:\Program Files\Python36\python.exe C:\CustomApps\tvmaze.integration\execute.py -a aquired -r $3
```

The path to the Python executable needs to match your Python installation, and the path to the script needs to match the path on your system to the script.  If your directory path has spaces in any of the folder names, the recommendation is to surround the script path with double quotes.

#### For All Non-Windows Platforms
For scheduling, you need to go to the NextPVR scripts directory, edit (or create) `PostUpdateEPG.sh`, and add:
```
python3 /config/scripts/tvmaze.integration/execute.py -a schedule -t tags:9001
```

For marking as aquired, you need to go to the NextPVR scripts directory, edit (or create) `PostProcessing.sh`, and add:
```
python3 /config/scripts/tvmaze.integration/execute.py -a acquired -r $3
```

The path to the script needs to match the path on your system to the script.  This example is from a Docker instance where  is script is placed in the NextPVR scripts directory. If your directory path has spaces in any of the folder names, the recommendation is to surround the script path with double quotes.
