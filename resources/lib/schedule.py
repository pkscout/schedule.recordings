
import argparse, os, time
from datetime import datetime
import resources.config as config
import resources.lib.apis.tvmaze as tvmaze
from resources.lib.dvrs import *
from resources.lib.xlogger import Logger



class Main:
    def __init__( self, thepath ):
        """Runs the various TV Maze routines."""
        self.LW = Logger( logfile=os.path.join(os.path.dirname( thepath ), 'data', 'logs', 'logfile.log' ),
                          numbackups=config.Get( 'logbackups' ), logdebug=config.Get( 'debug' ) )
        self.LW.log( ['script started'], 'info' )
        self._parse_argv()
        self._init_vars()
        if not self.DVR:
            self.LW.log( ['invalid DVR configuration, exiting'], 'info' )
            return
        if self.ARGS.action == 'schedule':
            self._schedule_recordings()
        elif self.ARGS.action == 'acquired':
            self._mark_aquired()
        else:
            self.LW.log( ['no matching action for %s, exiting' % self.ARGS.action], 'info' )
        self.LW.log( ['script ended'], 'info' )


    def _parse_argv( self ):
        parser = argparse.ArgumentParser()
        parser.add_argument( "-a", "--action", help="Action for the script to take" )
        parser.add_argument( "-t", "--tvmazeids", help="TV Maze IDs (comma sep), 'followed', or 'tags:tagids (comma sep)" )
        parser.add_argument( "-r", "--recordingid", help="The unique recording id provided by the PVR" )
        parser.add_argument( "-l", "--lookforward", help="number of days forwards in time to look for episode match" )
        self.ARGS = parser.parse_args()


    def _init_vars( self ):
        self.LW.log( ['initializing variables'], 'info' )
        self.DATEFORMAT = config.Get( 'dateformat' )
        self.TVMAZEWAIT = config.Get( 'tvmaze_wait' )
        self.TVMAZE = tvmaze.API( user=config.Get( 'tvmaze_user' ), apikey=config.Get( 'tvmaze_apikey' ) )
        self.DVR = self._pick_dvr()
        if self.ARGS.lookforward:
            self.LOOKFORWARD = self.ARGS.lookforward
        else:
            self.LOOKFORWARD = config.Get( 'lookforward' )


    def _check_recurring( self, show ):
        self.LW.log( ['checking for recurring recordings'], 'info' )
        recurrings, loglines = self.DVR.getScheduledRecordings()
        self.LW.log( loglines )
        if not recurrings:
            self.LW.log( ['no recurring recordings found, trying to schedule recording'], 'info' )
            return False
        self.LW.log( ['found some recurring recordings, checking to see if one matches %s' % show['name']], 'info' )
        if show in recurrings:
            self.LW.log( ['found a matching recurring recording, skipping'], 'info' )
            return True
        self.LW.log( ['no matching recurring recording, trying to schedule recording'], 'info' )
        return False


    def _check_results( self, results ):
        self.LW.log( ['checking the results to see if they are valid'], 'info' )
        try:
            results[0]['show_id']
        except (IndexError, KeyError):
            return False
        return True


    def _check_upcoming_episode( self, show ):
        self.LW.log( ['checking for upcoming episodes'], 'info' )
        try:
            nextepisode = show['_links']['nextepisode']['href']
        except KeyError:
            self.LW.log( ['no next episode found in TVMaze, skipping'], 'info' )
            return False
        episodeid = nextepisode.split( '/' )[-1]
        success, loglines, episode = self.TVMAZE.getEpisode( episodeid )
        self.LW.log( loglines )
        if not success:
            self.LW.log( ['unable to get episode information from TVMaze for episode %s, skipping' % episodeid], 'info' )
            return False
        next_airdate = episode.get( 'airdate' )
        if next_airdate:
            next_date = datetime.strptime( next_airdate, self.DATEFORMAT )
            today = datetime.now()
            gapdays = (next_date - today).days
            if  gapdays > self.LOOKFORWARD:
                self.LW.log( ['next episode is still %s days away, skipping for now' % str( gapdays )], 'info' )
                return False
            else:
               self.LW.log( ['found an episode within %s days, trying to schedule' % str( gapdays )], 'info' )
               return True
        else:
            self.LW.log( 'no airdate for next episode in TVMaze, skipping', 'info' )
            return False


    def _mark_aquired( self ):
        self.LW.log( ['starting process to mark show as acquired', 'getting show information from DVR'], 'info' )
        show_info, loglines = self.DVR.getShowInformationFromRecording( self.ARGS.recordingid )
        if show_info:
            self.LW.log( ['show info found', 'getting followed shows from TV Maze'], 'info' )
            success, loglines, results = self.TVMAZE.getFollowedShows( params={'embed':'show'} )
            self.LW.log( loglines )
            if not success:
                self.LW.log( ['no valid response returned from TV Maze, aborting'], 'info' )
                return
            tvmazeid = ''
            show_override = config.Get( 'show_override' )
            self.LW.log( ['checking to see if there is an override for %s' % show_info['name']], 'info' )
            try:
                show_info['name'] = show_override[show_info['name']]
            except KeyError:
                self.LW.log( ['no show override found, using original'], 'info' )
            self.LW.log( ['using show name of %s' % show_info['name']], 'info' )
            for followed_show in results:
                try:
                    followed_name = followed_show['_embedded']['show']['name']
                except KeyError:
                    continue
                self.LW.log( ['checking for %s matching %s' % (show_info['name'], followed_name)], 'info' )
                if followed_name == show_info['name']:
                    self.LW.log( ['found match for %s' % show_info['name'] ], 'info' )
                    tvmazeid = followed_show['show_id']
                    break
            if tvmazeid:
                self.LW.log( ['found tvmazeid of %s' % tvmazeid, 'attempting to get episode id'], 'info' )
                params = {'season':show_info['season'], 'number':show_info['episode']}
                success, loglines, results = self.TVMAZE.getEpisodeBySeasonEpNumber( tvmazeid, params )
                self.LW.log( loglines )
                if not success:
                    self.LW.log( ['no valid response returned from TV Maze, aborting'], 'info' )
                    return
                try:
                    episodeid = results['id']
                except KeyError:
                    episodeid = ''
                if episodeid:
                    self.LW.log( ['got back episode id of %s' % episodeid, 'marking episode as acquired on TV Maze'], 'info' )
                    success, loglines, results = self.TVMAZE.markEpisode( episodeid, marked_as=1 )
                    self.LW.log( loglines )
                    if not success:
                        self.LW.log( ['no valid response returned from TV Maze, show was not marked'], 'info' )
                else:
                    self.LW.log( ['no episode id found'], 'info' )
            else:
                self.LW.log( ['no tvmazeid found'], 'info' )
        else:
            self.LW.log( ['no show information from DVR'], 'info' )


    def _pick_dvr( self ):
        dvr_type = config.Get( 'dvr_type' ).lower()
        if dvr_type == 'nextpvr':
            return nextpvr.DVR( config )
        else:
            return None


    def _schedule_recordings( self ):
        self.LW.log( ['starting process of scheduling recordings'], 'info' )
        tag_map = {}
        if self.ARGS.tvmazeids == 'followed':
            use_tvmaze_public = False
            items = self._get_followed()
        elif 'tags' in self.ARGS.tvmazeids:
            use_tvmaze_public = True
            items, tag_map = self._get_tagged()
        else:
            use_tvmaze_public = True
            items = self.ARGS.tvmazeids.split( ',' )
        for item in items:
            if use_tvmaze_public:
                success, loglines, show = self.TVMAZE.getShow( item )
                self.LW.log( loglines )
                if not success:
                    self.LW.log( ['got nothing back from TVMaze, aborting'], 'info' )
                    break
                time.sleep( self.TVMAZEWAIT )
            else:
                show = item
            self.LW.log( ['checking %s' % show['name']], 'info' )
            if self._check_upcoming_episode( show ):
                if not self._check_recurring( show ):
                    success, loglines = self.DVR.scheduleNewRecurringRecording( show['name'], config.Get( 'dvr_params' ) )
                    if success and tag_map and config.Get( 'tvmaze_untag' ):
                        self.LW.log( ['untagging show %s with tag %s' % (item, tag_map[item])], 'info' )
                        self.TVMAZE.unTagShow( item, tag_map[item] )
                        self.LW.log( loglines )
                        if not success:
                            self.LW.log( ['no valid response returned from TV Maze, show was not untagged'], 'info' )


    def _get_followed( self ):
        self.LW.log( ['trying to get a list of followed shows from TV Maze'], 'info' )
        items = []
        success, loglines, results = self.TVMAZE.getFollowedShows( params={'embed':'show'} )
        self.LW.log( loglines )
        if not success:
            self.LW.log( ['no valid response returned from TV Maze, aborting'], 'info' )
            return []
        if self._check_results( results ):
            for show in results:
                try:
                    items.append( show['_embedded']['show'] )
                except KeyError:
                    continue
        self.LW.log( ['continuing with updated list of shows of:', items], 'info' )
        return items


    def _get_tagged( self ):
        self.LW.log( ['tring to get a list of tagged shows from TV Maze'], 'info' )
        items = []
        tag_map = {}
        try:
            tags = self.ARGS.tvmazeids.split( ':' )[1].split( ',' )
        except IndexError:
            tags = []
            self.LW.log( ['no tags found in tags call'], 'info' )
        for tag in tags:
            success, loglines, results = self.TVMAZE.getTaggedShows( tag )
            self.LW.log( loglines )
            if not success:
                self.LW.log( ['no valid response returned from TV Maze, skipping %s' % tag], 'info' )
                continue
            if self._check_results( results ):
                for show in results:
                    try:
                        items.append( show['show_id'] )
                    except KeyError:
                        continue
                    tag_map[show['show_id']] = tag
        self.LW.log( ['continuing with updated list of show ids of:', items], 'info' )
        return items, tag_map

