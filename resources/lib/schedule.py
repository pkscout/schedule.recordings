
import argparse, datetime, os, random, sys, time
from datetime import datetime
import resources.config as config
from resources.lib.dvrs import *
from resources.lib.apis.tvmaze import TVMaze
from resources.lib.xlogger import Logger

p_folderpath, p_filename = os.path.split( sys.argv[0] )
lw = Logger( logfile=os.path.join( p_folderpath, 'data', 'logs', 'logfile.log' ),
             numbackups=config.Get( 'logbackups' ), logdebug=config.Get( 'debug' ) )



class Main:
    def __init__( self ):
        lw.log( ['script started'], 'info' )
        self._parse_argv()
        self._init_vars()
        if not self.DVR:
            lw.log( ['invalid DVR configuration, exiting'] )
            return
        if self.ARGS.action == 'schedule':
            self._schedule_recordings()
        else:
            lw.log( ['no matching action for %s, exiting' % self.ARGS.action] )


    def _parse_argv( self ):
        parser = argparse.ArgumentParser()
        parser.add_argument( "-a", "--action", help="Action for the script to take" )
        parser.add_argument( "-t", "--tvmazeids", help="TV Maze IDs (comma sep), 'followed', or 'tags:tagids (comma sep)" )
        parser.add_argument( "-r", "--recordingid", help="The unique recording id provided by the PVR" )
        parser.add_argument( "-l", "--lookforward", help="number of days forwards in time to look for episode match" )
        self.ARGS = parser.parse_args()


    def _init_vars( self ):
        self.DATEFORMAT = config.Get( 'dateformat' )
        self.TVMAZEWAIT = config.Get( 'tvmaze_wait' )
        self.TVMAZE = TVMaze( user=config.Get( 'tvmaze_user' ), apikey=config.Get( 'tvmaze_apikey' ) )
        self.DVR = self._pick_dvr()
        if self.ARGS.lookforward:
            self.LOOKFORWARD = self.ARGS.lookforward
        else:
            self.LOOKFORWARD = config.Get( 'lookforward' )


    def _schedule_recordings( self ):
        if self.ARGS.tvmazeids == 'followed':
            use_tvmaze_public = False
            items = []
            success, loglines, results = self.TVMAZE.getFollowedShows( params={'embed':'show'} )
            lw.log( loglines )
            if self._check_results( results ):
                for show in results:
                    try:
                        items.append( show['_embedded']['show'] )
                    except KeyError:
                        continue
            lw.log( ['continuing with updated list of shows of:', items] )
        elif 'tags' in self.ARGS.tvmazeids:
            use_tvmaze_public = True
            items = []
            tag_map = {}
            try:
                tags = self.ARGS.tvmazeids.split( ':' )[1].split( ',' )
            except IndexError:
                tags = []
                lw.log( ['no tags found in tags call'] )
            for tag in tags:
                success, loglines, results = self.TVMAZE.getTaggedShows( tag )
                lw.log( loglines )
                if self._check_results( results ):
                    for show in results:
                        try:
                            items.append( show['show_id'] )
                        except KeyError:
                            continue
                        tag_map[show['show_id']] = tag
            lw.log( ['continuing with updated list of show ids of:', items] )
        else:
            use_tvmaze_public = True
            items = self.ARGS.tvmazeids.split( ',' )
        for item in items:
            if use_tvmaze_public:
                success, loglines, show = self.TVMAZE.getShow( item )
                lw.log( loglines )
                if not success:
                    lw.log( ['got nothing back from TVMaze, aborting'] )
                    break
                time.sleep( self.TVMAZEWAIT )
            else:
                show = item
            lw.log( ['checking %s' % show['name']] )
            if self._check_upcoming_episode( show ):
                if not self._check_recurring( show ):
                    success, loglines = self.DVR.scheduleNewRecurringRecording( show['name'], config.Get( 'dvr_params' ) )
                    lw.log( loglines )
                    if success and tag_map and config.Get( 'tvmaze_untag' ):
                        lw.log( ['untagging show %s with tag %s' % (item, tag_map[item])] )
                        self.TVMAZE.unTagShow( item, tag_map[item] )


    def _check_results( self, results ):
        try:
            check_results = results[0]['show_id']
        except (IndexError, KeyError):
            return False
        return True


    def _check_recurring( self, show ):
        loglines, recurrings = self.DVR.getScheduledRecordings()
        lw.log( loglines )
        if not recurrings:
            lw.log( ['no recurring recordings found, trying to schedule recording'] )
            return False
        lw.log( ['found some recurring recordings, checking to see if one matches %s' % show['name']] )
        if show in recurrings:
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


    def _pick_dvr( self ):
        dvr_type = config.Get( 'dvr_type' ).lower()
        if dvr_type == 'nextpvr':
            return nextpvr.NextPVR( config )
        else:
            return None
