
import resources.lib.apis.nextpvr as nextpvr

class DVR:

    def __init__( self, config ):
        self.APICALL = nextpvr.API( config.Get( 'dvr_host' ), config.Get( 'dvr_port' ), config.Get( 'dvr_auth' ) )


    def scheduleNewRecurringRecording( self, name, params ):
        success, loglines, results = self.APICALL.scheduleNewRecurringRecording( name, params )
        successful = success and results['stat'] == 'ok'
        return successful, loglines
 
        
    def getScheduledRecordings( self ):
        success, loglines, results = self.APICALL.getScheduledRecordings()
        if not success:
            return loglines, []
        recording_names = []
        for result in results.get( 'recurrings' ):
            try:
                recording_names.append( result['name'] )
            except KeyError:
                continue
        return loglines, recording_names
        
