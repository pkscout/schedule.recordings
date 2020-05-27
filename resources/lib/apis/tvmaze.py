#v.0.3.2

import json
from . import url

headers = {}
headers['Content-Type'] = 'application/json'
headers['Accept'] = 'application/json'
JSONURL = url.URL( 'json', headers=headers )
TXTURL = url.URL()


class API( object ):

    def __init__( self, user='', apikey='' ):
        self.PUBLICURL = 'https://api.tvmaze.com'
        if user and apikey:
            self.AUTHURL = 'https://%s:%s@api.tvmaze.com/v1/user' % (user, apikey)
        else:
            self.AUTHURL = self.PUBLICURL


    def getShow( self, tvmazeid, params=None ):
        return self._call( 'shows/%s' % tvmazeid, params )


    def getEpisode( self, episodeid, params=None ):
        return self._call( 'episodes/%s' % episodeid, params )


    def getEpisodeBySeasonEpNumber( self, tvmazeid, params ):
        return self._call( 'shows/%s/episodebynumber' % tvmazeid, params )


    def getFollowedShows( self, params=None ):
        return self._call( 'follows/shows', params, auth=True )


    def getTaggedShows( self, tag, params=None ):
        return self._call( 'tags/%s/shows' % tag, params, auth=True )


    def markEpisode( self, episodeid, marked_as=0, marked_at=0, params=None ):
        payload = {'episode_id':0, 'type':marked_as, 'marked_at':marked_at }
        return self._call( 'episodes/%s' % episodeid, params, data=json.dumps( payload ), type='put', auth=True )
        

    def unTagShow( self, show, tag, params=None ):
        return self._call( 'tags/%s/shows/%s' % (tag, show), params, auth=True, type='delete' )


    def getTags( self, params=None ):
        return self._call( 'tags', params, auth=True )


    def _call( self, url_end, params, data=None, auth=False, type="get" ):
        loglines = []
        if not params:
            params = {}
        if not data:
            data = {}
        if auth:
            if self.AUTHURL == self.PUBLICURL:
                loglines.append( 'authorization credentials required but not supplied' )
                return False, loglines, {}
            url_base = self.AUTHURL
        else:
            url_base = self.PUBLICURL
        url = '%s/%s' % (url_base, url_end )
        if type == 'get':
            success, j_loglines, results = JSONURL.Get( url, params=params )
        if type == 'put':
            success, j_loglines, results = JSONURL.Put( url, params=params, data=data )
        if type == 'delete':
            success, j_loglines, results = TXTURL.Delete( url, params=params )
        loglines.extend( j_loglines )
        return success, loglines, results
