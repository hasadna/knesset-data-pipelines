from datapackage_pipelines.wrapper import process


yielded_session_ids = set()


def process_row(row, row_index, spec, resource_index, parameters, stats):
    if spec['name'] == 'kns_documentcommitteesession':
        session_id = row['CommitteeSessionID']
        if (row['GroupTypeID'] != 23
            or row['ApplicationDesc'] != 'DOC'
            or (not row["FilePath"].lower().endswith('.doc')
                and not row["FilePath"].lower().endswith('.docx'))
            or session_id in yielded_session_ids):
            row = None
        else:
            yielded_session_ids.add(session_id)
    return row


if __name__ == '__main__':
    process(process_row=process_row)
