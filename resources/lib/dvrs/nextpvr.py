
import resources.lib.apis.nextpvr as nextpvr

class DVR:

    def __init__( self, config ):
        """Creates a NextPVR DVR object."""
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
        return recording_names, loglines


    def getShowInformationFromRecording( self, oid ):
        info = {}
        success, loglines, results = self.APICALL.getRecordingList( recording_id=oid )
        if not success:
            return info, loglines
        try:
            recording = results['recordings'][0]
        except (KeyError, IndexError):
            return info, loglines
        try:
            info['name'] = recording['name']
            info['season'] = recording['season']
            info['episode'] = recording['episode']
        except KeyError:
            info = {}
        return info, loglines
