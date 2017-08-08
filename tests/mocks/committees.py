from datapackage_pipelines_knesset.committees.processors.download_committee_meeting_protocols import DownloadCommitteeMeetingProtocolsProcessor
from datapackage_pipelines_knesset.committees.processors.parse_committee_meeting_protocols import ParseCommitteeMeetingProtocolsProcessor
from datapackage_pipelines_knesset.committees.processors.committee_meeting_protocols_update_db import CommitteeMeetingProtocolsUpdateDbProcessor
import os
from datapackage_pipelines_knesset.common.db import get_session


class MockDownloadCommitteeMeetingProtocols(DownloadCommitteeMeetingProtocolsProcessor):

    def _get_session(self):
        return get_session(connection_string="sqlite://")

    def _reuqests_get(self, url):
        if url == "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc":
            filename = "20_ptv_389210.doc"
        elif url == "http://knesset.gov.il/protocols/data/rtf/knesset/2007-12-27.rtf":
            filename = "2007-12-27.rtf"
        else:
            raise Exception("unknown url: {}".format(url))
        filename = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filename):
            res = super(MockDownloadCommitteeMeetingProtocols, self)._reuqests_get(url)
            res.raise_for_status()
            with open(filename, 'wb') as f:
                f.write(res.content)
        with open(filename, "rb") as f:
            return type("MockResponse", (object,), {"raise_for_status": lambda self: None,
                                                    "content": f.read()})()


class MockParseCommitteeMeetingProtocols(ParseCommitteeMeetingProtocolsProcessor):
    pass


class MockCommitteeMeetingProtocolsUpdateDb(CommitteeMeetingProtocolsUpdateDbProcessor):
    pass
