from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from knesset_data.protocols.committee import CommitteeMeetingProtocol
import os, csv, json, subprocess


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

    def _rtf_to_txt(self, rtf_filename):
        rootdir = os.path.join(os.path.dirname(__file__), "..", "..", "..")
        outdir = os.path.join(rootdir, ".rtf_to_txt")
        txt_filename = os.path.join(outdir, rtf_filename.replace(os.path.dirname(rtf_filename)+"/", "").split(".")[0])
        txt_filename += ".txt"
        cmd = [os.path.join(rootdir, "bin", "soffice_convert_to_text.sh"),
               outdir, rtf_filename]
        if subprocess.call(cmd) != 0:
            raise Exception("failed to convert rtf to text: {}".format(rtf_filename))
        else:
            return txt_filename

    def _filter_row(self, meeting_protocol, **kwargs):
        parts_relpath = os.path.join(str(meeting_protocol["committee_id"]), "{}.csv".format(meeting_protocol["meeting_id"]))
        text_relpath = os.path.join(str(meeting_protocol["committee_id"]), "{}.txt".format(meeting_protocol["meeting_id"]))
        parts_filename = self._get_filename(parts_relpath)
        text_filename = self._get_filename(text_relpath)
        protocol_filename = meeting_protocol["protocol_file"]
        protocol_ext = protocol_filename.strip()[-4:]
        if parts_relpath not in self._all_filenames:
            self._all_filenames += [parts_relpath, text_relpath]
            os.makedirs(os.path.dirname(parts_filename), exist_ok=True)
        if not os.path.exists(parts_filename):
            if protocol_ext == ".doc":
                with CommitteeMeetingProtocol.get_from_filename(protocol_filename) as protocol:
                    with open(text_filename, "w") as f:
                        f.write(protocol.text)
                    with open(parts_filename, "w") as f:
                        csv_writer = csv.writer(f)
                        csv_writer.writerow(["header", "body"])
                        for part in protocol.parts:
                            csv_writer.writerow([part.header, part.body])
            elif protocol_ext == ".rtf":
                os.rename(self._rtf_to_txt(protocol_filename), text_filename)
                with open(text_filename) as f:
                    with CommitteeMeetingProtocol.get_from_text(f.read()) as protocol:
                        with open(parts_filename, "w") as f:
                            csv_writer = csv.writer(f)
                            csv_writer.writerow(["header", "body"])
                            for part in protocol.parts:
                                csv_writer.writerow([part.header, part.body])
            else:
                raise Exception("unknown extension: {}".format(protocol_ext))
        yield {"committee_id": meeting_protocol["committee_id"],
               "meeting_id": meeting_protocol["meeting_id"],
               "protocol_file": protocol_filename,
               "text_file": text_filename,
               "parts_file": parts_filename}

    def _process_cleanup(self):
        filename = self._get_filename("datapackage.json")
        with open(filename, "w") as f:
            descriptor = {"name": "_", "path": self._all_filenames}
            descriptor.update(**self._parameters.get("data-resource-descriptor", {}))
            json.dump({"name": "_", "resources": [descriptor]}, f)

if __name__ == '__main__':
    ParseCommitteeMeetingProtocolsProcessor.main()
