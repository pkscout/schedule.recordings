#v.0.1.0

from resources.lib.url import URL

JSONURL = URL( 'json' )



class NextPVRAPI( object ):

    def __init__( self, config, user='', auth='' ):
        host = config.Get( 'dvr_host' )
        port = config.Get( 'dvr_port' )
        url_end = 'services/service'
        if user and auth:
            self.URL = 'http://%s:%s@%s:%s/%s' % (user, auth, host, port, url_end)
        else:
            self.URL = 'http://%s:%s/%s' % (host, port, url_end)
        self.PARAMS = { 'format':'json' }

    def searchForEpisode( self, name ):
        loglines = []
        params = self.PARAMS
        params['method'] = 'channel.listings.search'
        params['title'] = name
        loglines.append( ['looking in the upcoming listings for %s' % name] )
        success, j_loglines, listings = JSONURL.Get( self.URL, params=params )
        if success and listings:
            return success, loglines + j_loglines, listings['listings']
        else:
            return False, loglines + j_loglines, []


    def getScheduledRecordings( self ):
        params = self.PARAMS
        params['method'] = 'recording.recurring.list'
        success, loglines, recurrings = JSONURL.Get( self.URL, params=params )
        return success, loglines, recurrings.get( 'recurrings' )


    def scheduleNewRecurringRecording( self, name, params={} ):
        params.update( self.PARAMS )
        params['method'] = 'recording.recurring.save'
        loglines = []
        success, s_loglines, listings = self.searchForEpisode( name )
        loglines = loglines + s_loglines
        if not success:
            loglines.append( 'no listings found for %s, skipping' % name )
            return False, loglines
        for listing in listings:
            if listing.get( 'name' ) == name:
                params['event_id'] = listing.get( 'id' )
                loglines.append( 'found matching listing for %s' % name )
                success, s_loglines, results = JSONURL.Get( self.URL, params=params )
                break
            else:
                loglines.append( 'no match between listing %s and name %s' % (listings.get( 'name' ), name) )
        return True, loglines + s_loglines