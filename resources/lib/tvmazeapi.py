#v.0.1.0

from resources.lib.url import URL
JSONURL = URL( 'json' )


class TVMaze( object ):

    def __init__( self, user='', apikey='' ):
        self.URL = 'https://api.tvmaze.com'
        if user and apikey:
            self.AUTHURL = 'https://%s:%s@api.tvmaze.com' % (user, apikey)
        else:
            self.AUTHURL = self.URL


    def getShow( self, tvmazeid, params=None ):
        params = self._convert_params( params )
        url = '%s/shows/%s' % (self.URL, tvmazeid)
        return JSONURL.Get( url, params=params )


    def getEpisode( self, episodeid, params=None ):
        params = self._convert_params( params )
        url = '%s/episodes/%s' % (self.URL, episodeid)
        return JSONURL.Get( url, params=params )
        

    def _convert_params( self, params ):
        if not params:
            return {}
        else:
            return params
            
