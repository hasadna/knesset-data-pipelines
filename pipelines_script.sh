#!/usr/bin/env bash

RUN_PIPELINE_CMD="${RUN_PIPELINE_CMD:-dpp run}"

RES=0;

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

    ./votes/view_vote_rslts_hdr_approved,
    ./votes/view_vote_mk_individual,
    ./votes/vote_result_type,
    ./votes/vote_rslts_kmmbr_shadow,
    ./votes/join-votes,
    ./votes/join_votes_shadow_mk,

    ./plenum/kns_plenumsession,
    ./plenum/kns_plmsessionitem,
    ./plenum/kns_documentplenumsession,

    ./laws/kns_law,
    ./laws/kns_law_binding,
    ./laws/kns_document_law,
    ./laws/kns_israel_law,
    ./laws/kns_israel_law_name
"` | sed 's/ //g') && RES=1

! $RUN_PIPELINE_CMD --concurrency ${DPP_CONCURRENCY:-4} $(echo `echo "
    ./bills/all,
    ./knesset/all,
    ./lobbyists/all,
    ./votes/all,
    ./plenum/all,
    ./laws/all,

    ./knesset/dump_people,

    ./committees/all,
    ./members/all
"` | sed 's/ //g') && RES=1

exit $RES
