#!/usr/bin/env bash

RUN_PIPELINE_CMD="${RUN_PIPELINE_CMD:-dpp run}"

RES=0;

if [ "${1}" == "--dump-to-db" ]; then
    DB_USER="${DB_USER:-oknesset}"
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-oknesset}"
    ( [ -z "DB_USER" ] || [ -z "DB_PASS" ] || [ -z "DB_HOST" ] || [ -z "DB_PORT" ] || [ -z "DB_NAME" ] ) \
        && echo "missing required env vars" && exit 1
    export
    ! DPP_DB_ENGINE="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}" dpp run ./knesset/dump_to_db \
        && echo "failed to dump to db" && RES=1
    ! PGPASSWORD="${DB_PASS}" psql -h $DB_HOST -U $DB_USER -p $DB_PORT -d $DB_NAME -c "
        grant select on next_kns_committee to redash_reader;
        grant select on next_mk_individual to redash_reader;
        grant select on next_mk_attendance to redash_reader;
        grant select on next_votes to redash_reader;
    " && echo "failed to grant permissions to redash" && RES=1
    echo Great Success!

elif [ "${PIPELINES_BATCH_NAME}" == "dataservices1" ]; then
    ! $RUN_PIPELINE_CMD ./committees/kns_committee && RES=1
    ! $RUN_PIPELINE_CMD ./committees/kns_jointcommittee && RES=1
    ! $RUN_PIPELINE_CMD ./committees/kns_cmtsitecode && RES=1
    ! $RUN_PIPELINE_CMD ./committees/kns_committeesession && RES=1
    ! $RUN_PIPELINE_CMD ./committees/kns_cmtsessionitem && RES=1
    ! $RUN_PIPELINE_CMD ./committees/kns_documentcommitteesession && RES=1

    ! $RUN_PIPELINE_CMD ./members/kns_person && RES=1
    ! $RUN_PIPELINE_CMD ./members/kns_position && RES=1
    ! $RUN_PIPELINE_CMD ./members/kns_persontoposition && RES=1
    ! $RUN_PIPELINE_CMD ./members/kns_mksitecode && RES=1
    ! $RUN_PIPELINE_CMD ./members/mk_individual && RES=1
    ! $RUN_PIPELINE_CMD ./members/presence && RES=1

    ! $RUN_PIPELINE_CMD ./bills/kns_bill && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billname && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billinitiator && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billhistoryinitiator && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billsplit && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billunion && RES=1

elif [ "${PIPELINES_BATCH_NAME}" == "dataservices2" ]; then
    ! $RUN_PIPELINE_CMD ./lobbyists/v_lobbyist && RES=1
    ! $RUN_PIPELINE_CMD ./lobbyists/v_lobbyist_clients && RES=1

    ! $RUN_PIPELINE_CMD ./votes/view_vote_rslts_hdr_approved && RES=1
    ! $RUN_PIPELINE_CMD ./votes/view_vote_mk_individual && RES=1
    ! $RUN_PIPELINE_CMD ./votes/vote_result_type && RES=1
    ! $RUN_PIPELINE_CMD ./votes/vote_rslts_kmmbr_shadow && RES=1
    ! $RUN_PIPELINE_CMD ./votes/join-votes && RES=1
    ! $RUN_PIPELINE_CMD ./votes/join_votes_shadow_mk && RES=1

    ! $RUN_PIPELINE_CMD ./plenum/kns_plenumsession && RES=1
    ! $RUN_PIPELINE_CMD ./plenum/kns_plmsessionitem && RES=1
    ! $RUN_PIPELINE_CMD ./plenum/kns_documentplenumsession && RES=1

    ! $RUN_PIPELINE_CMD ./laws/kns_law && RES=1
    ! $RUN_PIPELINE_CMD ./laws/kns_law_binding && RES=1
    ! $RUN_PIPELINE_CMD ./laws/kns_document_law && RES=1
    ! $RUN_PIPELINE_CMD ./laws/kns_israel_law && RES=1
    ! $RUN_PIPELINE_CMD ./laws/kns_israel_law_name && RES=1

fi

exit $RES
