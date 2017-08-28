from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.protocols.committee import CommitteeMeetingProtocol
from knesset_data.protocols.exceptions import AntiwordException
import os, csv, json, subprocess, logging, shutil


class ParseCommitteeMeetingProtocolsProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(ParseCommitteeMeetingProtocolsProcessor, self).__init__(*args, **kwargs)
        self._schema["fields"] = [{"name": "committee_id", "type": "integer"},
                                  {"name": "meeting_id", "type": "integer"},
                                  {"name": "protocol_file", "type": "string",
                                   "description": "relative path to the protocol file"},
                                  {"name": "text_file", "type": "string"},
                                  {"name": "parts_file", "type": "string"},]
        self._all_filenames = []

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _get_filename(self, relpath):
        return os.path.join(self._parameters["out-path"], relpath)

    def _filter_row(self, meeting_protocol, **kwargs):
        committee_id = meeting_protocol["committee_id"]
        meeting_id = meeting_protocol["meeting_id"]
        parts_relpath = os.path.join(str(committee_id), "{}.csv".format(meeting_id))
        text_relpath = os.path.join(str(committee_id), "{}.txt".format(meeting_id))
        parts_filename = self._get_filename(parts_relpath)
        text_filename = self._get_filename(text_relpath)
        protocol_filename = meeting_protocol["protocol_file"]
        protocol_ext = protocol_filename.strip()[-4:]
        if not os.path.exists(parts_filename) or os.path.getsize(parts_filename) < 5:
            self._ensure_parts_path_exists(parts_filename, parts_relpath)
            if protocol_ext == ".doc":
                parse_res = self._parse_doc_protocol(committee_id, meeting_id, protocol_filename, parts_filename,
                                                     text_filename)
            elif protocol_ext == ".rtf":
                parse_res = self._parse_rtf_protocol(committee_id, meeting_id, protocol_filename, parts_filename,
                                                     text_filename)
            else:
                raise Exception("unknown extension: {}".format(protocol_ext))
            if not parse_res:
                if os.path.exists(text_filename):
                    os.unlink(text_filename)
                if os.path.exists(parts_filename):
                    os.unlink(parts_filename)
                text_filename = None
                parts_filename = None
        if parts_filename:
            self._all_filenames += [parts_relpath]
        if text_filename:
            self._all_filenames += [text_relpath]
        yield {"committee_id": committee_id,
               "meeting_id": meeting_id,
               "protocol_file": protocol_filename,
               "text_file": text_filename,
               "parts_file": parts_filename}

    def _ensure_parts_path_exists(self, parts_filename, parts_relpath):
        if parts_relpath not in self._all_filenames:
            os.makedirs(os.path.dirname(parts_filename), exist_ok=True)

    def _parse_rtf_protocol(self, committee_id, meeting_id, protocol_filename, parts_filename, text_filename):
        rtf_extractor = os.environ.get("RTF_EXTRACTOR_BIN")
        if not rtf_extractor:
            rtf_extractor = 'bin/rtf_extractor.py'
        cmd = rtf_extractor + ' ' + protocol_filename + ' ' + text_filename
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        with open(text_filename) as f:
            protocol_text = f.read()
        with CommitteeMeetingProtocol.get_from_text(protocol_text) as protocol:
            self._parse_protocol_parts(parts_filename, protocol)
        return True

    def _parse_doc_protocol(self, committee_id, meeting_id, protocol_filename, parts_filename, text_filename):
        try:
            with CommitteeMeetingProtocol.get_from_filename(protocol_filename) as protocol:
                with open(text_filename, "w") as f:
                    f.write(protocol.text)
                    logging.info("parsed doc to text -> {}".format(text_filename))
                self._parse_protocol_parts(parts_filename, protocol)
            return True
        except AntiwordException:
            logging.exception("committee {} meeting {}: failed to parse doc file, skipping".format(committee_id,
                                                                                                   meeting_id))
            return False

    def _parse_protocol_parts(self, parts_filename, protocol):
        with open(parts_filename, "w") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(["header", "body"])
            for part in protocol.parts:
                csv_writer.writerow([part.header, part.body])
            logging.info("parsed parts file -> {}".format(parts_filename))

    def _process_cleanup(self):
        filename = self._get_filename("datapackage.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            descriptor = {"name": "_", "path": self._all_filenames}
            descriptor.update(**self._parameters.get("data-resource-descriptor", {}))
            json.dump({"name": "_", "resources": [descriptor]}, f)

if __name__ == '__main__':
    ParseCommitteeMeetingProtocolsProcessor.main()
