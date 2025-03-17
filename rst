#!/usr/bin/env bash

# Author/Modifier: Iarom Madden

# - [ ] replace vars with equivalent globals as in brg

# restic backups
#hostname="$HOST"
#set -e -o pipefail
rep="$1"
cmd="$2"
shift 2

args=()
opt=()

bkhq_c="${HOME}/.config/bkhq"

exl="$bkhq_c/exl"
incl="$bkhq_c/inc"
incl_part_mid="$bkhq_c/inc.part"
incl_part_min="$bkhq_c/inc.part.min"
incl_part_mst="$bkhq_c/inc.part.mst"

rst_mnt="$HOME/.local/share/aaa/mnt/xbk.rst/"

rst_env="$HOME/.config/restic"
env_lca="$rst_env/env.lca"
env_dva="$rst_env/env.dva"
env_dvb="$rst_env/env.dvb"
env_gcs="$rst_env/env.gcs"
env_was="$rst_env/env.was"

# colors
blue=$(tput setaf 4)
normal=$(tput sgr0)
yellow=$(tput setaf 3)

prnt_ln()     { printf "\n"; }

prnt_h1()     { printf "RST: %s \n" " " "$@"; prnt_ln; }

prnt_x()      { printf "RST: %s \n" "$@"; }

prnt()        { prnt_ln; prnt_x "$@"; }

prnt_rep()    { prnt "repo env: $1: $RESTIC_REPOSITORY"; }

prnt_ls()     { while IFS= read -r i; do prnt_x "$i"; done; }

prnt_args()   { prnt_ln; prnt_x "$1"; shift 1; printf "RST:   %s \n" "$@"; prnt_ln; }

prnt_fin()    { printf "${normal}\n"; prnt "END OF SCRIPT"; prnt_ln; }

hspot_test()  { nm_mobile || { printf "Exiting script\n"; exit 1; }; }

rep_set()     { . "$1" && prnt_rep "$2" ; }

rep_rem()     { hspot_test && rep_set "$1" "$2"; }


prnt_h1 "restic script: init"

case $rep in
    lca) rep_set "$env_lca" "local_vcs_a" ;;
    dva) printf "TODO \n" && exit ; rep_set "$env_dva" "device_a" ;;
    dvb) printf "TODO \n" && exit ; rep_set "$env_dvb" "device_b" ;;
    was) printf "TODO \n" && exit ; rep_rem "$env_was" "remote_wasabi" ;;
    gcs) 
        rep_rem $env_gcs "remote_gcs"
        args+=( "--option" "gs.connections=$GS_CONNECTIONS" )
        ;; #todo - migrate personal args to config file also
    
    gcsx)
        # GS CONNECTIONS MINIMUM SETTING
        rep_rem $env_gcs "remote_gcsx"
        args+=( "--option" "gs.connections=1" )
        args+=( "--verbose=3" ) ;;

    *) prnt "arg1: repo" "opts: gcs ; dvX ; lcX" && exit
        ;;
esac

case ${cmd} in
  
    custom|xx)
        prnt "choose a custom command"
        args+=("${@}")
        ;;

    mount|mnt)
        prnt "mounting repo on $rst_mnt"
        args+=('mount'     "$rst_mnt")
        ;;

    push)
        prnt "partial of /data/" "dirs:" "%40s" "${blue}$(ls ${@})${normal}"
        args+=(    'backup' )
        args+=( '--tag'                     'push-mod' )
        args+=( "--exclude-file"     "$exl")
        args+=( "${@}" )
        ;;

    backup-part-mid|bpmid|push-part-mid|psh-mid)
        prnt "partial of /data/" "dirs:" "" "$(cat ${incl_part_mid})"
        args+=( 'backup' )
        args+=( '--tag' 'data-part' )
        args+=( "--exclude-file" "$exl" )
        args+=( "--files-from" "$incl_part_mid" )
        ;;

    push-part-min|backup-part-min|bpmin|p)
        prnt "partial of /data/" "dirs:"
        prnt_ls < "${incl_part_min}"
        args+=( 'backup' )
        args+=( "--tag" "data-part-min" )
        args+=( "--exclude-file" "$exl")
        args+=( "--files-from" "$incl_part_min" )
        ;;

    push-part-most|backup-part-most|bpmst)
        prnt "key user data" "dirs" 
        prnt_ls "$(cat ${incl_part})"
        args+=( 'backup' )
        args+=( '--tag' 'data-most' )
        args+=( '--exclude-file' "$exl" )
        args+=( "--files-from" "$incl_part_mst" )
        ;;

    push-full|backup-full|bf)
        prnt "full bk /data/" "exclude using:" "$(cat ${exl})"
        args+=( 'backup' )
        args+=( '--tag data-full' )
        args+=( "--exclude-file" "$exl")
        args+=( "/data/" )
        ;;

    forget|f)
        prnt "forget old snapshots"
        args+=(
            "forget"
            "--group-by"     "paths"
            "--host"         "${HOST}"
            "--keep-last"    "${KEEP_LAST}"
            "--keep-hourly"  "${RETENTION_HOURS}"
            "--keep-daily"   "${RETENTION_DAYS}"
            "--keep-weekly"  "${RETENTION_WEEKS}"
            "--keep-monthly" "${RETENTION_MONTHS}"
            "--keep-yearly"  "${RETENTION_YEARS}"
        )
        ;;

    forget-prune|fp)
        prnt "forgetting and pruning old snapshots"
        args+=(
            "forget"
            "--prune"
            "--group-by"     "paths"
            "--host"         "${HOST}"
            "--keep-last"    "${KEEP_LAST}"
            "--keep-hourly"  "${RETENTION_HOURS}"
            "--keep-daily"   "${RETENTION_DAYS}"
            "--keep-weekly"  "${RETENTION_WEEKS}"
            "--keep-monthly" "${RETENTION_MONTHS}"
            "--keep-yearly"  "${RETENTION_YEARS}"
        )
        ;;

    version-control-xds|vc-xds|vcs-xds|xds)
        prnt "vcs equivalent for ~/xdsa/"
        args+=( 'backup' )
        args+=( '--tag' 'xds' )
        args+=( '/data/ux/dsa/' '/data/ux/dsb/' )
        ;;

    *)
        prnt \
            "arg2: restic cmd. options:" \
            "- bp     | backup-partial of /data/" \
            "- bfh    | backup-full-home" \
            "- bh     | backup-home:" \
            "- f      | forget: Forgets snapshots according to retention policies" \
            "- fp     | forget-prune: forget but also prunes unused data from the repo"
        exit
        ;;

esac

prnt_args "restic" "${args[@]}${yellow}"

restic "${args[@]}"

prnt_fin

