
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
            lw.log( ['invalid DVR configuration, exiting'] )
            return
        if self.ARGS.action == 'schedule':
            self._schedule_recordings()
        elif self.ARGS.action == 'acquired':
            self._mark_aquired()
        else:
            lw.log( ['no matching action for %s, exiting' % self.ARGS.action] )
        lw.log( ['script ended'], 'info' )


    def _parse_argv( self ):
        parser = argparse.ArgumentParser()
        parser.add_argument( "-a", "--action", help="Action for the script to take" )
        parser.add_argument( "-t", "--tvmazeids", help="TV Maze IDs (comma sep), 'followed', or 'tags:tagids (comma sep)" )
        parser.add_argument( "-r", "--recordingid", help="The unique recording id provided by the PVR" )
        parser.add_argument( "-l", "--lookforward", help="number of days forwards in time to look for episode match" )
        self.ARGS = parser.parse_args()


    def _init_vars( self ):
        lw.log( ['initializing variables'] )
        self.DATEFORMAT = config.Get( 'dateformat' )
        self.TVMAZEWAIT = config.Get( 'tvmaze_wait' )
        self.TVMAZE = tvmaze.API( user=config.Get( 'tvmaze_user' ), apikey=config.Get( 'tvmaze_apikey' ) )
        self.DVR = self._pick_dvr()
        if self.ARGS.lookforward:
            self.LOOKFORWARD = self.ARGS.lookforward
        else:
            self.LOOKFORWARD = config.Get( 'lookforward' )


    def _check_recurring( self, show ):
        lw.log( ['checking for recurring recordings'] )
        recurrings, loglines = self.DVR.getScheduledRecordings()
        if not recurrings:
            lw.log( ['no recurring recordings found, trying to schedule recording'] )
            return False
        lw.log( ['found some recurring recordings, checking to see if one matches %s' % show['name']] )
        if show in recurrings:
            lw.log( ['found a matching recurring recording, skipping'] )
            return True
        lw.log( ['no matching recurring recording, trying to schedule recording'] )
        return False


    def _check_results( self, results ):
        lw.log( ['checking the results to see if they are valid'] )
        try:
            check_results = results[0]['show_id']
        except (IndexError, KeyError):
            return False
        return True


    def _check_upcoming_episode( self, show ):
        lw.log( ['checking for upcoming episodes'] )
        try:
            nextepisode = show['_links']['nextepisode']['href']
        except KeyError:
            lw.log( ['no next episode found in TVMaze, skipping'] )
            return False
        episodeid = nextepisode.split( '/' )[-1]
        success, loglines, episode = self.TVMAZE.getEpisode( episodeid )
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


    def _mark_aquired( self ):
        lw.log( ['starting process to mark show as acquired', 'getting show information from DVR'] )
        show_info, loglines = self.DVR.getShowInformationFromRecording( self.ARGS.recordingid )
        if show_info:
            lw.log( ['show info found', 'getting followed shows from TV Maze'] )
            success, loglines, results = self.TVMAZE.getFollowedShows( params={'embed':'show'} )
            tvmazeid = ''
            show_override = config.Get( 'show_override' )
            lw.log( ['checking to see if there is an override for %s' % show_info['name']] )
            try:
                show_info['name'] = show_override[show_info['name']]
            except KeyError:
                lw.log( ['no show override found, using original'] )
            lw.log( ['using show name of %s' % show_info['name']] )
            for followed_show in results:
                try:
                    followed_name = followed_show['_embedded']['show']['name']
                except KeyError:
                    continue
                lw.log( ['checking for %s matching %s' % (show_info['name'], followed_show['_embedded']['show']['name'])] )
                if followed_name == show_info['name']:
                    lw.log( ['found match for %s' % show_info['name'] ] )
                    tvmazeid = followed_show['show_id']
                    break
            if tvmazeid:
                lw.log( ['found tvmazeid of %s' % tvmazeid, 'attempting to get episode id'] )
                params = {'season':show_info['season'], 'number':show_info['episode']}
                success, loglines, results = self.TVMAZE.getEpisodeBySeasonEpNumber( tvmazeid, params )
                lw.log(loglines)
                try:
                    episodeid = results['id']
                except KeyError:
                    episodeid = ''
                if episodeid:
                    lw.log( ['got back episode id of %s' % episodeid] )
                    success, loglines, results = self.TVMAZE.markEpisode( episodeid, marked_as=1 )
                else:
                    lw.log( ['no episode id found'] )
            else:
                lw.log( ['no tvmazeid found'] )
        else:
            lw.log( ['no show information from DVR'] )


    def _pick_dvr( self ):
        dvr_type = config.Get( 'dvr_type' ).lower()
        if dvr_type == 'nextpvr':
            return nextpvr.DVR( config )
        else:
            return None


    def _schedule_recordings( self ):
        if self.ARGS.tvmazeids == 'followed':
            use_tvmaze_public = False
            items = []
            success, loglines, results = self.TVMAZE.getFollowedShows( params={'embed':'show'} )
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
                    if success and tag_map and config.Get( 'tvmaze_untag' ):
                        lw.log( ['untagging show %s with tag %s' % (item, tag_map[item])] )
                        self.TVMAZE.unTagShow( item, tag_map[item] )

