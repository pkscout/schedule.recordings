
import argparse, datetime, os, random, sys, time
from datetime import datetime
import resources.config as config
import resources.lib.apis.tvmaze as tvmaze
from resources.lib.dvrs import *
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
            lw.log( ['invalid DVR configuration, exiting'], 'info' )
            return
        if self.ARGS.action == 'schedule':
            self._schedule_recordings()
        elif self.ARGS.action == 'acquired':
            self._mark_aquired()
        else:
            lw.log( ['no matching action for %s, exiting' % self.ARGS.action], 'info' )
        lw.log( ['script ended'], 'info' )


    def _parse_argv( self ):
        parser = argparse.ArgumentParser()
        parser.add_argument( "-a", "--action", help="Action for the script to take" )
        parser.add_argument( "-t", "--tvmazeids", help="TV Maze IDs (comma sep), 'followed', or 'tags:tagids (comma sep)" )
        parser.add_argument( "-r", "--recordingid", help="The unique recording id provided by the PVR" )
        parser.add_argument( "-l", "--lookforward", help="number of days forwards in time to look for episode match" )
        self.ARGS = parser.parse_args()


    def _init_vars( self ):
        lw.log( ['initializing variables'], 'info' )
        self.DATEFORMAT = config.Get( 'dateformat' )
        self.TVMAZEWAIT = config.Get( 'tvmaze_wait' )
        self.TVMAZE = tvmaze.API( user=config.Get( 'tvmaze_user' ), apikey=config.Get( 'tvmaze_apikey' ) )
        self.DVR = self._pick_dvr()
        if self.ARGS.lookforward:
            self.LOOKFORWARD = self.ARGS.lookforward
        else:
            self.LOOKFORWARD = config.Get( 'lookforward' )


    def _check_recurring( self, show ):
        lw.log( ['checking for recurring recordings'], 'info' )
        recurrings, loglines = self.DVR.getScheduledRecordings()
        if not recurrings:
            lw.log( ['no recurring recordings found, trying to schedule recording'], 'info' )
            return False
        lw.log( ['found some recurring recordings, checking to see if one matches %s' % show['name']], 'info' )
        if show in recurrings:
            lw.log( ['found a matching recurring recording, skipping'], 'info' )
            return True
        lw.log( ['no matching recurring recording, trying to schedule recording'], 'info' )
        return False


    def _check_results( self, results ):
        lw.log( ['checking the results to see if they are valid'], 'info' )
        try:
            check_results = results[0]['show_id']
        except (IndexError, KeyError):
            return False
        return True


    def _check_upcoming_episode( self, show ):
        lw.log( ['checking for upcoming episodes'], 'info' )
        try:
            nextepisode = show['_links']['nextepisode']['href']
        except KeyError:
            lw.log( ['no next episode found in TVMaze, skipping'], 'info' )
            return False
        episodeid = nextepisode.split( '/' )[-1]
        success, loglines, episode = self.TVMAZE.getEpisode( episodeid )
        lw.log( loglines )
        if not success:
            lw.log( ['unable to get episode information from TVMaze for episode %s, skipping' % episodeid], 'info' )
            return False
        next_airdate = episode.get( 'airdate' )
        if next_airdate:
            next_date = datetime.strptime( next_airdate, self.DATEFORMAT )
            today = datetime.now()
            gapdays = (next_date - today).days
            if  gapdays > self.LOOKFORWARD:
                lw.log( ['next episode is still %s days away, skipping for now' % str( gapdays )], 'info' )
                return False
            else:
               lw.log( ['found an episode within %s days, trying to schedule' % str( gapdays )], 'info' )
               return True
        else:
            lw.log( 'no airdate for next episode in TVMaze, skipping', 'info' )
            return False


    def _mark_aquired( self ):
        lw.log( ['starting process to mark show as acquired', 'getting show information from DVR'], 'info' )
        show_info, loglines = self.DVR.getShowInformationFromRecording( self.ARGS.recordingid )
        if show_info:
            lw.log( ['show info found', 'getting followed shows from TV Maze'], 'info' )
            success, loglines, results = self.TVMAZE.getFollowedShows( params={'embed':'show'} )
            lw.log( loglines )
            if not success:
                lw.log( ['no valid response returned from TV Maze, aborting'], 'info' )
                return
            tvmazeid = ''
            show_override = config.Get( 'show_override' )
            lw.log( ['checking to see if there is an override for %s' % show_info['name']], 'info' )
            try:
                show_info['name'] = show_override[show_info['name']]
            except KeyError:
                lw.log( ['no show override found, using original'], 'info' )
            lw.log( ['using show name of %s' % show_info['name']], 'info' )
            for followed_show in results:
                try:
                    followed_name = followed_show['_embedded']['show']['name']
                except KeyError:
                    continue
                lw.log( ['checking for %s matching %s' % (show_info['name'], followed_show['_embedded']['show']['name'])], 'info' )
                if followed_name == show_info['name']:
                    lw.log( ['found match for %s' % show_info['name'] ], 'info' )
                    tvmazeid = followed_show['show_id']
                    break
            if tvmazeid:
                lw.log( ['found tvmazeid of %s' % tvmazeid, 'attempting to get episode id'], 'info' )
                params = {'season':show_info['season'], 'number':show_info['episode']}
                success, loglines, results = self.TVMAZE.getEpisodeBySeasonEpNumber( tvmazeid, params )
                lw.log( loglines )
                if not success:
                    lw.log( ['no valid response returned from TV Maze, aborting'], 'info' )
                    return
                try:
                    episodeid = results['id']
                except KeyError:
                    episodeid = ''
                if episodeid:
                    lw.log( ['got back episode id of %s' % episodeid, 'marking episode as acquired on TV Maze'], 'info' )
                    success, loglines, results = self.TVMAZE.markEpisode( episodeid, marked_as=1 )
                    lw.log( loglines )
                    if not success:
                        lw.log( ['no valid response returned from TV Maze, show was not marked'], 'info' )
                else:
                    lw.log( ['no episode id found'], 'info' )
            else:
                lw.log( ['no tvmazeid found'], 'info' )
        else:
            lw.log( ['no show information from DVR'], 'info' )


    def _pick_dvr( self ):
        dvr_type = config.Get( 'dvr_type' ).lower()
        if dvr_type == 'nextpvr':
            return nextpvr.DVR( config )
        else:
            return None


    def _schedule_recordings( self ):
        lw.log( ['starting process of scheduling recordings'], 'info' )
        tag_map = {}
        if self.ARGS.tvmazeids == 'followed':
            lw.log( ['trying to get a list of followed shows from TV Maze'], 'info' )
            use_tvmaze_public = False
            items = []
            success, loglines, results = self.TVMAZE.getFollowedShows( params={'embed':'show'} )
            lw.log( loglines )
            if not success:
                lw.log( ['no valid response returned from TV Maze, aborting'], 'info' )
                return
            if self._check_results( results ):
                for show in results:
                    try:
                        items.append( show['_embedded']['show'] )
                    except KeyError:
                        continue
            lw.log( ['continuing with updated list of shows of:', items], 'info' )
        elif 'tags' in self.ARGS.tvmazeids:
            lw.log( ['tring to get a list of tagged shows from TV Maze'], 'info' )
            use_tvmaze_public = True
            items = []
            try:
                tags = self.ARGS.tvmazeids.split( ':' )[1].split( ',' )
            except IndexError:
                tags = []
                lw.log( ['no tags found in tags call'], 'info' )
            for tag in tags:
                success, loglines, results = self.TVMAZE.getTaggedShows( tag )
                lw.log( loglines )
                if not success:
                    lw.log( ['no valid response returned from TV Maze, skipping %s' % tag], 'info' )
                    continue
                if self._check_results( results ):
                    for show in results:
                        try:
                            items.append( show['show_id'] )
                        except KeyError:
                            continue
                        tag_map[show['show_id']] = tag
            lw.log( ['continuing with updated list of show ids of:', items], 'info' )
        else:
            use_tvmaze_public = True
            items = self.ARGS.tvmazeids.split( ',' )
        for item in items:
            if use_tvmaze_public:
                success, loglines, show = self.TVMAZE.getShow( item )
                lw.log( loglines )
                if not success:
                    lw.log( ['got nothing back from TVMaze, aborting'], 'info' )
                    break
                time.sleep( self.TVMAZEWAIT )
            else:
                show = item
            lw.log( ['checking %s' % show['name']], 'info' )
            if self._check_upcoming_episode( show ):
                if not self._check_recurring( show ):
                    success, loglines = self.DVR.scheduleNewRecurringRecording( show['name'], config.Get( 'dvr_params' ) )
                    if success and tag_map and config.Get( 'tvmaze_untag' ):
                        lw.log( ['untagging show %s with tag %s' % (item, tag_map[item])], 'info' )
                        self.TVMAZE.unTagShow( item, tag_map[item] )
                        lw.log( loglines )
                        if not success:
                            lw.log( ['no valid response returned from TV Maze, show was not untagged'], 'info' )

