#!/usr/bin/env bash


RUN_PIPELINE_CMD="${RUN_PIPELINE_CMD:-dpp run}"


RES=0;


[ "${DPP_REDIS_HOST}" != "" ] && while ! \
    python -c 'import redis;redis.StrictRedis(host="'"${DPP_REDIS_HOST}"'", db=5).ping()'
    do sleep 1; done

[ "${DPP_INFLUXDB_URL}" != "" ] && while ! \
    curl "${DPP_INFLUXDB_URL}"
    do sleep 1; done


if [ "${1}" == "" ] || [ "${1}" == "dataservices" ]; then
    ! $RUN_PIPELINE_CMD --concurrency ${DPP_CONCURRENCY:-4} $(echo `echo "
        ./committees/kns_committee,
        ./committees/kns_jointcommittee,
        ./committees/kns_cmtsitecode,
        ./committees/kns_committeesession,
        ./committees/kns_cmtsessionitem,
        ./committees/kns_documentcommitteesession,

        ./members/kns_person,
        ./members/kns_position,
        ./members/kns_persontoposition,
        ./members/kns_mksitecode,
        ./members/mk_individual,
        ./members/presence,

        ./bills/kns_bill,
        ./bills/kns_billname,
        ./bills/kns_billinitiator,
        ./bills/kns_billhistoryinitiator,
        ./bills/kns_billsplit,
        ./bills/kns_billunion,
        ./bills/kns_documentbill

        ./knesset/kns_govministry,
        ./knesset/kns_itemtype,
        ./knesset/kns_status,
        ./knesset/kns_knessetdates,

        ./lobbyists/v_lobbyist,
        ./lobbyists/v_lobbyist_clients,

        ./votes/view_vote_mk_individual,
        ./votes/vote_result_type,

        ./plenum/kns_plenumsession,
        ./plenum/kns_plmsessionitem,
        ./plenum/kns_documentplenumsession,

        ./laws/kns_law,
        ./laws/kns_law_binding,
        ./laws/kns_document_law,
        ./laws/kns_israel_law,
        ./laws/kns_israel_law_name
    "` | sed 's/ //g') && RES=1

    # these pipelines consume too much RAM
    # ./votes/view_vote_rslts_hdr_approved,
    # ./votes/vote_rslts_kmmbr_shadow,
    # ./votes/join-votes,
    # ./votes/join_votes_shadow_mk,
fi


if [ "${1}" == "" ] || [ "${1}" == "all" ]; then
    ! $RUN_PIPELINE_CMD --concurrency ${DPP_CONCURRENCY:-4} $(echo `echo "
        ./bills/all,
        ./knesset/all,
        ./lobbyists/all,
        ./votes/all,
        ./plenum/all,
        ./laws/all,
        ./committees/all,
        ./members/all
    "` | sed 's/ //g') && RES=1
fi


if [ "${1}" == "" ] || [ "${1}" == "protocols" ]; then
    ! (
        $RUN_PIPELINE_CMD ./committees/gcs_list_files &&\
        $RUN_PIPELINE_CMD ./committees/download_document_committee_session &&\
        $RUN_PIPELINE_CMD --concurrency ${DPP_CONCURRENCY:-4} $(echo `echo "
            ./committees/parse_meeting_protocols_text,
            ./committees/parse_meeting_protocols_parts
        "` | sed 's/ //g') &&\
        $RUN_PIPELINE_CMD ./committees/join-meetings
    ) && RES=1
fi


exit $RES
