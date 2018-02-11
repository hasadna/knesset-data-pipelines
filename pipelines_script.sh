#!/usr/bin/env bash

RUN_PIPELINE_CMD="${RUN_PIPELINE_CMD:-dpp run}"

RES=0;

if [ "${PIPELINES_BATCH_NAME}" == "dataservices1" ]; then
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

    ! $RUN_PIPELINE_CMD ./bills/kns_bill && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billname && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billinitiator && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billhistoryinitiator && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billsplit && RES=1
    ! $RUN_PIPELINE_CMD ./bills/kns_billunion && RES=1

elif [ "${PIPELINES_BATCH_NAME}" == "dataservices2" ]; then
    ! $RUN_PIPELINE_CMD ./votes/votes && RES=1

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
