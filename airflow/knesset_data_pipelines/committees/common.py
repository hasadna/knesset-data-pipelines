from .. import db


def get_committee_parents(committee, committees):
    parent_committee_id = committee['parent_committee_id']
    if parent_committee_id:
        return [
            parent_committee_id,
            *get_committee_parents(committees[parent_committee_id], committees)
        ]
    else:
        return []


def get_committees_tree():
    with db.get_db_engine().connect() as conn:
        with conn.begin():
            committees = {
                row.committee_id: {
                    'committee_id': row.committee_id,
                    'parent_committee_id': row.parent_committee_id,
                    'name': row.name,
                    'category_desc': row.category_desc,
                } for row in conn.execute('''
                    select
                        "CommitteeID" as committee_id,
                        "ParentCommitteeID" as parent_committee_id,
                        "Name" as name,
                        "CategoryDesc" as category_desc
                    from committees_kns_committee
                ''')
            }
    for committee in committees.values():
        committee['parent_committee_ids'] = get_committee_parents(committee, committees)
        if committee['parent_committee_ids']:
            committee['root_committee_id'] = committee['parent_committee_ids'][-1]
        else:
            committee['root_committee_id'] = None
    return committees
