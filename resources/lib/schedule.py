
import atexit, argparse, datetime, os, random, sys, time
from datetime import datetime
import resources.config as config
from resources.lib.tvmazeapi import TVMaze
from resources.lib.dvrapis import NextPVRAPI
from resources.lib.fileops import checkPath, deleteFile, writeFile
from resources.lib.xlogger import Logger
from configparser import *

p_folderpath, p_filename = os.path.split( sys.argv[0] )
logpath = os.path.join( p_folderpath, 'data', 'logs', '' )
checkPath( logpath )
lw = Logger( logfile=os.path.join( logpath, 'logfile.log' ), numbackups=config.Get( 'logbackups' ), logdebug=config.Get( 'debug' ) )

def _deletePID():
    success, loglines = deleteFile( pidfile )
    lw.log (loglines )
    lw.log( ['script stopped'], 'info' )

pid = str(os.getpid())
pidfile = os.path.join( p_folderpath, 'data', 'create.pid' )
atexit.register( _deletePID )



class Main:
    def __init__( self ):
        lw.log( ['script started'], 'info' )
        self._setPID()
        self._parse_argv()
        self._init_vars()
        if self.DVRAPI:
            self._schedule_recordings()
        else:
            lw.log( ['invalid DVR API configuration, exiting'] )


    def _setPID( self ):
        basetime = time.time()
        while os.path.isfile( pidfile ):
            time.sleep( random.randint( 1, 3 ) )
            if time.time() - basetime > config.Get( 'aborttime' ):
                err_str = 'taking too long for previous process to close - aborting attempt'
                lw.log( [err_str] )
                sys.exit( err_str )
        lw.log( ['setting PID file'] )
        success, loglines = writeFile( pid, pidfile, 'w' )
        lw.log( loglines )


    def _parse_argv( self ):
        parser = argparse.ArgumentParser()
        parser.add_argument( "-i", "--tvmazeids", help="comma separated list of the TV Maze ID of the shows" )
        parser.add_argument( "-l", "--lookforward", help="number of days forwards in time to look for episode match" )
        parser.add_argument( "-u", "--tvmaze_user", help="the TV Maze user id (only needed for certain functions)" )
        parser.add_argument( "-a", "--tvmaze_apikey", help="the TV Maze api key (only needed for certain functions)" )
        parser.add_argument( "-d", "--dvr_user", help="the DVR user id (if needed)" )
        parser.add_argument( "-p", "--dvr_auth", help="the DVR auth (if needed)" )
        self.ARGS = parser.parse_args()


    def _init_vars( self ):
        self.ABORT = False
        self.DATEFORMAT = config.Get( 'dateformat' )
        if self.ARGS.lookforward:
            self.LOOKFORWARD = self.ARGS.lookforward
        else:
            self.LOOKFORWARD = config.Get( 'lookforward' )
        if self.ARGS.tvmaze_user:
            tvmaze_user = self.ARGS.tvmaze_user
        else:
            tvmaze_user = config.Get( 'tvmaze_user' )
        if self.ARGS.tvmaze_apikey:
            tvmaze_apikey = self.ARGS.tvmaze_apikey
        else:
            tvmaze_apikey = config.Get( 'tvmaze_user' )
        if self.ARGS.dvr_user:
            self.DVRUSER = self.ARGS.dvr_user
        else:
            self.DVRUSER = config.Get( 'dvr_user' )
        if self.ARGS.dvr_auth:
            self.DVRAUTH = self.ARGS.dvr_auth
        else:
            self.DVRAUTH = config.Get( 'dvr_auth' )
        self.TVMAZE = TVMaze( user=tvmaze_user, apikey=tvmaze_apikey )
        self.DVRAPI = self._pick_api()


    def _schedule_recordings( self ):
        params = { 'embed':'episodes' }
        for tvmazeid in self.ARGS.tvmazeids.split( ',' ):
            success, loglines, show = self.TVMAZE.getShow( tvmazeid )
            lw.log( loglines )
            if not success:
                lw.log( ['got nothing back from TVMaze, aborting'] )
                break
            lw.log( ['checking %s' % show['name']] )
            if self._check_recurring( show ):
                if self.ABORT:
                    break
                else:
                    continue
            if self._check_upcoming_episode( show ):
                success, loglines = self.DVRAPI.scheduleNewRecurringRecording( show['name'], config.Get( 'dvr_params' ) )
                lw.log( loglines )


    def _check_recurring( self, show ):
        success, loglines, recurrings = self.DVRAPI.getScheduledRecordings()
        lw.log( loglines )
        if not success:
            self.ABORT = True
            lw.log( ['got no response from the DVR, aborting'] )
            return True
        if not recurrings:
            lw.log( ['no recurring recordings found, trying to schedule recording'] )
            return False
        else:
            lw.log( ['found some recurring recordings, checking to see if one matches %s' % show['name']] )
            for recurring in recurrings:
                if recurring['name'] == show['name']:
                    lw.log( ['found a matching recurring recording, skipping'] )
                    return True
            lw.log( ['no matching recurring recording, trying to schedule recording'] )
            return False


    def _check_upcoming_episode( self, show ):
        try:
            nextepisode = show['_links']['nextepisode']['href']
        except KeyError:
            lw.log( ['no next episode found in TVMaze, skipping'] )
            return False
        episodeid = nextepisode.split( '/' )[-1]
        success, loglines, episode = self.TVMAZE.getEpisode( episodeid )
        lw.log( loglines )
        if not success:
            lw.log( ['unable to get episode information from TVMaze for episode %s, skipping' % episodeid] )
            return False
        next_airdate = episode.get( 'airdate' )
        if next_airdate:
            next_date = datetime.strptime( next_airdate, self.DATEFORMAT )
            today = datetime.now()
            gapdays = (next_date - today).days
            if  gapdays > self.LOOKFORWARD:
                lw.log( ['next episode is still %s days away, skipping for now' % str( gapdays )] )
                return False
            else:
               lw.log( ['found an episode within %s days, trying to schedule' % str( gapdays )] )
               return True
        else:
            lw.log( 'no airdate for next episode in TVMaze, skipping' )
            return False


    def _pick_api( self ):
        dvr_type = config.Get( 'dvr_type' ).lower()
        if dvr_type == 'nextpvr':
            return NextPVRAPI( config, self.DVRUSER, self.DVRAUTH )
        else:
            return None
