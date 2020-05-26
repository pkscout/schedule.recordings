#v.0.1.0

from resources.lib.url import URL

JSONURL = URL( 'json' )



class NextPVRAPI( object ):

    def __init__( self, config ):
        host = config.Get( 'dvr_host' )
        port = config.Get( 'dvr_port' )
        url_end = 'services/service'
        self.BASEURL = 'http://%s:%s/%s' % (host, port, url_end)
        self.PINCODE = config.Get( 'dvr_auth' )
        self.PARAMS = {}
        self.PARAMS['format'] = 'json'
        self.PARAMS['sid'] = ''


    def searchForEpisode( self, name ):
        loglines = []
        params = self.PARAMS
        if not params['sid']:
            success, a_loglines = self._login()
            loglines.extend( a_loglines )
            if not success:
                return False, loglines, []
        params['method'] = 'channel.listings.search'
        params['title'] = name
        loglines.append( ['looking in the upcoming listings for %s' % name] )
        success, j_loglines, listings = JSONURL.Get( self.BASEURL, params=params )
        if success and listings:
            return success, loglines + j_loglines, listings['listings']
        else:
            return False, loglines + j_loglines, []


    def getScheduledRecordings( self ):
        loglines = []
        params = self.PARAMS
        if not params['sid']:
            success, a_loglines = self._login()
            loglines.extend( a_loglines )
            if not success:
                return False, loglines, []
        params['method'] = 'recording.recurring.list'
        success, loglines, recurrings = JSONURL.Get( self.BASEURL, params=params )
        return success, loglines, recurrings.get( 'recurrings' )


    def scheduleNewRecurringRecording( self, name, params={} ):
        loglines = []
        params.update( self.PARAMS )
        if not params['sid']:
            success, a_loglines = self._login()
            loglines.extend( a_loglines )
            if not success:
                return False, loglines
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
                success, s_loglines, results = JSONURL.Get( self.BASEURL, params=params )
                loglines = loglines + s_loglines
                break
            else:
                loglines.append( 'no match between listing %s and name %s' % (listings.get( 'name' ), name) )
        return True, loglines

    def _login( self ):
        params = { 'format':'json' }
        params['method'] = 'session.initiate'
        params['ver'] = '1.0'
        params['device'] = 'tvmaze.integration'
        success, loglines, keys = JSONURL.Get( self.BASEURL, params=params )
        if success:
            sid = keys['sid']
            salt = keys['salt']
            params = { 'format':'json' }
            params['sid'] = sid
            params['method'] = 'session.login'
            params['md5'] = self._hash_me( ':' + self._hash_me( self.PINCODE ) + ':' + salt )
            success, a_loglines, login = JSONURL.Get( self.BASEURL, params=params )
            loglines = loglines + a_loglines
            if success and login['stat'] == 'ok':
                self.PARAMS['sid'] = login['sid']
                return True, loglines
            else:
                loglines.append( 'unable to login' )
                return False, loglines
        else:
            loglines.append( 'unable to login' )
            return False, loglines

    def _hash_me ( self, thedata ):
        import hashlib
        h = hashlib.md5()
        h.update( thedata.encode( 'utf-8' ) )
        return h.hexdigest()
